// Central app state: settings, connection, auth, system status, worker, logs.
// A tiny pub/sub so views re-render on change without a framework.

import { invoke, isTauri } from "./tauri";
import type {
  ApiResponse,
  ConnectionReport,
  Settings,
  SystemStatus,
  WorkerEvent,
  WorkerStatus,
} from "./types";

export interface LogEntry {
  ts: string;
  level: "info" | "warn" | "error" | "action";
  message: string;
}

export interface AppState {
  settings: Settings | null;
  connection: ConnectionReport | null;
  authenticated: boolean;
  status: SystemStatus | null;
  worker: WorkerStatus | null;
  logs: LogEntry[];
  connecting: boolean;
}

const state: AppState = {
  settings: null,
  connection: null,
  authenticated: false,
  status: null,
  worker: null,
  logs: [],
  connecting: false,
};

type Listener = () => void;
const listeners = new Set<Listener>();

export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function notify(): void {
  for (const fn of listeners) fn();
}

export function get(): AppState {
  return state;
}

export function log(level: LogEntry["level"], message: string): void {
  state.logs.unshift({ ts: new Date().toISOString(), level, message });
  state.logs = state.logs.slice(0, 300);
  notify();
}

// Latest live progress per render job, fed by the worker event stream so the
// Render Jobs board moves in real time (not just on the 5s server poll).
export interface LiveJob {
  progress: number;
  message: string;
  kind: string;
}
export const liveJobProgress = new Map<string, LiveJob>();

export function recordWorkerEvent(ev: WorkerEvent): void {
  if (ev.job_id) {
    liveJobProgress.set(ev.job_id, {
      progress: ev.progress,
      message: ev.message,
      kind: ev.kind,
    });
  }
}

// --- Settings ---------------------------------------------------------------

export async function loadSettings(): Promise<Settings> {
  state.settings = await invoke<Settings>("get_settings");
  return state.settings;
}

export async function saveSettings(next: Settings): Promise<void> {
  state.settings = await invoke<Settings>("save_settings", { newSettings: next });
  log("info", "Settings saved");
  notify();
}

export async function clearSettings(): Promise<void> {
  await invoke("clear_settings");
  log("warn", "Local settings cleared");
}

// --- Auth -------------------------------------------------------------------

export async function refreshAuth(): Promise<void> {
  const r = await invoke<{ authenticated: boolean }>("auth_status");
  state.authenticated = r.authenticated;
  notify();
}

export async function setToken(token: string): Promise<void> {
  await invoke("set_token", { value: token });
  await refreshAuth();
  log("info", "API token stored in OS keychain");
}

export async function logout(): Promise<void> {
  await invoke("logout");
  await refreshAuth();
  log("warn", "Logged out — token cleared");
}

// --- Connection -------------------------------------------------------------

export function apiBase(): string | null {
  return state.connection?.api_base_url ?? null;
}

export async function connect(): Promise<ConnectionReport> {
  if (!state.settings) await loadSettings();
  state.connecting = true;
  notify();
  const report = await invoke<ConnectionReport>("resolve_connection", {
    settings: state.settings,
  });
  state.connection = report;
  state.connecting = false;
  if (report.connected) {
    log("info", `Connected to ${report.server_url}`);
    await refreshStatus();
  } else {
    log("error", "No server reachable (custom → LAN → Cloudflare → localhost)");
  }
  notify();
  return report;
}

// --- Authenticated API calls (token injected in Rust) -----------------------

export async function api<T = unknown>(
  method: string,
  path: string,
  body?: unknown,
): Promise<ApiResponse<T>> {
  const base = apiBase();
  if (!base) {
    return { ok: false, status: 0, body: null as T, error: "not connected" };
  }
  return invoke<ApiResponse<T>>("api_request", {
    request: { method, base_url: base, path, body: body ?? null },
  });
}

export async function refreshStatus(): Promise<boolean> {
  const r = await api<SystemStatus>("GET", "/api/system/status");
  if (r.ok) {
    state.status = r.body;
    notify();
    return true;
  }
  return false;
}

// --- Worker -----------------------------------------------------------------

export async function refreshWorker(): Promise<void> {
  state.worker = await invoke<WorkerStatus>("worker_status");
  notify();
}

export async function startWorker(): Promise<void> {
  const base = apiBase();
  const s = state.settings;
  if (!base || !s) {
    log("error", "Connect to the server before starting the worker");
    return;
  }
  await invoke("start_worker", {
    config: {
      base_url: base,
      worker_id: s.worker_id,
      poll_seconds: s.worker_poll_seconds,
      job_kinds: s.worker_job_kinds,
      render_folder: s.local_render_folder,
    },
  });
  log("action", "Studio worker started");
  await refreshWorker();
}

export async function stopWorker(): Promise<void> {
  await invoke("stop_worker");
  log("action", "Studio worker stopped");
  await refreshWorker();
}

// --- Background polling + auto-reconnect ------------------------------------

let pollTimer: number | undefined;
let statusFailures = 0; // consecutive failed status polls while "connected"
let reconnectAttempts = 0; // for backoff while disconnected
let ticking = false;

const POLL_MS = 5000;
// Skip this many ticks between reconnect attempts (exponential, capped) so a
// downed server isn't hammered: ~5s, 10s, 20s, 40s, 60s.
function reconnectSkip(): number {
  return Math.min(2 ** reconnectAttempts, 12);
}
let skipsRemaining = 0;

async function tick(): Promise<void> {
  if (ticking) return; // never overlap slow network calls
  ticking = true;
  try {
    if (isTauri()) void refreshWorker();

    if (state.connection?.connected) {
      const ok = await refreshStatus();
      if (ok) {
        statusFailures = 0;
      } else if (++statusFailures >= 2) {
        // Server dropped — mark disconnected so the top bar goes red, then let the
        // reconnect path re-resolve (which may now pick a different priority URL).
        log("warn", "Lost connection to the server — reconnecting…");
        if (state.connection) state.connection.connected = false;
        statusFailures = 0;
        reconnectAttempts = 0;
        skipsRemaining = 0;
        notify();
      }
      return;
    }

    // Disconnected: try to reconnect on a backoff schedule.
    if (skipsRemaining > 0) {
      skipsRemaining--;
      return;
    }
    const report = await connect();
    if (report.connected) {
      reconnectAttempts = 0;
      skipsRemaining = 0;
    } else {
      skipsRemaining = reconnectSkip();
      reconnectAttempts++;
    }
  } finally {
    ticking = false;
  }
}

export function startPolling(intervalMs = POLL_MS): void {
  stopPolling();
  pollTimer = window.setInterval(() => void tick(), intervalMs);
}

export function stopPolling(): void {
  if (pollTimer) window.clearInterval(pollTimer);
  pollTimer = undefined;
  statusFailures = 0;
  reconnectAttempts = 0;
  skipsRemaining = 0;
}

// Thin bridge to the Tauri backend. Falls back to harmless stubs when the app is
// opened in a plain browser (vite dev without `tauri dev`), so the UI still renders.

type InvokeFn = (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;
type ListenFn = (
  event: string,
  handler: (e: { payload: unknown }) => void,
) => Promise<() => void>;

interface TauriGlobal {
  core?: { invoke?: InvokeFn };
  event?: { listen?: ListenFn };
}

function tauri(): TauriGlobal | undefined {
  return (window as unknown as { __TAURI__?: TauriGlobal }).__TAURI__;
}

export function isTauri(): boolean {
  return !!tauri()?.core?.invoke;
}

export async function invoke<T>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T> {
  const inv = tauri()?.core?.invoke;
  if (!inv) {
    // Browser-only dev: return empty-ish values so the UI degrades gracefully.
    return browserStub<T>(cmd);
  }
  return inv(cmd, args) as Promise<T>;
}

export async function listen<T>(
  event: string,
  handler: (payload: T) => void,
): Promise<() => void> {
  const l = tauri()?.event?.listen;
  if (!l) return () => {};
  return l(event, (e) => handler(e.payload as T));
}

function browserStub<T>(cmd: string): Promise<T> {
  const stubs: Record<string, unknown> = {
    get_settings: {
      role: "unset",
      server_url: "",
      api_base_url: "",
      lan_url: "http://192.168.1.10:8080",
      cloudflare_url: "https://media.invisable.co.uk",
      localhost_url: "http://localhost:8080",
      auto_connect_on_launch: true,
      local_worker_enabled: false,
      start_worker_on_launch: false,
      worker_id: "studio-5090",
      worker_poll_seconds: 5,
      worker_job_kinds: [],
      local_render_folder: "",
      upload_folder: "",
      warchest_folder: "",
    },
    auth_status: { authenticated: false },
    worker_status: { running: false, ffmpeg: false, whisper: false, comfyui_env: false },
    resolve_connection: { server_url: null, api_base_url: null, connected: false, candidates: [] },
    api_request: { ok: false, status: 0, body: null, error: "browser dev: not connected" },
  };
  return Promise.resolve((stubs[cmd] ?? null) as T);
}

// App bootstrap: first-launch role gate → shell (sidebar + topbar + view).

import "./styles.css";
import { clear, el } from "./lib/dom";
import {
  connect,
  get,
  loadSettings,
  log,
  recordWorkerEvent,
  refreshAuth,
  refreshWorker,
  startPolling,
  startWorker,
  subscribe,
} from "./lib/store";
import { listen } from "./lib/tauri";
import type { WorkerEvent } from "./lib/types";
import { sidebar } from "./ui/nav";
import { roleSelector } from "./ui/roleSelector";
import { settingsView } from "./ui/settings";
import { topbar } from "./ui/topbar";
import { applyLiveProgress, VIEWS } from "./ui/views";

const root = document.getElementById("app")!;
let activeView = "dashboard";

function renderShell(): void {
  const view =
    activeView === "settings"
      ? settingsView(() => renderShell())
      : (VIEWS[activeView] ?? VIEWS.dashboard)();

  const shell = el(
    "div",
    { class: "shell" },
    sidebar(activeView, (id) => {
      activeView = id;
      renderShell();
    }),
    el(
      "div",
      { class: "main" },
      topbar(),
      el("main", { class: "content" }, view),
    ),
  );
  clear(root);
  root.append(shell);
}

function renderRoleGate(): void {
  clear(root);
  root.append(
    roleSelector(() => {
      // Land on the most relevant first screen for the chosen role.
      activeView = get().settings?.role === "studio_worker" ? "worker-status" : "dashboard";
      void boot();
    }),
  );
}

// Re-render the shell when global state changes (status polls, logs, etc.).
let scheduled = false;
subscribe(() => {
  if (get().settings?.role === "unset") return;
  if (scheduled) return;
  scheduled = true;
  queueMicrotask(() => {
    scheduled = false;
    // Only refresh the chrome (topbar) cheaply; full view reloads happen on nav
    // and on explicit refresh, so typing in forms isn't interrupted.
    const tb = root.querySelector(".topbar");
    if (tb) tb.replaceWith(topbar());
  });
});

async function boot(): Promise<void> {
  const settings = await loadSettings();
  if (settings.role === "unset") {
    renderRoleGate();
    return;
  }

  renderShell();
  await refreshAuth();
  await refreshWorker();

  if (settings.auto_connect_on_launch) {
    const report = await connect();
    if (
      report.connected &&
      settings.role === "studio_worker" &&
      settings.local_worker_enabled &&
      settings.start_worker_on_launch
    ) {
      await startWorker();
    }
  }
  startPolling(5000);
  renderShell();
}

// Worker events stream from Rust → log, live render progress, status refresh.
void listen<WorkerEvent>("worker://event", (ev) => {
  const level = ev.kind === "failed" || ev.kind === "error" ? "error" : "info";
  const pct = ev.progress ? ` (${Math.round(ev.progress * 100)}%)` : "";
  log(level, `worker · ${ev.message}${pct}`);
  recordWorkerEvent(ev);
  // Update the on-screen progress bar in place; if the job isn't drawn yet (newly
  // claimed) or it just terminated, do a fuller refresh of the active board.
  const applied = applyLiveProgress(ev);
  const terminal = ["completed", "failed", "stopped"].includes(ev.kind);
  if ((!applied || terminal) && (activeView === "render-jobs" || activeView === "worker-status")) {
    renderShell();
  }
  void refreshWorker();
});

void boot();

// The persistent status bar: connection, Cloudflare/remote, LAN, API, worker,
// emergency pause, pending/failed jobs, posts scheduled today.

import { el, fmt } from "../lib/dom";
import { connect, get } from "../lib/store";

function dot(ok: boolean, warn = false): HTMLElement {
  return el("span", {
    class: `dot ${ok ? "dot--ok" : warn ? "dot--warn" : "dot--bad"}`,
  });
}

function pill(label: string, value: string, cls = ""): HTMLElement {
  return el(
    "div",
    { class: `pill ${cls}` },
    el("span", { class: "pill__label" }, label),
    el("span", { class: "pill__value" }, value),
  );
}

export function topbar(): HTMLElement {
  const st = get();
  const conn = st.connection;
  const status = st.status;

  const candidate = (label: string) =>
    conn?.candidates.find((c) => c.label === label);
  const lan = candidate("LAN");
  const cf = candidate("Cloudflare");

  const connected = !!conn?.connected;
  const apiOk = !!status?.ok;
  const workerRunning = !!st.worker?.running;
  const emergency = !!status?.emergency_pause;

  const left = el(
    "div",
    { class: "topbar__group" },
    el(
      "div",
      { class: "stat" },
      dot(connected),
      el("span", {}, connected ? `Server · ${hostOf(conn?.server_url)}` : "Disconnected"),
    ),
    el(
      "div",
      { class: "stat" },
      dot(!!cf?.reachable, cf?.auth_required),
      el("span", {}, "Cloudflare"),
    ),
    el(
      "div",
      { class: "stat" },
      dot(!!lan?.reachable),
      el("span", {}, "LAN"),
    ),
    el(
      "div",
      { class: "stat" },
      dot(apiOk),
      el("span", {}, "API"),
    ),
    el(
      "div",
      { class: "stat" },
      dot(workerRunning, !workerRunning),
      el("span", {}, workerRunning ? "Worker live" : "Worker idle"),
    ),
    el(
      "div",
      { class: "stat" },
      dot(!emergency, emergency),
      el("span", {}, emergency ? "PAUSED" : "Automation on"),
    ),
  );

  const right = el(
    "div",
    { class: "topbar__group" },
    pill("Pending", fmt(status?.pending_jobs), "pill--info"),
    pill(
      "Failed",
      fmt(status?.failed_jobs),
      (status?.failed_jobs ?? 0) > 0 ? "pill--bad" : "",
    ),
    pill("Scheduled today", fmt(status?.posts_scheduled_today), "pill--ok"),
    pill("To review", fmt(status?.pending_review), "pill--warn"),
    el(
      "button",
      {
        class: "btn btn--ghost",
        title: "Refresh server status",
        onclick: () => void connect(),
      },
      st.connecting ? "Connecting…" : "⟳ Refresh",
    ),
  );

  return el("header", { class: "topbar" }, left, right);
}

function hostOf(url: string | null | undefined): string {
  if (!url) return "—";
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

// All navigable views. Each returns an element and lazily loads its data from the
// server, then re-renders in place. Manual-intervention buttons are wired to actions.

import { clear, el, fmt } from "../lib/dom";
import { api, get, startWorker, stopWorker } from "../lib/store";
import type { SystemStatus } from "../lib/types";
import * as act from "./actions";

interface QueueItem {
  id: string;
  status: string;
  slot_label?: string;
  pillar?: string;
  platform?: string;
  candidate?: Record<string, unknown>;
}

interface Job {
  id: string;
  kind: string;
  status: string;
  title?: string;
  progress?: number;
  worker_id?: string;
  error?: string;
}

// A container that shows a spinner, loads async, then renders the result.
function asyncBox(
  load: () => Promise<HTMLElement>,
): HTMLElement {
  const box = el("div", { class: "view-async" }, el("div", { class: "loading" }, "Loading…"));
  void load()
    .then((node) => {
      clear(box);
      box.append(node);
    })
    .catch((e) => {
      clear(box);
      box.append(el("div", { class: "error-box" }, `Failed to load: ${String(e)}`));
    });
  return box;
}

function reload(host: HTMLElement, view: () => HTMLElement): void {
  clear(host);
  host.append(view());
}

function section(title: string, ...children: (HTMLElement | string)[]): HTMLElement {
  return el(
    "section",
    { class: "panel" },
    el("h2", { class: "panel__title" }, title),
    ...children,
  );
}

function titleOf(it: QueueItem): string {
  const c = it.candidate ?? {};
  return (
    it.slot_label ||
    (c["brief"] as string) ||
    (c["hook"] as string) ||
    `Post ${it.id.slice(0, 8)}`
  );
}

function bodyOf(it: QueueItem): string {
  const c = it.candidate ?? {};
  return (c["body"] as string) || (c["caption"] as string) || "";
}

function btn(label: string, cls: string, onClick: () => void): HTMLElement {
  return el("button", { class: `btn ${cls}`, onclick: onClick }, label);
}

// --- Generic queue view -----------------------------------------------------

function postCard(it: QueueItem, refresh: () => void): HTMLElement {
  const after = async (p: Promise<void>) => {
    await p;
    refresh();
  };
  const actions: HTMLElement[] = [];
  const status = it.status;
  if (status === "pending_review" || status === "needs_improvement") {
    actions.push(btn("Approve", "btn--ok", () => void after(act.approve(it.id))));
    actions.push(btn("Reject", "btn--bad", () => void after(act.reject(it.id))));
    actions.push(btn("Regenerate", "btn--ghost", () => void after(act.regeneratePost(it.id, titleOf(it)))));
  }
  if (status === "approved") {
    actions.push(btn("Schedule", "btn--info", () => void after(act.schedule(it.id))));
    actions.push(btn("Post Now", "btn--ok", () => void after(act.postNow(it.id))));
    actions.push(btn("Push To Story", "btn--ghost", () => void after(act.pushToStory(it.id))));
  }
  if (status === "scheduled") {
    actions.push(btn("Post Now", "btn--ok", () => void after(act.postNow(it.id))));
    actions.push(btn("Reject", "btn--bad", () => void after(act.reject(it.id))));
  }
  if (status === "published") {
    actions.push(btn("Recycle Post", "btn--ghost", () => void after(act.recyclePost(it.id))));
    actions.push(btn("Push To Story", "btn--ghost", () => void after(act.pushToStory(it.id))));
  }
  if (status === "rejected") {
    actions.push(btn("Recycle Post", "btn--ghost", () => void after(act.recyclePost(it.id))));
  }
  // Always available: send a render job to the 5090 for this item.
  actions.push(
    btn("Send To 5090", "btn--ghost", () =>
      void after(act.sendJobTo5090("ffmpeg_render", titleOf(it), it.id)),
    ),
  );

  return el(
    "article",
    { class: "card" },
    el(
      "div",
      { class: "card__head" },
      el("span", { class: "card__title" }, titleOf(it)),
      el("span", { class: `tag tag--${status}` }, status.replace("_", " ")),
    ),
    el(
      "div",
      { class: "card__meta" },
      it.platform ? el("span", { class: "chip" }, it.platform) : "",
      it.pillar ? el("span", { class: "chip" }, it.pillar) : "",
      el("span", { class: "chip chip--muted" }, it.id.slice(0, 8)),
    ),
    bodyOf(it) ? el("p", { class: "card__body" }, bodyOf(it).slice(0, 240)) : "",
    el("div", { class: "card__actions" }, ...actions),
  );
}

function queueView(title: string, status: string): HTMLElement {
  const host = el("div", {});
  const render = () =>
    asyncBox(async () => {
      const r = await api<{ items: QueueItem[]; counts: Record<string, number> }>(
        "GET",
        `/api/queue?status=${encodeURIComponent(status)}`,
      );
      const items = r.ok ? r.body.items ?? [] : [];
      const refresh = () => reload(host, render);
      if (!r.ok) {
        return section(title, el("div", { class: "error-box" }, r.error ?? "not connected"));
      }
      if (items.length === 0) {
        return section(title, el("p", { class: "muted" }, "Nothing here right now."));
      }
      return section(
        `${title} (${items.length})`,
        el("div", { class: "card-grid" }, ...items.map((it) => postCard(it, refresh))),
      );
    });
  reload(host, render);
  return host;
}

function formatQueueView(title: string, format: string): HTMLElement {
  // Story / Reels queues filter the whole queue by content_format.
  const host = el("div", {});
  const render = () =>
    asyncBox(async () => {
      const r = await api<{ items: QueueItem[] }>("GET", "/api/queue");
      const all = r.ok ? r.body.items ?? [] : [];
      const items = all.filter(
        (it) => (it.candidate?.["content_format"] as string) === format,
      );
      const refresh = () => reload(host, render);
      if (items.length === 0) {
        return section(title, el("p", { class: "muted" }, `No ${format} content queued.`));
      }
      return section(
        `${title} (${items.length})`,
        el("div", { class: "card-grid" }, ...items.map((it) => postCard(it, refresh))),
      );
    });
  reload(host, render);
  return host;
}

// --- Dashboard --------------------------------------------------------------

function statTile(label: string, value: string, cls = ""): HTMLElement {
  return el(
    "div",
    { class: `tile ${cls}` },
    el("div", { class: "tile__value" }, value),
    el("div", { class: "tile__label" }, label),
  );
}

export function dashboardView(): HTMLElement {
  const host = el("div", {});
  const render = () =>
    asyncBox(async () => {
      const r = await api<SystemStatus>("GET", "/api/system/status");
      const s = r.ok ? r.body : get().status;
      const counts = s?.queue_counts ?? {};
      const tiles = el(
        "div",
        { class: "tile-grid" },
        statTile("To review", fmt(s?.pending_review), "tile--warn"),
        statTile("Approved", fmt(counts["approved"]), "tile--ok"),
        statTile("Scheduled today", fmt(s?.posts_scheduled_today), "tile--info"),
        statTile("Published", fmt(counts["published"]), ""),
        statTile("Pending jobs", fmt(s?.pending_jobs), "tile--info"),
        statTile("Failed jobs", fmt(s?.failed_jobs), (s?.failed_jobs ?? 0) > 0 ? "tile--bad" : ""),
      );

      const overrides = section(
        "Manual override",
        el(
          "div",
          { class: "btn-row" },
          btn("⏸ Pause All Automation", "btn--bad", () => void act.pauseAll()),
          btn("▶ Resume Automation", "btn--ok", () => void act.resumeAll()),
          btn("⏸ Pause Posting", "btn--warn", () => void act.pausePosting()),
        ),
        s?.automation_paused
          ? el("p", { class: "banner banner--bad" }, `Automation PAUSED — ${s.automation_reason || "manual"}`)
          : el("p", { class: "banner banner--ok" }, "Automation running normally."),
      );

      const integrations = section(
        "Integrations",
        el(
          "div",
          { class: "chip-row" },
          ...Object.entries(s?.integrations ?? {}).map(([k, v]) =>
            el("span", { class: `chip ${v ? "chip--ok" : "chip--muted"}` }, `${v ? "●" : "○"} ${k}`),
          ),
        ),
      );

      return el("div", {}, section("Agency dashboard", tiles), overrides, integrations);
    });
  reload(host, render);
  return host;
}

// --- Accounts ---------------------------------------------------------------

interface Account {
  id: string;
  platform: string;
  handle: string;
  connected: boolean;
  paused: boolean;
  status: string;
}

export function accountsView(): HTMLElement {
  const host = el("div", {});
  const render = () =>
    asyncBox(async () => {
      const r = await api<{ accounts: Account[]; postiz_configured: boolean }>(
        "GET",
        "/api/accounts",
      );
      const accounts = r.ok ? r.body.accounts ?? [] : [];
      const connectRow = section(
        "Connect accounts",
        el("p", { class: "muted" }, "Connections complete server-side in Postiz/n8n — no credentials pass through this app."),
        el(
          "div",
          { class: "btn-row" },
          btn("Connect Instagram", "btn--info", () => void act.connectAccount("instagram")),
          btn("Connect TikTok", "btn--info", () => void act.connectAccount("tiktok")),
          btn("Refresh Account Status", "btn--ghost", () => reload(host, render)),
        ),
      );
      const list =
        accounts.length === 0
          ? el("p", { class: "muted" }, "No channels configured yet.")
          : el(
              "div",
              { class: "card-grid" },
              ...accounts.map((a) =>
                el(
                  "article",
                  { class: "card" },
                  el(
                    "div",
                    { class: "card__head" },
                    el("span", { class: "card__title" }, `${a.platform} · ${a.handle}`),
                    el("span", { class: `tag ${a.connected ? "tag--published" : "tag--rejected"}` }, a.status),
                  ),
                  el(
                    "div",
                    { class: "card__actions" },
                    a.paused
                      ? btn("Resume Account", "btn--ok", () => void act.resumeAccount(a.id))
                      : btn("Pause Account", "btn--warn", () => void act.pauseAccount(a.id)),
                  ),
                ),
              ),
            );
      return el("div", {}, connectRow, section("Connected accounts", list));
    });
  reload(host, render);
  return host;
}

// --- Content Factory --------------------------------------------------------

export function contentFactoryView(): HTMLElement {
  const briefInput = el("textarea", {
    class: "input input--area",
    placeholder: "Describe the content you want — e.g. 'A warm, funny reel about explaining a flare-up to a new boss'…",
    rows: "3",
  }) as HTMLTextAreaElement;

  const form = section(
    "Request specific content",
    briefInput,
    el(
      "div",
      { class: "btn-row" },
      btn("Generate New Post", "btn--ok", () => {
        if (briefInput.value.trim()) void act.generatePost(briefInput.value.trim());
      }),
      btn("Generate Campaign", "btn--info", () => {
        if (briefInput.value.trim()) void act.generateCampaign(briefInput.value.trim());
      }),
      btn("Create Specific Content Request", "btn--ghost", () => {
        if (briefInput.value.trim()) void act.requestContent(briefInput.value.trim());
      }),
    ),
    el("p", { class: "muted" }, "Runs the Content Tournament Engine on the server and queues the winners for approval."),
  );

  const jobs = section(
    "Send a production job to the 5090",
    el(
      "div",
      { class: "btn-row" },
      btn("FFmpeg Render", "btn--ghost", () => void act.sendJobTo5090("ffmpeg_render", "Ad-hoc render")),
      btn("Whisper Captions", "btn--ghost", () => void act.sendJobTo5090("whisper_caption", "Ad-hoc captions")),
      btn("ComfyUI Image", "btn--ghost", () => void act.sendJobTo5090("comfyui_image", "Ad-hoc image")),
      btn("ComfyUI Video", "btn--ghost", () => void act.sendJobTo5090("comfyui_video", "Ad-hoc video")),
    ),
  );

  return el("div", {}, form, jobs);
}

// --- Warchest ---------------------------------------------------------------

export function warchestView(): HTMLElement {
  const host = el("div", {});
  const render = () =>
    asyncBox(async () => {
      const r = await api<{ health: Record<string, unknown>; items: QueueItem[] }>(
        "GET",
        "/api/warchest",
      );
      const items = r.ok ? r.body.items ?? [] : [];
      const health = r.ok ? r.body.health ?? {} : {};
      return el(
        "div",
        {},
        section(
          "War Chest reserve",
          el(
            "div",
            { class: "kv" },
            ...Object.entries(health)
              .filter(([, v]) => typeof v !== "object")
              .map(([k, v]) =>
                el("div", { class: "kv__row" }, el("span", { class: "kv__k" }, k), el("span", {}, String(v))),
              ),
          ),
          el(
            "div",
            { class: "btn-row" },
            btn("Open Warchest", "btn--info", () => reload(host, render)),
          ),
        ),
        section(
          `Ready assets (${items.length})`,
          items.length
            ? el(
                "div",
                { class: "card-grid" },
                ...items.map((it) =>
                  el(
                    "article",
                    { class: "card" },
                    el("div", { class: "card__title" }, (it as unknown as { title?: string }).title || it.id.slice(0, 8)),
                    el("div", { class: "card__meta" }, el("span", { class: "chip" }, (it as unknown as { category?: string }).category || "evergreen")),
                  ),
                ),
              )
            : el("p", { class: "muted" }, "Reserve is empty — approve content to stock it."),
        ),
      );
    });
  reload(host, render);
  return host;
}

// --- Render jobs ------------------------------------------------------------

export function renderJobsView(): HTMLElement {
  const host = el("div", {});
  const render = () =>
    asyncBox(async () => {
      const r = await api<{ jobs: Job[]; counts: Record<string, number> }>("GET", "/api/jobs");
      const jobs = r.ok ? r.body.jobs ?? [] : [];
      const refresh = () => reload(host, render);
      const card = (j: Job) =>
        el(
          "article",
          { class: "card" },
          el(
            "div",
            { class: "card__head" },
            el("span", { class: "card__title" }, j.title || j.kind),
            el("span", { class: `tag tag--${j.status}` }, j.status),
          ),
          el(
            "div",
            { class: "card__meta" },
            el("span", { class: "chip" }, j.kind),
            j.worker_id ? el("span", { class: "chip chip--muted" }, j.worker_id) : "",
          ),
          el(
            "div",
            { class: "progress" },
            el("div", { class: "progress__bar", style: `width:${Math.round((j.progress ?? 0) * 100)}%` }),
          ),
          j.error ? el("p", { class: "error-box" }, j.error) : "",
          el(
            "div",
            { class: "card__actions" },
            ["queued", "claimed", "processing"].includes(j.status)
              ? btn("Cancel", "btn--bad", () => {
                  void act.cancelJob(j.id).then(refresh);
                })
              : el("span", {}),
          ),
        );
      return section(
        `Render jobs (${jobs.length})`,
        el(
          "div",
          { class: "btn-row" },
          btn("Refresh", "btn--ghost", refresh),
          btn("New FFmpeg Job", "btn--info", () => void act.sendJobTo5090("ffmpeg_render", "Manual job").then(refresh)),
        ),
        jobs.length ? el("div", { class: "card-grid" }, ...jobs.map(card)) : el("p", { class: "muted" }, "No jobs on the board."),
      );
    });
  reload(host, render);
  return host;
}

// --- Worker status ----------------------------------------------------------

export function workerStatusView(): HTMLElement {
  const host = el("div", {});
  const render = () => {
    const w = get().worker;
    const running = !!w?.running;
    const toolChip = (label: string, ok: boolean) =>
      el("span", { class: `chip ${ok ? "chip--ok" : "chip--muted"}` }, `${ok ? "●" : "○"} ${label}`);
    return el(
      "div",
      {},
      section(
        "Studio worker (5090)",
        el(
          "p",
          { class: running ? "banner banner--ok" : "banner banner--warn" },
          running ? "Worker is RUNNING — claiming and processing jobs." : "Worker is stopped.",
        ),
        el(
          "div",
          { class: "btn-row" },
          running
            ? btn("Stop Local Worker", "btn--bad", () => void stopWorker().then(() => reload(host, render)))
            : btn("Start Local Worker", "btn--ok", () => void startWorker().then(() => reload(host, render))),
          btn("Refresh", "btn--ghost", () => reload(host, render)),
        ),
      ),
      section(
        "Local tool status",
        el(
          "div",
          { class: "chip-row" },
          toolChip("FFmpeg", !!w?.ffmpeg),
          toolChip("Whisper", !!w?.whisper),
          toolChip("ComfyUI (env)", !!w?.comfyui_env),
        ),
      ),
      section(
        "Render board",
        renderJobsView(),
      ),
    );
  };
  reload(host, render);
  return host;
}

// --- Logs -------------------------------------------------------------------

export function logsView(): HTMLElement {
  const logs = get().logs;
  return section(
    `Activity log (${logs.length})`,
    logs.length === 0
      ? el("p", { class: "muted" }, "No activity yet.")
      : el(
          "div",
          { class: "log" },
          ...logs.map((l) =>
            el(
              "div",
              { class: `log__row log__row--${l.level}` },
              el("span", { class: "log__ts" }, new Date(l.ts).toLocaleTimeString()),
              el("span", { class: `log__lvl log__lvl--${l.level}` }, l.level),
              el("span", { class: "log__msg" }, l.message),
            ),
          ),
        ),
  );
}

// --- View registry ----------------------------------------------------------

export const VIEWS: Record<string, () => HTMLElement> = {
  dashboard: dashboardView,
  accounts: accountsView,
  "content-factory": contentFactoryView,
  warchest: warchestView,
  "approval-queue": () => queueView("Approval Queue", "pending_review"),
  scheduled: () => queueView("Scheduled Posts", "scheduled"),
  published: () => queueView("Published Posts", "published"),
  rejected: () => queueView("Rejected Posts", "rejected"),
  "story-queue": () => formatQueueView("Story Queue", "story"),
  "reels-queue": () => formatQueueView("Reels Queue", "short_video"),
  "render-jobs": renderJobsView,
  "worker-status": workerStatusView,
  logs: logsView,
};

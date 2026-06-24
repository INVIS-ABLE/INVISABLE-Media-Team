// Manual-intervention actions — every button maps to a server route. The server is
// the source of truth; these only trigger it and log the outcome.

import { api, log, refreshStatus } from "../lib/store";

async function run(label: string, fn: () => Promise<void>): Promise<void> {
  log("action", label);
  try {
    await fn();
    await refreshStatus();
  } catch (e) {
    log("error", `${label} failed: ${String(e)}`);
  }
}

function ok(label: string, r: { ok: boolean; error: string | null }): void {
  if (r.ok) log("info", `${label} ✓`);
  else log("error", `${label} ✗ ${r.error ?? "request failed"}`);
}

// --- Automation -------------------------------------------------------------

export const pauseAll = (reason = "manual") =>
  run("Pause All Automation", async () =>
    ok("Pause all", await api("POST", "/api/automation/pause", { scope: "all", reason })),
  );

export const resumeAll = () =>
  run("Resume Automation", async () =>
    ok("Resume all", await api("POST", "/api/automation/resume", { scope: "all" })),
  );

export const pausePosting = () =>
  run("Pause Posting", async () =>
    ok("Pause posting", await api("POST", "/api/automation/pause", { scope: "posting" })),
  );

export const pauseAccount = (account: string) =>
  run(`Pause Account ${account}`, async () =>
    ok(
      "Pause account",
      await api("POST", "/api/automation/pause", { scope: "account", account }),
    ),
  );

export const resumeAccount = (account: string) =>
  run(`Resume Account ${account}`, async () =>
    ok(
      "Resume account",
      await api("POST", "/api/automation/resume", { scope: "account", account }),
    ),
  );

// --- Content ----------------------------------------------------------------

export const requestContent = (brief: string, opts: Record<string, unknown> = {}) =>
  run("Create Specific Content Request", async () =>
    ok("Content request", await api("POST", "/api/content/request", { brief, ...opts })),
  );

export const generatePost = (brief: string) =>
  requestContent(brief, { count: 1, campaign: false });

export const generateCampaign = (brief: string) =>
  requestContent(brief, { count: 6, campaign: true });

// --- Jobs -------------------------------------------------------------------

export const sendJobTo5090 = (kind: string, title: string, queueItemId = "") =>
  run("Send Job To 5090", async () =>
    ok(
      "Create job",
      await api("POST", "/api/jobs/create", {
        kind,
        title,
        queue_item_id: queueItemId,
      }),
    ),
  );

export const cancelJob = (jobId: string) =>
  run("Cancel Job", async () =>
    ok("Cancel job", await api("POST", `/api/jobs/${jobId}/cancel`)),
  );

export const cancelRender = cancelJob;

// --- Posts ------------------------------------------------------------------

export const approve = (id: string) =>
  run("Approve", async () => ok("Approve", await api("POST", `/api/posts/${id}/approve`)));

export const reject = (id: string, reason = "") =>
  run("Reject", async () =>
    ok("Reject", await api("POST", `/api/posts/${id}/reject`, { reason })),
  );

export const schedule = (id: string) =>
  run("Schedule", async () => ok("Schedule", await api("POST", `/api/posts/${id}/schedule`)));

export const postNow = (id: string) =>
  run("Post Now", async () => ok("Post now", await api("POST", `/api/posts/${id}/post-now`)));

export const pushToStory = (id: string) =>
  run("Push To Story", async () =>
    ok("Push to story", await api("POST", `/api/posts/${id}/push-to-story`)),
  );

export const recyclePost = (id: string) =>
  run("Recycle Post", async () =>
    ok("Recycle", await api("POST", `/api/posts/${id}/recycle`)),
  );

export const regeneratePost = (id: string, brief: string) =>
  run("Regenerate Post", async () =>
    ok(
      "Regenerate",
      await api("POST", "/api/content/request", {
        brief: `Regenerate post ${id}: ${brief}`,
        count: 1,
      }),
    ),
  );

// --- Accounts ---------------------------------------------------------------

export const connectAccount = (platform: string) =>
  run(`Connect ${platform}`, async () =>
    ok("Connect account", await api("POST", "/api/accounts/connect", { platform })),
  );

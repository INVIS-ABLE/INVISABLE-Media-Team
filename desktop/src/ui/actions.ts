// Manual-intervention actions — every button maps to a server route. The server is
// the source of truth; these only trigger it and log the outcome.

import { api, apiBase, log, refreshStatus } from "../lib/store";
import { invoke } from "../lib/tauri";

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
  run("Create Specific Content Request", async () => {
    const r = await api<{ queued_ids?: string[] }>("POST", "/api/content/request", {
      brief,
      ...opts,
    });
    if (r.ok) {
      const n = r.body?.queued_ids?.length ?? 0;
      log("info", `Queued ${n} post${n === 1 ? "" : "s"} for review ✓`);
    } else {
      log("error", `Content request ✗ ${r.error ?? "request failed"}`);
    }
  });

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

// --- Post content edits (Edit Caption / Edit Hashtags / Replace Media) -------

export interface PostEdit {
  caption?: string;
  hook?: string;
  call_to_action?: string;
  hashtags?: string[];
}

export const editPost = (id: string, fields: PostEdit) =>
  run("Edit Post", async () =>
    ok("Edit post", await api("POST", `/api/posts/${id}/edit`, fields)),
  );

export const editCaption = (id: string, caption: string) =>
  editPost(id, { caption });

export const editHashtags = (id: string, hashtags: string[]) =>
  editPost(id, { hashtags });

export const replaceMedia = (id: string, mediaPath: string) =>
  run("Replace Media", async () =>
    ok(
      "Replace media",
      await api("POST", `/api/posts/${id}/replace-media`, { media_path: mediaPath }),
    ),
  );

export const regenerateInPlace = (id: string, brief?: string) =>
  run("Regenerate Post", async () =>
    ok(
      "Regenerate",
      await api("POST", `/api/posts/${id}/regenerate`, brief ? { brief } : {}),
    ),
  );

/** Upload a local file to the server and return its server-side path (or null). */
export async function uploadFile(
  filePath: string,
  opts: { jobId?: string; queueItemId?: string; kind?: string } = {},
): Promise<string | null> {
  const base = apiBase();
  if (!base) {
    log("error", "Upload failed: not connected");
    return null;
  }
  log("action", `Upload Finished Asset · ${filePath}`);
  const res = await invoke<{ ok: boolean; path?: string; error?: string }>(
    "upload_asset",
    {
      baseUrl: base,
      filePath,
      jobId: opts.jobId ?? "",
      queueItemId: opts.queueItemId ?? "",
      kind: opts.kind ?? "render",
    },
  );
  if (res.ok && res.path) {
    log("info", `Uploaded → ${res.path}`);
    return res.path;
  }
  log("error", `Upload failed: ${res.error ?? "unknown error"}`);
  return null;
}

// --- Accounts ---------------------------------------------------------------

export const connectAccount = (platform: string) =>
  run(`Connect ${platform}`, async () =>
    ok("Connect account", await api("POST", "/api/accounts/connect", { platform })),
  );

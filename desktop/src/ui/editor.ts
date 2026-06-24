// Post editor modal — the manual-override surface for a single post.
// Edit Caption / Edit Hashtags / hook / CTA, Replace Media (browse + upload), and
// the lifecycle actions, all in one place. The server stays the source of truth.

import { el, clear } from "../lib/dom";
import { api, log } from "../lib/store";
import { pickFile } from "../lib/tauri";
import * as act from "./actions";

interface PostDetail {
  post: {
    id: string;
    status: string;
    platform?: string;
    candidate?: Record<string, unknown>;
  };
  media: Array<{ id: string; kind: string; path: string }>;
}

function str(v: unknown): string {
  return typeof v === "string" ? v : "";
}

export function openPostEditor(postId: string, onClose: () => void): void {
  const overlay = el("div", { class: "modal-overlay" });
  const dialog = el("div", { class: "modal" });
  overlay.append(dialog);
  document.body.append(overlay);

  const close = () => {
    overlay.remove();
    onClose();
  };
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });

  function loading() {
    clear(dialog);
    dialog.append(el("div", { class: "loading" }, "Loading post…"));
  }

  async function render() {
    loading();
    const r = await api<PostDetail>("GET", `/api/posts/${postId}`);
    if (!r.ok || !r.body?.post) {
      clear(dialog);
      dialog.append(
        el("div", { class: "error-box" }, r.error ?? "Could not load post"),
        el("div", { class: "btn-row" }, el("button", { class: "btn", onclick: close }, "Close")),
      );
      return;
    }
    const { post, media } = r.body;
    const c = post.candidate ?? {};

    const hook = el("input", { class: "input", type: "text", value: str(c["hook"]) }) as HTMLInputElement;
    const caption = el("textarea", { class: "input input--area", rows: "5" }) as HTMLTextAreaElement;
    caption.value = str(c["body"]);
    const cta = el("input", { class: "input", type: "text", value: str(c["call_to_action"]) }) as HTMLInputElement;
    const hashtags = el("input", {
      class: "input",
      type: "text",
      value: Array.isArray(c["hashtags"]) ? (c["hashtags"] as string[]).join(" ") : "",
      placeholder: "#invisible #spoonie #chronicillness",
    }) as HTMLInputElement;

    const primary = str(c["primary_media"]);

    const refresh = () => void render();

    async function save() {
      await act.editPost(postId, {
        hook: hook.value,
        caption: caption.value,
        call_to_action: cta.value,
        hashtags: hashtags.value.split(/\s+/).map((h) => h.trim()).filter(Boolean),
      });
      refresh();
    }

    const regenBrief = el("input", {
      class: "input",
      type: "text",
      value: str(c["brief"]),
      placeholder: "Optional new brief — blank reuses the post's brief",
    }) as HTMLInputElement;

    async function regenerate() {
      await act.regenerateInPlace(postId, regenBrief.value.trim() || undefined);
      refresh();
    }

    async function browseAndReplace() {
      const path = await pickFile("Choose the replacement media");
      if (!path) return;
      // Upload the local file to the server, then point the post at it.
      const serverPath = await act.uploadFile(path, { queueItemId: postId, kind: "primary" });
      if (serverPath) {
        await act.replaceMedia(postId, serverPath);
        refresh();
      }
    }

    const field = (label: string, input: HTMLElement, hint?: string) =>
      el(
        "label",
        { class: "field" },
        el("span", { class: "field__label" }, label),
        input,
        hint ? el("span", { class: "field__hint" }, hint) : "",
      );

    const lifecycle: HTMLElement[] = [];
    const after = (p: Promise<void>) => void p.then(refresh);
    if (post.status === "pending_review" || post.status === "needs_improvement") {
      lifecycle.push(el("button", { class: "btn btn--ok", onclick: () => after(act.approve(postId)) }, "Approve"));
      lifecycle.push(el("button", { class: "btn btn--bad", onclick: () => after(act.reject(postId)) }, "Reject"));
    }
    if (post.status === "approved") {
      lifecycle.push(el("button", { class: "btn btn--info", onclick: () => after(act.schedule(postId)) }, "Schedule"));
      lifecycle.push(el("button", { class: "btn btn--ok", onclick: () => after(act.postNow(postId)) }, "Post Now"));
    }
    lifecycle.push(el("button", { class: "btn btn--ghost", onclick: () => after(act.pushToStory(postId)) }, "Push To Story"));

    clear(dialog);
    dialog.append(
      el(
        "div",
        { class: "modal__head" },
        el("span", { class: "modal__title" }, `Edit post · ${post.id.slice(0, 8)}`),
        el("span", { class: `tag tag--${post.status}` }, post.status.replace("_", " ")),
        el("button", { class: "modal__close", onclick: close }, "✕"),
      ),
      el(
        "div",
        { class: "modal__body" },
        field("Hook", hook),
        field("Caption", caption),
        field("Call to action", cta),
        field("Hashtags", hashtags, "Space-separated."),
        el(
          "div",
          { class: "field" },
          el("span", { class: "field__label" }, "Regenerate content"),
          regenBrief,
          el("span", { class: "field__hint" }, "Runs the Content Tournament and swaps in a fresh, gate-passed winner — same post."),
          el(
            "div",
            { class: "btn-row" },
            el("button", { class: "btn btn--warn", onclick: () => void regenerate() }, "Regenerate Post"),
          ),
        ),
        el(
          "div",
          { class: "field" },
          el("span", { class: "field__label" }, "Media"),
          primary
            ? el("div", { class: "chip chip--ok" }, `primary: ${primary.split("/").pop()}`)
            : el("span", { class: "muted" }, "No primary media set."),
          media.length
            ? el(
                "div",
                { class: "chip-row" },
                ...media.map((m) => el("span", { class: "chip chip--muted" }, `${m.kind}: ${m.path.split("/").pop()}`)),
              )
            : el("span", {}),
          el(
            "div",
            { class: "btn-row" },
            el("button", { class: "btn btn--info", onclick: () => void browseAndReplace() }, "Replace Media…"),
          ),
        ),
      ),
      el(
        "div",
        { class: "modal__foot" },
        el("div", { class: "btn-row" }, ...lifecycle),
        el(
          "div",
          { class: "btn-row" },
          el("button", { class: "btn btn--ghost", onclick: close }, "Close"),
          el("button", { class: "btn btn--ok", onclick: () => void save() }, "Save changes"),
        ),
      ),
    );
  }

  void render().catch((e) => {
    log("error", `Editor failed: ${String(e)}`);
    close();
  });
}

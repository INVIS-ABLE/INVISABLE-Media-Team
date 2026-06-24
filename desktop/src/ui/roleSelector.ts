// First-launch role selector: Command Centre vs Studio Worker.

import { el } from "../lib/dom";
import { get, saveSettings } from "../lib/store";
import type { AppRole } from "../lib/types";

export function roleSelector(onChosen: () => void): HTMLElement {
  async function choose(role: AppRole) {
    const s = get().settings;
    if (!s) return;
    const next = { ...s, role };
    if (role === "studio_worker") next.local_worker_enabled = true;
    await saveSettings(next);
    onChosen();
  }

  const card = (
    role: AppRole,
    title: string,
    tagline: string,
    bullets: string[],
  ) =>
    el(
      "button",
      { class: "role-card", onclick: () => void choose(role) },
      el("div", { class: "role-card__title" }, title),
      el("div", { class: "role-card__tagline" }, tagline),
      el(
        "ul",
        { class: "role-card__list" },
        ...bullets.map((b) => el("li", {}, b)),
      ),
      el("div", { class: "role-card__cta" }, "Choose this role →"),
    );

  return el(
    "div",
    { class: "role-screen" },
    el(
      "div",
      { class: "role-screen__head" },
      el("div", { class: "brand-mark" }, "INVISABLE®"),
      el("h1", {}, "Choose this device's role"),
      el(
        "p",
        { class: "muted" },
        "One app, two faces. You can change this later in Settings.",
      ),
    ),
    el(
      "div",
      { class: "role-grid" },
      card(
        "command_centre",
        "🛰️ Command Centre",
        "Run this on the server. The agency control room.",
        [
          "See every queue, schedule, account and worker",
          "Approve / reject / schedule / post now",
          "Pause automation & request content manually",
          "Full manual override at any time",
        ],
      ),
      card(
        "studio_worker",
        "🎬 Studio Worker",
        "Run this on the 5090. The production studio.",
        [
          "Poll & claim render jobs from the server",
          "FFmpeg / Whisper / ComfyUI processing",
          "Upload finished media back to the server",
          "Live render progress & worker status",
        ],
      ),
    ),
  );
}

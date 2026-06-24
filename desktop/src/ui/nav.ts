// Left navigation. Some items are role-aware (e.g. Worker Status leads for Studio).

import { el } from "../lib/dom";
import { get } from "../lib/store";
import type { AppRole } from "../lib/types";

export interface NavItem {
  id: string;
  label: string;
  icon: string;
  roles?: AppRole[]; // if set, only shown for these roles
}

const ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "▣" },
  { id: "accounts", label: "Accounts", icon: "@" },
  { id: "content-factory", label: "Content Factory", icon: "✦" },
  { id: "warchest", label: "Warchest", icon: "⛃" },
  { id: "approval-queue", label: "Approval Queue", icon: "✓" },
  { id: "scheduled", label: "Scheduled Posts", icon: "◷" },
  { id: "published", label: "Published Posts", icon: "✈" },
  { id: "rejected", label: "Rejected Posts", icon: "✕" },
  { id: "story-queue", label: "Story Queue", icon: "◔" },
  { id: "reels-queue", label: "Reels Queue", icon: "▶" },
  { id: "render-jobs", label: "Render Jobs", icon: "⚙" },
  { id: "worker-status", label: "Worker Status", icon: "🖥" },
  { id: "logs", label: "Logs", icon: "≣" },
  { id: "settings", label: "Settings", icon: "⚙" },
];

export function navItems(): NavItem[] {
  const role = get().settings?.role ?? "unset";
  return ITEMS.filter((it) => !it.roles || it.roles.includes(role));
}

export function sidebar(active: string, onNavigate: (id: string) => void): HTMLElement {
  const role = get().settings?.role ?? "unset";
  const roleLabel =
    role === "command_centre" ? "Command Centre" : role === "studio_worker" ? "Studio Worker" : "—";

  return el(
    "nav",
    { class: "sidebar" },
    el(
      "div",
      { class: "sidebar__brand" },
      el("div", { class: "sidebar__logo" }, "I"),
      el(
        "div",
        {},
        el("div", { class: "sidebar__name" }, "INVISABLE®"),
        el("div", { class: "sidebar__role" }, roleLabel),
      ),
    ),
    el(
      "div",
      { class: "sidebar__items" },
      ...navItems().map((it) =>
        el(
          "button",
          {
            class: `navlink ${it.id === active ? "navlink--active" : ""}`,
            onclick: () => onNavigate(it.id),
          },
          el("span", { class: "navlink__icon" }, it.icon),
          el("span", { class: "navlink__label" }, it.label),
        ),
      ),
    ),
  );
}

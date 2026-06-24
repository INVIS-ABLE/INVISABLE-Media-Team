// Platform Health — the Compliance Watchdog's page. Account health, posting mode,
// risk level, findings, shadowban signals, trends, recent events, emergency buttons.

import { clear, el, fmt } from "../lib/dom";
import { api } from "../lib/store";
import * as act from "./actions";

interface Finding {
  monitor: string;
  risk: string;
  detail: string;
  recommended_action: string;
}
interface ModeLimit {
  min_posts: number;
  max_posts: number;
  manual_approval: boolean;
  auto_comments: boolean;
  comments_drafted: boolean;
  auto_reposts: boolean;
  story_pushes: boolean;
  trend_reactions: boolean;
  strict_duplicate_checks: boolean;
}
interface HealthReport {
  health_score: number;
  risk_level: string;
  mode: string;
  suggested_mode: string;
  mode_changed: boolean;
  findings: Finding[];
  shadowban_signals: string[];
  recommended_action: string;
  mode_limits: ModeLimit;
  modes: Record<string, ModeLimit>;
  posts_today: number;
  reach_trend: number;
  engagement_trend: number;
  switches: Record<string, boolean>;
}

interface Event {
  id: string;
  kind: string;
  severity: string;
  detail: string;
  platform: string;
  created_at: string;
}

const RISK_CLASS: Record<string, string> = {
  low: "ok",
  medium: "warn",
  high: "bad",
  critical: "bad",
};

const MODE_LABEL: Record<string, string> = {
  introduction: "Introduction",
  modest_growth: "Modest Growth",
  active_influencer: "Active Influencer",
  career: "Career",
  manual_only: "Manual Only",
};

const MODE_ORDER = ["introduction", "modest_growth", "active_influencer", "career", "manual_only"];

const EMERGENCY_BUTTONS: Array<{ action: string; label: string }> = [
  { action: "pause_all", label: "Pause All Automation" },
  { action: "manual_only", label: "Manual Mode Only" },
  { action: "stop_comments", label: "Stop Comments" },
  { action: "stop_reposts", label: "Stop Reposts" },
  { action: "stop_story_pushes", label: "Stop Story Pushes" },
  { action: "stop_scheduling", label: "Stop Scheduling" },
  { action: "clear_today_queue", label: "Clear Today's Queue" },
  { action: "account_cooldown", label: "Account Cooldown Mode" },
];

function section(title: string, ...children: (HTMLElement | string)[]): HTMLElement {
  return el("section", { class: "panel" }, el("h2", { class: "panel__title" }, title), ...children);
}

function trendChip(label: string, v: number): HTMLElement {
  const cls = v < -0.3 ? "chip--bad" : v < 0 ? "chip--warn" : "chip--ok";
  const arrow = v > 0.02 ? "▲" : v < -0.02 ? "▼" : "▬";
  return el("span", { class: `chip ${cls}` }, `${label} ${arrow} ${(v * 100).toFixed(0)}%`);
}

export function platformHealthView(): HTMLElement {
  const host = el("div", {});

  const render = () => {
    clear(host);
    const box = el("div", { class: "view-async" }, el("div", { class: "loading" }, "Loading Platform Health…"));
    host.append(box);
    void api<HealthReport>("GET", "/api/compliance/health").then((r) => {
      clear(box);
      if (!r.ok) {
        box.append(el("div", { class: "error-box" }, r.error ?? "Could not load compliance health"));
        return;
      }
      box.append(build(r.body));
    });
  };

  const refresh = () => render();
  const doEmergency = (action: string) => void act.complianceEmergency(action).then(refresh);

  function build(h: HealthReport): HTMLElement {
    const risk = h.risk_level;
    const riskCls = RISK_CLASS[risk] ?? "warn";

    // Header: health score + risk banner.
    const header = section(
      "Account health",
      el(
        "div",
        { class: "health-head" },
        el(
          "div",
          { class: `health-score health-score--${riskCls}` },
          el("div", { class: "health-score__num" }, fmt(h.health_score)),
          el("div", { class: "health-score__label" }, "/ 100"),
        ),
        el(
          "div",
          { class: "health-meta" },
          el("div", { class: `banner banner--${riskCls}` }, `Risk: ${risk.toUpperCase()}`),
          el("p", {}, h.recommended_action),
          el(
            "div",
            { class: "chip-row" },
            el("span", { class: "chip" }, `${h.posts_today} posts today`),
            trendChip("Reach", h.reach_trend),
            trendChip("Engagement", h.engagement_trend),
          ),
        ),
      ),
      el(
        "div",
        { class: "btn-row" },
        el("button", { class: "btn btn--info", onclick: () => void act.evaluateCompliance().then(refresh) }, "Run Watchdog Now"),
        el("button", { class: "btn btn--ghost", onclick: refresh }, "Refresh"),
      ),
    );

    // Posting mode + selector + limits.
    const limits = h.mode_limits;
    const modeSelect = el(
      "select",
      { class: "input" },
      ...MODE_ORDER.map((m) =>
        el("option", { value: m, ...(m === h.mode ? { selected: "selected" } : {}) }, MODE_LABEL[m]),
      ),
    ) as HTMLSelectElement;

    const modeBlock = section(
      "Posting mode",
      h.mode_changed
        ? el(
            "div",
            { class: "banner banner--bad" },
            `⚠ Watchdog recommends downgrading: ${MODE_LABEL[h.mode]} → ${MODE_LABEL[h.suggested_mode]} (safety wins over growth).`,
          )
        : el("div", { class: "banner banner--ok" }, `Current mode: ${MODE_LABEL[h.mode]} — within safe limits.`),
      el(
        "div",
        { class: "kv" },
        el("div", { class: "kv__row" }, el("span", { class: "kv__k" }, "Daily posts"), el("span", {}, `${limits.min_posts}–${limits.max_posts}`)),
        el("div", { class: "kv__row" }, el("span", { class: "kv__k" }, "Manual approval"), el("span", {}, limits.manual_approval ? "Required" : "Optional")),
        el("div", { class: "kv__row" }, el("span", { class: "kv__k" }, "Auto comments"), el("span", {}, "Never")),
        el("div", { class: "kv__row" }, el("span", { class: "kv__k" }, "Comments"), el("span", {}, limits.comments_drafted ? "Drafted for approval" : "Off")),
        el("div", { class: "kv__row" }, el("span", { class: "kv__k" }, "Reposts"), el("span", {}, limits.auto_reposts ? "Allowed (manual)" : "Off")),
        el("div", { class: "kv__row" }, el("span", { class: "kv__k" }, "Story pushes"), el("span", {}, limits.story_pushes ? "Allowed" : "Off")),
        el("div", { class: "kv__row" }, el("span", { class: "kv__k" }, "Trend reactions"), el("span", {}, limits.trend_reactions ? "Allowed" : "Off")),
      ),
      el(
        "div",
        { class: "btn-row" },
        modeSelect,
        el("button", { class: "btn btn--ok", onclick: () => void act.setPostingMode(modeSelect.value).then(refresh) }, "Set Mode"),
        h.mode_changed
          ? el("button", { class: "btn btn--warn", onclick: () => void act.setPostingMode(h.suggested_mode).then(refresh) }, "Apply Downgrade")
          : el("span", {}),
      ),
    );

    // Emergency buttons.
    const activeSwitches = Object.entries(h.switches || {}).filter(([, v]) => v);
    const emergency = section(
      "Emergency controls",
      el("p", { class: "muted" }, "Every button only stops things — nothing here starts or bypasses any platform action."),
      el(
        "div",
        { class: "btn-row" },
        ...EMERGENCY_BUTTONS.map((b) =>
          el("button", { class: "btn btn--bad", onclick: () => doEmergency(b.action) }, b.label),
        ),
      ),
      activeSwitches.length
        ? el(
            "div",
            { class: "chip-row", style: "margin-top:10px" },
            ...activeSwitches.map(([k]) =>
              el(
                "span",
                { class: "chip chip--bad" },
                `${k.replace(/_/g, " ")} `,
                el("a", { class: "chip__x", onclick: () => void act.resetComplianceSwitch(k).then(refresh) }, "✕"),
              ),
            ),
            el("button", { class: "btn btn--ghost", onclick: () => void act.resetComplianceSwitch("all").then(refresh) }, "Lift all"),
          )
        : el("span", {}),
    );

    // Findings.
    const findings = section(
      `Warnings (${h.findings.length})`,
      h.findings.length === 0
        ? el("p", { class: "banner banner--ok" }, "No compliance warnings. Safe to continue.")
        : el(
            "div",
            { class: "finding-list" },
            ...h.findings
              .slice()
              .sort((a, b) => riskRank(b.risk) - riskRank(a.risk))
              .map((f) =>
                el(
                  "div",
                  { class: `finding finding--${RISK_CLASS[f.risk] ?? "warn"}` },
                  el(
                    "div",
                    { class: "finding__head" },
                    el("span", { class: `tag tag--${f.risk === "low" ? "approved" : f.risk === "medium" ? "pending_review" : "rejected"}` }, f.risk),
                    el("span", { class: "finding__monitor" }, f.monitor.replace(/_/g, " ")),
                  ),
                  el("p", { class: "finding__detail" }, f.detail),
                  el("p", { class: "finding__action" }, `→ ${f.recommended_action}`),
                ),
              ),
          ),
    );

    // Shadowban signals.
    const shadowban = h.shadowban_signals.length
      ? section(
          "Shadowban / flag warning signals",
          el("p", { class: "muted" }, "A shadowban can't be proven — these are warning patterns to act on."),
          el("ul", { class: "signal-list" }, ...h.shadowban_signals.map((sig) => el("li", {}, sig))),
        )
      : el("span", {});

    // Recent events.
    const events = el("div", {});
    void api<{ events: Event[] }>("GET", "/api/compliance/events").then((r) => {
      const list = r.ok ? r.body.events ?? [] : [];
      events.append(
        section(
          `Recent platform events (${list.length})`,
          list.length === 0
            ? el("p", { class: "muted" }, "No platform safety events recorded.")
            : el(
                "div",
                { class: "log" },
                ...list.slice(0, 40).map((e) =>
                  el(
                    "div",
                    { class: "log__row" },
                    el("span", { class: "log__ts" }, new Date(e.created_at).toLocaleString()),
                    el("span", { class: `log__lvl log__lvl--${RISK_CLASS[e.severity] === "bad" ? "error" : RISK_CLASS[e.severity] === "warn" ? "warn" : "info"}` }, e.kind.replace(/_/g, " ")),
                    el("span", { class: "log__msg" }, `${e.platform ? e.platform + " · " : ""}${e.detail}`),
                  ),
                ),
              ),
        ),
      );
    });

    return el("div", {}, header, modeBlock, emergency, findings, shadowban, events);
  }

  render();
  return host;
}

function riskRank(r: string): number {
  return { low: 0, medium: 1, high: 2, critical: 3 }[r] ?? 0;
}

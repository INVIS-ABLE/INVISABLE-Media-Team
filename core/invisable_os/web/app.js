"use strict";
// INVISABLE OS dashboard — a dependency-free PWA over the /v1 API.

const API = ""; // same-origin
const $ = (sel, root = document) => root.querySelector(sel);
const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function api(path, opts = {}) {
  const res = await fetch(API + path, { headers: { "content-type": "application/json" }, ...opts });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.status === 204 ? null : res.json();
}

let toastTimer;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 2600);
}

// --- health ----------------------------------------------------------------
async function refreshHealth() {
  const h = $("#health");
  try {
    const d = await api("/health");
    h.className = "health ok";
    h.textContent = `${d.brand}® · founder ${Math.round(d.founder_presence_target * 100)}% · ${d.claude_configured ? "Claude" : "offline"}`;
  } catch { h.className = "health down"; h.textContent = "API unreachable"; }
}

// --- views -----------------------------------------------------------------
const views = {};

views.today = async (root) => {
  root.innerHTML = `
    <div class="row">
      <h2>Today</h2><div class="spacer"></div>
      <button class="btn ghost" id="seed">Seed channels</button>
      <button class="btn" id="gen">Generate today’s 20 → queue</button>
    </div>
    <div class="stats" id="stats"><div class="muted">Generate a day to populate the queue.</div></div>
    <div class="muted" id="hint">Posts are gated, mission-scored and quality-checked, then spun into ~7 assets each.</div>`;
  $("#seed", root).onclick = async () => {
    try {
      await api("/v1/channels", { method: "POST", body: JSON.stringify({ name: "INVISABLE Instagram", platform: "instagram" }) });
      await api("/v1/channels", { method: "POST", body: JSON.stringify({ name: "INVISABLE TikTok", platform: "tiktok" }) });
      toast("Channels + posting schedule created");
    } catch (e) { toast("Seed failed: " + e.message); }
  };
  $("#gen", root).onclick = async (ev) => {
    ev.target.disabled = true; ev.target.textContent = "Generating…";
    try {
      const d = await api("/v1/daily/plan", { method: "POST", body: JSON.stringify({ persist: true, candidates_per_slot: 10 }) });
      renderStats($("#stats", root), d);
      toast(`Queued ${d.queued_ids.length} posts · ${d.total_assets} assets`);
    } catch (e) { toast("Failed: " + e.message); }
    ev.target.disabled = false; ev.target.textContent = "Generate today’s 20 → queue";
  };
  try { renderStats($("#stats", root), await api("/v1/brain/stats"), true); } catch {}
};

function renderStats(node, d, isBrain) {
  const cells = isBrain
    ? [["Memories", d.total_memories], ["Winning patterns", d.winning_patterns], ["Learnings", d.performance_learnings], ["Trend signals", d.trend_signals]]
    : [["Posts", d.total], ["Assets", d.total_assets], ["Needs work", d.needs_improvement], ["Review", d.needs_human_review]];
  node.innerHTML = cells.map(([l, n]) => `<div class="stat"><div class="n">${n ?? 0}</div><div class="l">${l}</div></div>`).join("");
}

views.queue = async (root) => {
  root.innerHTML = `<div class="row"><h2>Approval queue</h2><div class="spacer"></div>
    <button class="btn ghost" id="refresh">Refresh</button></div>
    <div class="row" id="counts"></div><div class="cards" id="list"></div>`;
  $("#refresh", root).onclick = () => views.queue(root);
  const data = await api("/v1/queue");
  $("#counts", root).innerHTML = Object.entries(data.counts || {})
    .map(([s, n]) => `<span class="badge">${esc(s)}: ${n}</span>`).join("") || `<span class="muted">Queue empty — generate a day in “Today”.</span>`;
  const list = $("#list", root);
  list.innerHTML = "";
  for (const it of data.items) list.appendChild(queueCard(it, root));
};

function queueCard(it, root) {
  const c = it.candidate || {};
  const q = it.quality_avg?.toFixed?.(1) ?? "–";
  const m = it.mission_total?.toFixed?.(2) ?? "–";
  const badges = [
    `<span class="badge pillar">${esc(it.pillar || "—")}</span>`,
    `<span class="badge">${esc(it.platform || "")}</span>`,
    `<span class="badge ${it.quality_passes ? "good" : "warn"}">Q ${q}</span>`,
    `<span class="badge">M ${m} · ${esc(it.mission_verdict || "")}</span>`,
    c.founder_centred ? `<span class="badge founder">founder</span>` : "",
    it.needs_human_review ? `<span class="badge bad">review</span>` : "",
    `<span class="badge">${it.asset_count || 0} assets</span>`,
  ].join("");
  const card = el(`<div class="card">
    <div class="meta"><span class="badge">${esc(it.status)}</span></div>
    <div class="hook">${esc(c.hook || "(no hook)")}</div>
    <div class="body">${esc(c.body || "")}</div>
    <div class="meta">${badges}</div>
    <div class="actions">
      <button class="btn good" data-a="approve">Approve</button>
      <button class="btn ghost" data-a="schedule-next">Schedule</button>
      <button class="btn ghost" data-a="produce">Produce</button>
      <button class="btn ghost" data-a="reject">Reject</button>
    </div></div>`);
  card.querySelectorAll("button").forEach((b) => {
    b.onclick = async () => {
      try {
        if (b.dataset.a === "produce") {
          const r = await api(`/v1/media/produce/${it.id}`, { method: "POST" });
          toast(`Produced ${r.produced} assets`);
        } else {
          const r = await api(`/v1/queue/${it.id}/${b.dataset.a}`, { method: "POST" });
          toast(r.error ? r.error : `${b.dataset.a} → ${r.status || "ok"}`);
          if (!r.error) views.queue(root);
        }
      } catch (e) { toast("Failed: " + e.message); }
    };
  });
  return card;
}

views.calendar = async (root) => {
  root.innerHTML = `<div class="row"><h2>Calendar</h2><div class="spacer"></div>
    <button class="btn ghost" id="sched">Schedule approved</button></div><div id="cal"></div>`;
  $("#sched", root).onclick = async () => {
    try {
      const q = await api("/v1/queue?status=approved");
      let n = 0;
      for (const it of q.items) { const r = await api(`/v1/queue/${it.id}/schedule-next`, { method: "POST" }); if (!r.error) n++; }
      toast(`Scheduled ${n} post(s)`); views.calendar(root);
    } catch (e) { toast("Failed: " + e.message); }
  };
  const { calendar } = await api("/v1/calendar");
  const cal = $("#cal", root);
  const days = Object.keys(calendar || {});
  if (!days.length) { cal.innerHTML = `<div class="muted">Nothing scheduled. Approve items in the Queue, then “Schedule approved”.</div>`; return; }
  cal.innerHTML = days.map((day) => `
    <div class="day"><h3>${esc(day)} · ${calendar[day].length} post(s)</h3>
      ${calendar[day].map((it) => `<div class="slot"><span class="time">${esc((it.scheduled_at || "").slice(11, 16))}</span>
        <span><span class="badge pillar">${esc(it.pillar || "")}</span> ${esc((it.candidate || {}).hook || "")}</span></div>`).join("")}
    </div>`).join("");
};

views.media = async (root) => {
  root.innerHTML = `<div class="row"><h2>Media library</h2></div><div class="cards" id="m"></div>`;
  const { assets } = await api("/v1/media");
  const m = $("#m", root);
  if (!assets.length) { m.innerHTML = `<div class="muted">No assets yet — hit “Produce” on a queued post.</div>`; return; }
  m.innerHTML = assets.map((a) => `<div class="card">
    <div class="meta"><span class="badge pillar">${esc(a.kind)}</span><span class="badge ${a.backend === "dry-run" ? "warn" : "good"}">${esc(a.backend)}</span></div>
    <div class="body">${esc(a.spec || "")}</div>
    <div class="muted" style="font-size:12px;margin-top:8px">${esc(a.path)}</div></div>`).join("");
};

views.agents = async (root) => {
  root.innerHTML = `<div class="row"><h2>Agent library</h2></div><div id="a"></div>`;
  const { agents } = await api("/v1/agents");
  const byDept = {};
  for (const a of agents) (byDept[a.department] ||= []).push(a);
  $("#a", root).innerHTML = Object.keys(byDept).sort().map((d) => `
    <div class="agentdept"><h3>${esc(d)} · ${byDept[d].length}</h3>
      ${byDept[d].map((a) => `<div class="a"><b>${esc(a.name)}</b> <span class="muted">— ${esc(a.role)}</span></div>`).join("")}
    </div>`).join("");
};

views.values = async (root) => {
  const v = await api("/v1/values");
  const mix = await api("/v1/personality/mix").catch(() => ({}));
  root.innerHTML = `
    <div class="row"><h2>Values</h2></div>
    <div class="directive"><b>Prime Directive.</b> ${esc(v.prime_directive)}</div>
    <div class="lists">
      <div class="card"><h3>Optimise for</h3><ul>${v.optimise_for.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="card"><h3>Never optimise for</h3><ul>${v.never_optimise_for.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="card"><h3>Never do</h3><ul>${v.never_do.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="card"><h3>Content mix</h3><ul>${Object.entries(mix).map(([k, val]) => `<li>${esc(k)}: ${Math.round(val * 100)}%</li>`).join("")}</ul></div>
    </div>`;
};

// --- router ----------------------------------------------------------------
async function show(name) {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  const root = $("#view"); root.innerHTML = `<div class="loading">Loading…</div>`;
  try { await views[name](root); } catch (e) { root.innerHTML = `<div class="loading">Could not load: ${esc(e.message)}</div>`; }
  location.hash = name;
}

$("#tabs").addEventListener("click", (e) => { if (e.target.dataset.view) show(e.target.dataset.view); });

refreshHealth();
show((location.hash || "#today").slice(1) in views ? location.hash.slice(1) : "today");

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});

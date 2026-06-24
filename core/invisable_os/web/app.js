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

views.integrations = async (root) => {
  const s = await api("/v1/integrations");
  const rows = Object.entries(s)
    .map(([k, on]) => `<span class="badge ${on ? "good" : "bad"}">${esc(k)}: ${on ? "configured" : "off"}</span>`)
    .join(" ");
  root.innerHTML = `
    <div class="row"><h2>Integrations</h2><div class="spacer"></div>
      <button class="btn" id="msync">Run metrics sync</button>
      <button class="btn ghost" id="damall">Sync published → DAM</button>
    </div>
    <div class="meta">${rows}</div>
    <div class="muted" id="out" style="margin-top:12px">Metrics sync feeds the Watchtower (Founder Recognition Index). DAM sync pushes finished assets to ResourceSpace. Both run safely as dry-run / no-op until their keys are set.</div>`;
  $("#msync", root).onclick = async (ev) => {
    ev.target.disabled = true;
    try {
      const r = await api("/v1/metrics/sync", { method: "POST", body: JSON.stringify({}) });
      $("#out", root).textContent = `Metrics: ingested ${r.ingested} signal(s) from ${r.source} · Founder Recognition Index ${r.founder_recognition_index}`;
      toast(`Metrics synced (${r.source})`);
    } catch (e) { toast("Failed: " + e.message); }
    ev.target.disabled = false;
  };
  $("#damall", root).onclick = async (ev) => {
    ev.target.disabled = true;
    try {
      const q = await api("/v1/queue?status=published");
      let posts = 0, files = 0;
      for (const it of (q.items || [])) {
        const r = await api(`/v1/dam/sync/${it.id}`, { method: "POST" });
        if (!r.error) { posts++; files += (r.count || 0); }
      }
      $("#out", root).textContent = `DAM: synced ${files} asset(s) across ${posts} published post(s).`;
      toast(`DAM sync: ${files} asset(s)`);
    } catch (e) { toast("Failed: " + e.message); }
    ev.target.disabled = false;
  };
};

views.recognition = async (root) => {
  const d = await api("/v1/founder/recognition");
  const hist = d.history || [];
  // The index is 0..1; render a simple bar chart so it reads left-to-right over time.
  const W = 640, H = 160, pad = 8;
  const n = hist.length;
  const bars = hist.map((p, i) => {
    const bw = n ? (W - pad * 2) / n : 0;
    const bh = Math.max(2, (p.index_value || 0) * (H - pad * 2));
    const x = pad + i * bw;
    const y = H - pad - bh;
    return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="var(--founder)"><title>${esc((p.at || "").slice(0, 16))}: ${(p.index_value || 0).toFixed(3)}</title></rect>`;
  }).join("");
  const chart = n
    ? `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" style="background:var(--panel);border:1px solid var(--line);border-radius:var(--radius)">${bars}</svg>`
    : `<div class="muted">No recognition readings yet — run a metrics sync (Integrations) once real performance arrives.</div>`;
  const latest = hist.length ? hist[hist.length - 1] : null;
  const breakdown = latest
    ? Object.entries(latest.breakdown || {}).sort((a, b) => b[1] - a[1])
        .map(([k, v]) => `<li>${esc(k)}: ${v}</li>`).join("")
    : "";
  root.innerHTML = `
    <div class="row"><h2>Founder Recognition</h2><div class="spacer"></div>
      <span class="badge founder">latest ${(d.latest || 0).toFixed(3)}</span>
      <span class="badge">${d.points || 0} reading(s)</span>
    </div>
    <div class="muted" style="margin-bottom:10px">Recognition is a consequence of impact — media mentions, podcast & speaking invitations, partner/sponsor enquiries, profile visits. Index 0–1, tracked over time.</div>
    ${chart}
    ${breakdown ? `<div class="card" style="margin-top:14px"><h3>Latest contributors</h3><ul>${breakdown}</ul></div>` : ""}`;
};

// --- Remix department: Scanner Dashboard -----------------------------------
const SCAN_LABEL = (m) => m.replace(/^scan_/, "").replace(/_/g, " ");
const CREATE_LABEL = (m) => m.replace(/^create_/, "").replace(/_/g, " ");

views.scanner = async (root) => {
  root.innerHTML = `<div class="row"><h2>Scanner Dashboard</h2></div>
    <div class="muted">Scan culture into abstracted ideas. References are stored as our
      own summary only — never a verbatim copy, never reposted as-is.</div>
    <div class="row" id="scanbtns" style="flex-wrap:wrap;gap:8px;margin-top:12px"></div>
    <div class="row" style="margin-top:12px">
      <input id="link" class="input" placeholder="Paste a link or topic…" style="flex:1" />
      <button class="btn" id="scanlink">Add reference</button>
    </div>
    <div id="scanout"></div>`;
  const btns = $("#scanbtns", root);
  try {
    const { scan_modes } = await api("/v1/remix/modes");
    for (const mode of scan_modes) {
      const b = el(`<button class="btn ghost">${esc(SCAN_LABEL(mode))}</button>`);
      b.onclick = () => runScan(root, mode);
      btns.appendChild(b);
    }
  } catch (e) { btns.innerHTML = `<span class="muted">Modes unavailable: ${esc(e.message)}</span>`; }
  $("#scanlink", root).onclick = () => {
    const v = $("#link", root).value.trim();
    if (!v) return toast("Enter a link or topic");
    addManualLink(root, v);
  };
};

async function runScan(root, mode) {
  const out = $("#scanout", root);
  out.innerHTML = `<div class="loading">Scanning…</div>`;
  try {
    const d = await api("/v1/scanner/scan", { method: "POST", body: JSON.stringify({ mode, persist: true }) });
    out.innerHTML = `<div class="card"><div class="hook">${esc(SCAN_LABEL(mode))} · ${d.count || 0} item(s)</div>
      ${(d.items || []).map((it) => `<div class="slot"><span class="badge">${(it.trend_score ?? it.score ?? 0).toFixed?.(2) ?? "–"}</span>
        <span>${esc(it.title || it.summary || "")}</span></div>`).join("")}</div>`;
    toast(`Scanned ${d.count || 0} → Reference Inbox`);
  } catch (e) { out.innerHTML = `<div class="muted">Scan failed: ${esc(e.message)}</div>`; }
}

async function addManualLink(root, value) {
  const out = $("#scanout", root);
  out.innerHTML = `<div class="loading">Classifying…</div>`;
  const body = value.startsWith("http") ? { url: value } : { topic: value };
  try {
    const d = await api("/v1/scanner/manual-link", { method: "POST", body: JSON.stringify(body) });
    const r = d.reference || {};
    out.innerHTML = `<div class="card">
      <div class="hook">${esc(r.title || r.url || value)}</div>
      <div class="meta">
        <span class="badge ${USABLE.has(r.rights_status) ? "good" : "warn"}">${esc(r.rights_status || "reference_only")}</span>
        ${r.copyright_risk ? `<span class="badge ${r.copyright_risk === "high" ? "bad" : ""}">risk: ${esc(r.copyright_risk)}</span>` : ""}
      </div>
      <h3>Suggested INVISABLE angles</h3>
      <ul>${(d.suggested_angles || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul>
      ${d.download_plan ? `<div class="muted">${esc(typeof d.download_plan === "string" ? d.download_plan : (d.download_plan.note || ""))}</div>` : ""}
    </div>`;
    toast("Added to Reference Inbox");
  } catch (e) { out.innerHTML = `<div class="muted">Failed: ${esc(e.message)}</div>`; }
}

// Rights statuses that may enter assembled media (filled from /v1/rights).
let USABLE = new Set(["owned", "licensed", "public_domain", "creative_commons", "user_submitted_consent", "platform_duet_stitch"]);

// --- Remix department: Reference Inbox -------------------------------------
views.inbox = async (root) => {
  root.innerHTML = `<div class="row"><h2>Reference Inbox</h2><div class="spacer"></div>
    <button class="btn ghost" id="refresh">Refresh</button></div><div class="cards" id="list"></div>`;
  $("#refresh", root).onclick = () => views.inbox(root);
  const { items } = await api("/v1/scanner/items");
  const list = $("#list", root);
  if (!items.length) { list.innerHTML = `<div class="muted">Nothing scanned yet — use the Scanner.</div>`; return; }
  list.innerHTML = "";
  for (const it of items) {
    const card = el(`<div class="card">
      <div class="hook">${esc(it.title || "(untitled)")}</div>
      <div class="body">${esc(it.summary || "")}</div>
      <div class="meta">
        <span class="badge">${esc(it.platform || "—")}</span>
        <span class="badge ${it.rights_status === "reference_only" ? "warn" : "good"}">${esc(it.rights_status || "")}</span>
        ${(it.risk_score ?? 0) > 0.5 ? `<span class="badge bad">risk ${it.risk_score}</span>` : ""}
      </div>
      <div class="actions"><button class="btn" data-a="remix">Generate content</button></div></div>`);
    card.querySelector("button").onclick = () => show("remix", it);
    list.appendChild(card);
  }
};

// --- Remix department: Remix Studio ----------------------------------------
views.remix = async (root, seed) => {
  root.innerHTML = `<div class="row"><h2>Remix Studio</h2></div>
    <div class="muted">Generates ORIGINAL content. Reference-only sources inspire scripts only —
      they are never downloaded or reused as footage.</div>
    <div class="form">
      <input id="topic" class="input" placeholder="Topic / trend…" value="${esc(seed?.title || seed?.topic_area || "")}" style="flex:1 1 200px" />
      <select id="mode" class="input"></select>
      <input id="ref" class="input" placeholder="Reference URL (optional)" value="${esc(seed?.url || "")}" />
      <label class="muted" style="display:flex;align-items:center;gap:6px"><input type="checkbox" id="sponsor" /> sponsor-safe</label>
      <button class="btn" id="go">Generate</button>
    </div>
    <div id="remixout"></div>`;
  try {
    const { create_modes } = await api("/v1/remix/modes");
    $("#mode", root).innerHTML = create_modes.map((m) => `<option value="${esc(m)}">${esc(CREATE_LABEL(m))}</option>`).join("");
  } catch {}
  $("#go", root).onclick = async (ev) => {
    ev.target.disabled = true;
    const body = {
      mode: $("#mode", root).value,
      topic: $("#topic", root).value.trim(),
      reference_url: $("#ref", root).value.trim(),
      sponsor_safe: $("#sponsor", root).checked,
      persist: true,
    };
    if (!body.topic && !body.reference_url) { toast("Enter a topic or reference URL"); ev.target.disabled = false; return; }
    try { renderRemix($("#remixout", root), await api("/v1/remix/create", { method: "POST", body: JSON.stringify(body) })); }
    catch (e) { toast("Failed: " + e.message); }
    ev.target.disabled = false;
  };
};

function renderRemix(node, d) {
  const packs = d.pack ? [d.pack] : (d.memes || []);
  const warn = d.rights_warning ? `<div class="directive">${esc(d.rights_warning)}</div>` : "";
  if (!packs.length) { node.innerHTML = warn + `<div class="muted">No pack returned (mode: ${esc(d.mode || "")}).</div>`; return; }
  node.innerHTML = warn + packs.map((p) => `<div class="card">
    <div class="meta">
      ${d.job_id ? `<span class="badge good">queued</span>` : ""}
      ${p.angle ? `<span class="badge pillar">${esc(p.angle)}</span>` : ""}
      ${(p.risk_score ?? 0) > 0.5 ? `<span class="badge bad">risk ${p.risk_score}</span>` : `<span class="badge">risk ${p.risk_score ?? 0}</span>`}
    </div>
    ${(p.variants || []).map((v) => `<h3>${esc(v.label || v.platform || "variant")}</h3>
      <pre class="script">${esc(v.script || "")}</pre>
      ${v.voiceover ? `<div class="muted">VO: ${esc(v.voiceover)}</div>` : ""}`).join("")}
    <h3>Caption</h3><div class="body">${esc(p.caption || "")}</div>
    <div class="meta">${(p.hashtags || []).map((h) => `<span class="badge">${esc(h)}</span>`).join("")}</div>
    ${(p.asset_suggestions || []).length ? `<h3>Rights-safe assets</h3><ul>${p.asset_suggestions.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>` : ""}
  </div>`).join("");
}

// --- Remix department: Rights Manager --------------------------------------
views.rights = async (root) => {
  root.innerHTML = `<div class="row"><h2>Rights Manager</h2></div>
    <div id="ruleinfo" class="muted"></div>
    <div class="form">
      <input id="title" class="input" placeholder="Title / file path or source URL…" style="flex:1 1 220px" />
      <select id="rstatus" class="input"></select>
      <input id="owner" class="input" placeholder="Owner (e.g. INVISABLE)" />
      <button class="btn" id="add">Register asset</button>
    </div>
    <div class="cards" id="list"></div>`;
  let info = {};
  try { info = await api("/v1/rights"); } catch {}
  if (info.usable_in_media) USABLE = new Set(info.usable_in_media);
  $("#ruleinfo", root).textContent = info.rule || "Only owned/licensed/CC/public-domain/consented/duet-stitch material may enter assembled media.";
  $("#rstatus", root).innerHTML = (info.all_statuses || [...USABLE]).map((s) =>
    `<option value="${esc(s)}">${esc(s)}${USABLE.has(s) ? " ✓" : ""}</option>`).join("");
  $("#add", root).onclick = async () => {
    const title = $("#title", root).value.trim();
    if (!title) return toast("Enter a title / path / URL");
    try {
      await api("/v1/rights-assets", { method: "POST", body: JSON.stringify({
        title, file_path: title, source_url: title.startsWith("http") ? title : "",
        rights_status: $("#rstatus", root).value, owner: $("#owner", root).value.trim() }) });
      toast("Asset registered"); views.rights(root);
    } catch (e) { toast("Failed: " + e.message); }
  };
  const { assets } = await api("/v1/rights-assets");
  const list = $("#list", root);
  if (!assets.length) { list.innerHTML = `<div class="muted">No assets yet. Only usable-rights assets can enter assembled media.</div>`; return; }
  list.innerHTML = assets.map((a) => `<div class="card">
    <div class="body">${esc(a.title || a.file_path || a.source_url)}</div>
    <div class="meta">
      <span class="badge">${esc(a.asset_type || "asset")}</span>
      <span class="badge ${USABLE.has(a.rights_status) ? "good" : "warn"}">${esc(a.rights_status)}</span>
      <span class="badge">${esc(a.owner || "—")}</span>
    </div></div>`).join("");
};

// --- Content War Chest -----------------------------------------------------
const TIER_CLASS = { below_minimum: "bad", minimum: "warn", healthy: "good", elite: "good" };

views.warchest = async (root) => {
  root.innerHTML = `<div class="row"><h2>War Chest</h2><div class="spacer"></div>
    <button class="btn ghost" id="stock">Stock approved</button>
    <button class="btn" id="select">Draw next post</button></div>
    <div class="muted">The reserve of approved, ready-to-post assets. The platform always
      generates more than it publishes — a strong reserve means post more, a thin one
      means protect it and post fewer (quality over quantity).</div>
    <div class="stats" id="wcstats"></div>
    <div id="wcdraw"></div>
    <div class="row" style="margin-top:8px"><h3 style="margin:0">By category</h3></div>
    <div class="row" id="wccats"></div>
    <div class="cards" id="wclist"></div>`;
  $("#stock", root).onclick = async () => {
    try { const r = await api("/v1/warchest/stock", { method: "POST" }); toast(`Stocked ${r.stocked} approved → reserve`); views.warchest(root); }
    catch (e) { toast("Failed: " + e.message); }
  };
  $("#select", root).onclick = async () => {
    try {
      const r = await api("/v1/warchest/select", { method: "POST", body: JSON.stringify({}) });
      const out = $("#wcdraw", root);
      if (r.error) { out.innerHTML = `<div class="muted">${esc(r.error)}</div>`; return; }
      const it = r.item;
      out.innerHTML = `<div class="card"><div class="meta">
          <span class="badge good">drawn → marked used</span>
          <span class="badge pillar">${esc(it.category)}</span>
          ${r.rotated_from_category ? `<span class="badge">rotated from ${esc(r.rotated_from_category)}</span>` : ""}
        </div><div class="hook">${esc(it.title)}</div>
        <div class="meta"><span class="badge">${esc(it.platform || "—")}</span>
          <span class="badge">Q ${(+it.quality_score).toFixed(1)}</span>
          <span class="badge">M ${(+it.mission_score).toFixed(2)}</span>
          <span class="badge">fresh ${it.freshness_score}</span></div></div>`;
      views.warchest(root);
    } catch (e) { toast("Failed: " + e.message); }
  };
  const h = await api("/v1/warchest");
  $("#wcstats", root).innerHTML = [
    ["Ready", h.ready], ["Tier", h.tier.replace("_", " ")],
    ["Posts/day", h.recommended_posts_per_day], ["Every", h.recommended_interval_minutes + "m"],
  ].map(([l, n], i) => `<div class="stat"><div class="n ${i === 1 ? (TIER_CLASS[h.tier] || "") : ""}">${esc(String(n))}</div><div class="l">${l}</div></div>`).join("");
  // Progress toward the next reserve milestone (500 / 1000 / 2000).
  $("#wcstats", root).insertAdjacentHTML("afterend",
    `<div class="muted" style="margin:6px 0">Reserve milestones — minimum ${h.thresholds.minimum} ·
      healthy ${h.thresholds.healthy} · elite ${h.thresholds.elite}.
      ${Math.round(h.progress_to_next * 100)}% to next.</div>`);
  $("#wccats", root).innerHTML = Object.entries(h.by_category || {})
    .map(([cat, n]) => `<span class="badge pillar">${esc(cat)}: ${n}</span>`).join("") || `<span class="muted">Empty — stock approved items.</span>`;
  const { items } = await api("/v1/warchest/items");
  $("#wclist", root).innerHTML = items.slice(0, 60).map((it) => `<div class="card">
    <div class="hook">${esc(it.title)}</div>
    <div class="meta">
      <span class="badge pillar">${esc(it.category)}</span>
      <span class="badge">${esc(it.platform || "—")}</span>
      <span class="badge">Q ${(+it.quality_score).toFixed(1)}</span>
      ${it.evergreen ? `<span class="badge good">evergreen</span>` : ""}
      ${it.reuse_count ? `<span class="badge warn">used ${it.reuse_count}×</span>` : ""}
    </div></div>`).join("") || `<div class="muted">No ready items. Approve content in the Queue, then “Stock approved”.</div>`;
};

// --- Remix department: Pop Culture Index -----------------------------------
const RISK_CLASS = (r) => (r === "high" ? "bad" : r === "medium" ? "warn" : "good");

views.popculture = async (root) => {
  root.innerHTML = `<div class="row"><h2>Pop Culture Index</h2></div>
    <div class="muted">Prefer paraphrase-safe, transformative wording over exact quotes —
      exact film/TV lines carry copyright risk and must not be overused.</div>
    <div class="form">
      <input id="pctitle" class="input" placeholder="Source title (film / TV / phrase / meme)…" style="flex:1 1 220px" />
      <input id="pctype" class="input" placeholder="Type (film, tv, phrase, format)" />
      <input id="pcsafe" class="input" placeholder="Paraphrase-safe version…" style="flex:1 1 220px" />
      <select id="pcrisk" class="input">
        ${["none", "low", "medium", "high"].map((r) => `<option value="${r}">risk: ${r}</option>`).join("")}
      </select>
      <button class="btn" id="pcadd">Add reference</button>
    </div>
    <div class="cards" id="pclist"></div>
    <div class="row" style="margin-top:18px"><h3>Meme formats</h3></div>
    <div class="cards" id="memes"></div>`;
  $("#pcadd", root).onclick = async () => {
    const title = $("#pctitle", root).value.trim();
    if (!title) return toast("Enter a source title");
    try {
      await api("/v1/popculture", { method: "POST", body: JSON.stringify({
        source_title: title, reference_type: $("#pctype", root).value.trim() || "film",
        paraphrase_safe: $("#pcsafe", root).value.trim(),
        copyright_risk: $("#pcrisk", root).value }) });
      toast("Reference added"); views.popculture(root);
    } catch (e) { toast("Failed: " + e.message); }
  };
  const { references } = await api("/v1/popculture");
  const list = $("#pclist", root);
  list.innerHTML = (references || []).map((r) => `<div class="card">
    <div class="hook">${esc(r.title || r.source_title || "(untitled)")}</div>
    <div class="body">${esc(r.paraphrase_safe_version || r.paraphrase_safe || r.suggested_invisable_angle || "")}</div>
    ${r.exact_quote ? `<div class="muted">Exact quote (use sparingly): “${esc(r.exact_quote)}”</div>` : ""}
    <div class="meta">
      <span class="badge pillar">${esc(r.source_type || r.reference_type || "ref")}</span>
      <span class="badge ${RISK_CLASS(r.copyright_risk)}">risk: ${esc(r.copyright_risk || "medium")}</span>
      ${r.tone ? `<span class="badge">${esc(r.tone)}</span>` : ""}
    </div></div>`).join("") || `<div class="muted">No references yet.</div>`;
  try {
    const { formats } = await api("/v1/meme-formats");
    $("#memes", root).innerHTML = (formats || []).map((f) => `<div class="card">
      <div class="hook">${esc(f.format_name || f.name || "format")}</div>
      <div class="body">${esc(f.example_safe_version || f.example_angle || f.structure || "")}</div>
      <div class="meta"><span class="badge ${RISK_CLASS(f.copyright_risk)}">risk: ${esc(f.copyright_risk ?? f.risk_score ?? "low")}</span></div>
    </div>`).join("") || `<div class="muted">No meme formats yet.</div>`;
  } catch {}
};

// --- Remix department: Voiceover Queue -------------------------------------
views.voiceover = async (root) => {
  root.innerHTML = `<div class="row"><h2>Voiceover Queue</h2></div>
    <div class="muted">Lay a voiceover over an <b>owned / licensed / permitted</b> clip only.
      Reference-only footage is blocked from assembly.</div>
    <div class="form">
      <select id="vasset" class="input" style="flex:1 1 240px"></select>
      <select id="vstyle" class="input">
        ${["founder", "narrator", "warm", "dry"].map((s) => `<option value="${s}">voice: ${s}</option>`).join("")}
      </select>
      <select id="vplatform" class="input">
        ${["tiktok", "instagram"].map((p) => `<option value="${p}">${p}</option>`).join("")}
      </select>
      <button class="btn" id="vgo">Build voiceover job</button>
    </div>
    <textarea id="vscript" class="input" placeholder="Voiceover script…" style="width:100%;min-height:90px;margin-top:10px"></textarea>
    <div id="vout"></div>`;
  let assets = [];
  try { assets = (await api("/v1/rights-assets")).assets || []; } catch {}
  const usable = assets.filter((a) => USABLE.has(a.rights_status));
  const sel = $("#vasset", root);
  if (!usable.length) {
    sel.innerHTML = `<option value="">(no usable assets — register one in Rights)</option>`;
  } else {
    sel.innerHTML = usable.map((a) =>
      `<option value="${esc(a.id)}">${esc(a.title || a.file_path || a.id)} · ${esc(a.rights_status)}</option>`).join("");
  }
  $("#vgo", root).onclick = async (ev) => {
    const asset_id = sel.value;
    const script = $("#vscript", root).value.trim();
    if (!asset_id) return toast("Register a usable asset first (Rights)");
    if (!script) return toast("Write a voiceover script");
    ev.target.disabled = true;
    try {
      const j = await api("/v1/voiceover/create", { method: "POST", body: JSON.stringify({
        asset_id, script, voice_style: $("#vstyle", root).value, platform: $("#vplatform", root).value }) });
      renderVoiceover($("#vout", root), j);
      toast(j.blocked_reason ? "Blocked: " + j.blocked_reason : "Voiceover job built");
    } catch (e) { toast("Failed: " + e.message); }
    ev.target.disabled = false;
  };
};

function renderVoiceover(node, j) {
  if (j.error) { node.innerHTML = `<div class="muted">${esc(j.error)}</div>`; return; }
  if (j.blocked_reason) {
    node.innerHTML = `<div class="directive">⛔ Blocked — ${esc(j.blocked_reason)}</div>`;
    return;
  }
  const steps = (j.ffmpeg_job && j.ffmpeg_job.steps) || [];
  node.innerHTML = `<div class="card">
    <div class="meta">
      <span class="badge good">ready</span>
      <span class="badge">${esc(j.clip_rights_status || "")}</span>
      <span class="badge pillar">${esc(j.platform || "")}</span>
      <span class="badge">export: ${esc(j.export_format || "")}</span>
    </div>
    <h3>ElevenLabs request</h3>
    <pre class="script">${esc(JSON.stringify(j.elevenlabs_request || {}, null, 2))}</pre>
    <h3>Subtitles</h3><div class="muted">format: ${esc(j.subtitle_format || "srt")} (Whisper → auto-subtitle)</div>
    <h3>FFmpeg assembly</h3>
    <div class="meta">${steps.map((s) => `<span class="badge">${esc(s)}</span>`).join("")}</div>
    <div class="muted" style="margin-top:8px">Approval: routes through the normal queue before publishing.</div>
  </div>`;
}

// --- Remix department: Asset Library ---------------------------------------
views.library = async (root) => {
  root.innerHTML = `<div class="row"><h2>Asset Library</h2><div class="spacer"></div>
    <button class="btn ghost" id="refresh">Refresh</button></div>
    <div class="muted">Rights-classified source assets. Green = may enter assembled media;
      amber = inspiration/reference only.</div>
    <div class="row" id="counts" style="flex-wrap:wrap;gap:6px;margin-top:10px"></div>
    <div class="cards" id="list"></div>`;
  $("#refresh", root).onclick = () => views.library(root);
  let assets = [];
  try { assets = (await api("/v1/rights-assets")).assets || []; } catch {}
  const counts = {};
  for (const a of assets) counts[a.rights_status] = (counts[a.rights_status] || 0) + 1;
  $("#counts", root).innerHTML = Object.entries(counts)
    .map(([s, n]) => `<span class="badge ${USABLE.has(s) ? "good" : "warn"}">${esc(s)}: ${n}</span>`).join("")
    || `<span class="muted">No assets yet — register them in Rights.</span>`;
  const list = $("#list", root);
  list.innerHTML = assets.map((a) => `<div class="card">
    <div class="body">${esc(a.title || a.file_path || a.source_url || a.id)}</div>
    <div class="meta">
      <span class="badge pillar">${esc(a.asset_type || "asset")}</span>
      <span class="badge ${USABLE.has(a.rights_status) ? "good" : "warn"}">${esc(a.rights_status)}</span>
      <span class="badge">${esc(a.owner || "—")}</span>
      ${a.licence_notes ? `<span class="badge">${esc(a.licence_notes)}</span>` : ""}
    </div></div>`).join("");
};

// --- Source Control Centre (credible sources + fact-check) ------------------
views.sources = async (root) => {
  root.innerHTML = `<div class="row"><h2>Source Control Centre</h2></div>
    <div class="muted">Any fact-led post (statistics, news, government/NHS/benefits/legal/medical
      claims, broadcast quotes) must carry a credible source. Social/community sources are for
      lived experience only — never as hard facts.</div>
    <div class="form">
      <input id="sname" class="input" placeholder="Source name (e.g. ONS, BBC News)…" style="flex:1 1 200px" />
      <select id="stype" class="input"></select>
      <input id="surl" class="input" placeholder="URL (optional)" />
      <button class="btn" id="sadd">Add source</button>
    </div>
    <div class="card">
      <h3>Fact-check a draft</h3>
      <textarea id="fctext" class="input" placeholder="Paste a draft post…" style="width:100%;min-height:70px"></textarea>
      <div class="row" style="margin-top:8px"><select id="fcsource" class="input" style="flex:1"></select>
        <button class="btn" id="fcgo">Check</button></div>
      <div id="fcout"></div>
    </div>
    <div class="cards" id="slist"></div>`;
  // Populate source-type options from the credibility hierarchy.
  let hierarchy = [];
  try { hierarchy = (await api("/v1/sources/hierarchy")).hierarchy; } catch {}
  $("#stype", root).innerHTML = hierarchy.map((h) =>
    `<option value="${esc(h.source_type)}">${esc(h.source_type)} — tier ${h.tier}</option>`).join("");
  const sources = (await api("/v1/sources")).sources || [];
  $("#fcsource", root).innerHTML = `<option value="">(no source attached)</option>` +
    sources.map((s) => `<option value="${esc(s.id)}">${esc(s.name)} · ${esc(s.source_type)}</option>`).join("");
  $("#sadd", root).onclick = async () => {
    const name = $("#sname", root).value.trim();
    if (!name) return toast("Enter a source name");
    try {
      await api("/v1/sources", { method: "POST", body: JSON.stringify({
        name, source_type: $("#stype", root).value, url: $("#surl", root).value.trim() }) });
      toast("Source added"); views.sources(root);
    } catch (e) { toast("Failed: " + e.message); }
  };
  $("#fcgo", root).onclick = async () => {
    const text = $("#fctext", root).value.trim();
    if (!text) return toast("Paste a draft to check");
    const sid = $("#fcsource", root).value;
    try {
      const v = await api("/v1/factcheck", { method: "POST", body: JSON.stringify({
        text, source_ids: sid ? [sid] : [] }) });
      $("#fcout", root).innerHTML = `<div class="meta" style="margin-top:10px">
        <span class="badge ${v.fact_led ? "warn" : ""}">${v.fact_led ? "fact-led" : "not fact-led"}</span>
        <span class="badge ${v.ok ? "good" : "bad"}">${v.ok ? "OK" : "needs a source"}</span>
        ${(v.attributions || []).map((a) => `<span class="badge good">${esc(a)}</span>`).join("")}
        ${(v.weak_sources || []).map((w) => `<span class="badge bad">weak: ${esc(w)}</span>`).join("")}
      </div>
      ${v.reasons && v.reasons.length ? `<div class="muted">Flagged because: ${v.reasons.map(esc).join("; ")}.</div>` : ""}
      <div class="muted">${esc(v.advisory)}</div>`;
    } catch (e) { toast("Failed: " + e.message); }
  };
  $("#slist", root).innerHTML = sources.map((s) => `<div class="card">
    <div class="hook">${esc(s.name)}</div>
    <div class="meta">
      <span class="badge pillar">${esc(s.source_type)}</span>
      <span class="badge ${s.credibility_level <= 3 ? "good" : s.credibility_level <= 6 ? "warn" : "bad"}">tier ${s.credibility_level}</span>
      <span class="badge">${esc(s.country || "")}</span>
      ${s.enabled ? "" : `<span class="badge bad">disabled</span>`}
    </div>
    ${s.url ? `<div class="muted" style="font-size:12px">${esc(s.url)}</div>` : ""}
  </div>`).join("") || `<div class="muted">No sources yet — add credible UK-first sources above.</div>`;
};

// --- Agent Swarm Dashboard --------------------------------------------------
const STAGE_CLASS = { scan: "pillar", generate: "", gate: "warn", schedule: "good" };

views.swarm = async (root) => {
  root.innerHTML = `<div class="row"><h2>Agent Swarm</h2><div class="spacer"></div>
    <button class="btn" id="run">Run a cycle</button></div>
    <div class="muted">20 specialist bots scan → generate → gate → stock. The swarm always
      generates more than it publishes and rejects more than it keeps — quality over volume.</div>
    <div class="stats" id="swstats"></div>
    <div id="swfunnel"></div>
    <div class="row" style="margin-top:8px"><h3 style="margin:0">The 20 bots</h3></div>
    <div id="swbots"></div>`;
  $("#run", root).onclick = async (ev) => {
    ev.target.disabled = true; ev.target.textContent = "Running…";
    try {
      const r = await api("/v1/swarm/run", { method: "POST", body: JSON.stringify({ drafts_per_topic: 2 }) });
      renderFunnel($("#swfunnel", root), r);
      toast(`Cycle: ${r.funnel.usable_drafts_queued} usable · ${r.funnel.stocked_to_war_chest} stocked`);
      loadSwarm(root);
    } catch (e) { toast("Failed: " + e.message); }
    ev.target.disabled = false; ev.target.textContent = "Run a cycle";
  };
  loadSwarm(root);
};

async function loadSwarm(root) {
  const s = await api("/v1/swarm/stats");
  $("#swstats", root).innerHTML = [
    ["Bots", s.bots], ["Produced", s.total_produced], ["Passed", s.total_passed],
    ["Pass rate", s.overall_pass_rate == null ? "–" : Math.round(s.overall_pass_rate * 100) + "%"],
  ].map(([l, n]) => `<div class="stat"><div class="n">${esc(String(n))}</div><div class="l">${l}</div></div>`).join("");
  if (s.best_bot) $("#swstats", root).insertAdjacentHTML("afterend",
    `<div class="muted" style="margin:6px 0">Best: <b>${esc(s.best_bot)}</b> · weakest: <b>${esc(s.weakest_bot || "–")}</b> ·
      reserve tier <b>${esc(s.reserve.tier.replace("_", " "))}</b> (${s.reserve.ready} ready).</div>`);
  const { bots } = await api("/v1/swarm/bots");
  const byStage = {};
  for (const b of bots) (byStage[b.stage] ||= []).push(b);
  $("#swbots", root).innerHTML = ["scan", "generate", "gate", "schedule"].filter((st) => byStage[st]).map((st) => `
    <div class="agentdept"><h3>${esc(st)} · ${byStage[st].length}</h3>
      ${byStage[st].map((b) => `<div class="a"><b>${esc(b.name)}</b>
        <span class="muted">— ${esc(b.role)}</span>
        ${b.produced ? `<span class="badge ${STAGE_CLASS[st] || ""}">${b.passed}/${b.produced}${b.pass_rate != null ? ` · ${Math.round(b.pass_rate * 100)}%` : ""}</span>` : ""}
      </div>`).join("")}
    </div>`).join("");
}

function renderFunnel(node, r) {
  const f = r.funnel;
  const rows = [
    ["Raw drafts", f.raw_drafts], ["Passed brand gate", f.passed_brand_gate],
    ["Quality passed", f.quality_passed], ["Fact-check clean", f.fact_check_clean],
    ["Usable → queue", f.usable_drafts_queued], ["Needs review", f.needs_human_review],
    ["Stocked → War Chest", f.stocked_to_war_chest], ["Brand rejected", f.brand_rejected],
  ];
  node.innerHTML = `<div class="card"><div class="meta">
      <span class="badge">cycle ${esc(r.cycle_id.slice(0, 8))}</span>
      <span class="badge ${r.reject_rate > 0 ? "warn" : ""}">reject ${Math.round(r.reject_rate * 100)}%</span>
    </div>${rows.map(([l, n]) => `<div class="slot"><span class="time" style="width:auto">${n}</span><span>${esc(l)}</span></div>`).join("")}</div>`;
}

// --- router ----------------------------------------------------------------
async function show(name, seed) {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  const root = $("#view"); root.innerHTML = `<div class="loading">Loading…</div>`;
  try { await views[name](root, seed); } catch (e) { root.innerHTML = `<div class="loading">Could not load: ${esc(e.message)}</div>`; }
  location.hash = name;
}

$("#tabs").addEventListener("click", (e) => { if (e.target.dataset.view) show(e.target.dataset.view); });

refreshHealth();
show((location.hash || "#today").slice(1) in views ? location.hash.slice(1) : "today");

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});

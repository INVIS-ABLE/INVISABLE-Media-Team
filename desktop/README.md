# INVISABLE® Media Team — Desktop

**[⬇️ Download the latest installer →](https://github.com/INVIS-ABLE/INVISABLE-Media-Team/releases/latest)** &nbsp;·&nbsp; double-click to install, then pick your role on first launch.

Native desktop apps that wrap and control the INVISABLE® Media Team PWA/API. Built
with **[Tauri](https://v2.tauri.app)** (Rust + a tiny TypeScript frontend, no heavy
runtime). One executable ships **two roles**, chosen at first launch:

| Role | Runs on | Does |
| ---- | ------- | ---- |
| 🛰️ **Command Centre** | the always-on **server** | Opens the protected PWA, shows every queue / schedule / account / worker, and gives Stephen full manual override — approve/reject/schedule/post-now, pause automation, request content. |
| 🎬 **Studio Worker** | the **5090 workstation** | Opens the same PWA, polls the server for render jobs, runs them locally (FFmpeg / Whisper / ComfyUI), reports progress, and uploads finished media back. |

> **Why Tauri, not Electron?** Tauri meets every requirement here (multi-window webview
> over the PWA, native filesystem + subprocess for the worker, OS-keychain token
> storage, a tiny signed Windows installer). Electron is only a fallback if a future
> requirement can't be met by Tauri — none is so far.

---

## Prerequisites

- **Node.js 18+** and **npm**
- **Rust** (stable) via [rustup](https://rustup.rs)
- Platform build tools for Tauri — see the
  [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/):
  - **Windows**: Microsoft C++ Build Tools + WebView2 (preinstalled on Win 10/11).
  - **Linux** (dev only): `libwebkit2gtk-4.1-dev libgtk-3-dev librsvg2-dev libsoup-3.0-dev`.
  - **macOS** (dev only): Xcode command-line tools.

## Run & build

```bash
cd desktop
npm install

npm run tauri dev      # hot-reloading dev app
npm run tauri build    # production app + installer for the current OS
```

`npm run tauri dev` boots Vite (frontend) and the Rust shell together. The frontend
also builds standalone with `npm run build` (type-checked) — useful in CI.

### Windows output

`npm run tauri build` (or the GitHub Action) produces, under
`src-tauri/target/release/bundle/`:

- `INVISABLE Media Team_0.1.0_x64-setup.exe` (NSIS installer)
- `INVISABLE Media Team_0.1.0_x64_en-US.msi` (MSI)

It's **one executable** with a first-launch **role selector** (Command Centre / Studio
Worker), so the same install runs on both the server and the 5090. (To ship two
separately-branded `.exe`s instead, duplicate `tauri.conf.json` with a different
`productName` per role and build twice — the single-exe role selector is the default
and recommended path.)

### Icons

Brand icons are committed under `src-tauri/icons/`. To regenerate the full set from a
single source PNG: `npm run icons` (runs `tauri icon src-tauri/icons/icon.png`).

### Code signing (remove the SmartScreen warning)

By default the installer is **unsigned**, so Windows SmartScreen shows an "unknown
publisher" prompt on first run (click *More info → Run anyway*). To ship a **signed**
installer, add an Authenticode certificate to the repo — the pipeline is already wired
for it and stays a no-op until the secrets exist:

1. Obtain an Authenticode code-signing certificate (OV or EV) from a CA as a `.pfx`.
2. Base64-encode it: `base64 -w0 cert.pfx` (or `certutil -encode` on Windows).
3. In **GitHub → Settings → Secrets and variables → Actions**, add:
   - `WINDOWS_CERTIFICATE` — the base64 string
   - `WINDOWS_CERTIFICATE_PASSWORD` — the `.pfx` password
4. Re-run the **Desktop build** workflow. Tauri signs + timestamps the installer
   automatically (`src-tauri/tauri.conf.json` sets `timestampUrl` + `digestAlgorithm`),
   and the SmartScreen warning goes away (EV certs clear it immediately; OV certs build
   reputation over time/downloads).

> With the secrets unset, builds are unsigned — exactly as today — so this never blocks
> the pipeline.

---

## First launch & the role selector

On first run the app shows the **role selector**. Pick:

- **Command Centre** → lands on the agency dashboard.
- **Studio Worker** → enables the local worker and lands on Worker Status.

You can change the role any time in **Settings → App Role**.

---

## Settings & server URL priority

**Settings** (in-app) saves locally — to the OS app-config dir (e.g.
`%APPDATA%/INVISABLE Media Team/settings.json`), **never** any secret:

| Setting | Purpose |
| ------- | ------- |
| Server URL | Operator override (highest priority). |
| API Base URL | Override for `/api/*`; blank = same as the server URL. |
| LAN URL | The server's LAN address, e.g. `http://192.168.1.10:8080`. |
| Cloudflare URL | `https://media.invisable.co.uk` (the protected public PWA). |
| Localhost fallback | `http://localhost:8080` (server desktop). |
| App Role | Command Centre / Studio Worker. |
| Local Worker Enabled · Start Worker On Launch | Studio worker behaviour. |
| Local Render / Upload / Warchest Folders | Worker filesystem locations. |
| Auto Connect On Launch | Resolve + connect to the server at startup. |

### Connection priority (LAN vs Cloudflare)

On connect, the app health-checks each candidate at `/api/health` and uses the **first
reachable** one, in this order:

1. **Saved custom URL**
2. **LAN URL** — preferred at home; the 5090 reaches the server directly over Ethernet.
3. **Cloudflare URL** — `media.invisable.co.uk`, for remote devices.
4. **localhost** — when running on the server itself.

The top bar shows each one's live status (Server, Cloudflare, LAN, API), so you can
see exactly which route is in use.

---

## Authentication & desktop security

- The app authenticates to the API with a **server-issued bearer token**, stored in
  **OS-safe storage** (Windows Credential Manager / macOS Keychain / Linux Secret
  Service) via the `keyring` crate — never in the settings file or the frontend.
- Set `INVISABLE_DESKTOP_TOKEN` on the server; paste the same token into
  **Settings → Authentication**. The Rust backend attaches it to every API call; the
  frontend never sees the secret.
- Controls provided: **connection status**, **authenticated/unauthenticated status**,
  **retry login**, **logout**, **clear local settings**.
- **No platform credentials** (Instagram/TikTok) or API keys live in the desktop app.
  Account connections are completed **server-side** in Postiz/n8n; the app only
  triggers server routes.

### Cloudflare Access & login

Cloudflare Access protects the PWA in the browser/webview. If an embedded webview
can't complete the Access login, the app can **open the login in your external
browser**; at home the 5090 just uses the **LAN URL** and bypasses the tunnel. See
[`cloudflare/README.md`](cloudflare/README.md) for the full tunnel + Access setup that
locks `media.invisable.co.uk` to approved users only.

---

## How the 5090 talks to the server

The **server is the source of truth** — all queues, approvals, schedules, analytics,
accounts and asset records live there. The 5090 only processes jobs and uploads
results.

```
Command Centre (server) ──creates──▶  Render job  ──┐
                                                     │  GET/POST /api/jobs/*
Studio Worker (5090) ──claims──▶ runs FFmpeg/Whisper/ComfyUI ──▶ uploads asset
                       POST /api/jobs/next/claim     │           POST /api/assets/upload
                       POST /api/jobs/{id}/progress  │           POST /api/jobs/{id}/complete
                                                     ▼
                                          Server records the result
```

Worker job kinds: `ffmpeg_render`, `whisper_caption`, `comfyui_image`,
`comfyui_video`, `audio_cleanup`, `caption_render`, `format_convert`, `upload`. The
worker invokes real local tools when present (e.g. FFmpeg with a job's `ffmpeg_args`)
and otherwise simulates the step so the pipeline is demonstrable end-to-end — either
way the job transitions are real on the server.

### API surface the apps use

`GET /api/health` · `GET /api/system/status` · `GET /api/accounts` ·
`GET /api/queue` · `GET /api/warchest` · `GET /api/jobs` · `GET /api/jobs/render` ·
`POST /api/jobs/create` · `POST /api/jobs/{id}/claim` · `POST /api/jobs/next/claim` ·
`POST /api/jobs/{id}/progress` · `POST /api/jobs/{id}/complete` ·
`POST /api/jobs/{id}/cancel` · `POST /api/assets/upload` ·
`POST /api/posts/{id}/approve|reject|schedule|post-now|push-to-story|recycle` ·
`POST /api/automation/pause|resume` · `POST /api/content/request`.

These are served by the core (`core/invisable_os/api/desktop_routes.py`) and gated by
`INVISABLE_DESKTOP_TOKEN` when set.

---

## Running each role

### Command Centre (on the server)

1. Install the app on the server desktop.
2. First launch → choose **Command Centre**.
3. Settings → set the LAN/Cloudflare URLs and paste the API token → **Connect**.
4. You now have the live dashboard: every queue, the warchest, account status,
   render jobs, and the manual-override buttons (pause/resume automation, request
   content, approve/reject/schedule/post-now). Stephen can open it any time and see
   exactly what the system is doing.

### Studio Worker (on the 5090)

1. Install the app on the 5090.
2. First launch → choose **Studio Worker** (enables the local worker).
3. Settings → set the **LAN URL** (preferred at home), worker folders, paste the
   token, and optionally **Start Worker On Launch** → **Connect**.
4. **Worker Status** → **Start Local Worker**. It claims jobs, shows live render
   progress, and uploads finished media. Tool status (FFmpeg / Whisper / ComfyUI) is
   shown there too.

---

## Navigation

Dashboard · Accounts · Content Factory · Warchest · Approval Queue · Scheduled Posts ·
Published Posts · Rejected Posts · Story Queue · Reels Queue · Render Jobs · Worker
Status · **Platform Health** · Logs · Settings.

Top bar: server / Cloudflare / LAN / API / worker / emergency-pause status and the
Compliance **Risk** level, plus pending jobs, failed jobs, posts scheduled today,
items to review, posting **Mode**, and account **Health**.

---

## Platform Compliance Watchdog (Platform Health)

A safety agent that keeps the accounts alive, trusted, compliant and human-led. **It
only ever monitors, warns, pauses and downgrades — it never performs or bypasses any
platform action** (no auto-follow/like/DM, no CAPTCHA/login/security bypass, no spam).
If growth conflicts with account safety, safety wins.

The **Platform Health** page shows the account health score, current posting mode and
its limits, risk level, every compliance warning with a recommended action, shadowban
warning signals, reach/engagement trends, and the recent platform-event feed.

**Posting modes** (daily limits, auto-enforced):

| Mode | Posts/day | Notes |
| ---- | --------- | ----- |
| Introduction | 1–3 | all manual approval, no auto comments/reposts |
| Modest Growth | 3–6 | story pushes; comments drafted for approval only |
| Active Influencer | 6–12 | trend reactions; strict duplicate checks |
| Career | 12–20 | only when account health is strong |
| Manual Only | 0 | automation off; Stephen posts by hand |

When risk rises the Watchdog **forces a downgrade** (Career → Active → Modest →
Introduction → Manual Only) and pauses automation; on CRITICAL it stops posting.

**Risk levels**: LOW continue · MEDIUM warn + review · HIGH pause automation + manual
approval · CRITICAL stop posting + emergency.

**Emergency buttons** (each only *stops* things): Pause All Automation · Manual Mode
Only · Stop Comments · Stop Reposts · Stop Story Pushes · Stop Scheduling · Clear
Today's Queue · Account Cooldown Mode.

Integrations feed safety events to `POST /api/compliance/events` (warnings, failed/
removed posts, API errors, login/security prompts, reach/engagement drops, blocked
comments). The Watchdog reads them via `GET /api/compliance/health`; `POST
/api/compliance/evaluate` runs it and enforces the outcome.

---

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| Top bar shows everything red | The server isn't reachable on any candidate URL. Check the server is up (`invisable serve`), and that your LAN/Cloudflare URLs in Settings are correct. |
| Connected, but API is red / 401 | Token mismatch. Ensure `INVISABLE_DESKTOP_TOKEN` on the server equals the token saved in Settings → Authentication. Use **Retry login**, or **Logout** and re-paste. |
| Cloudflare shows "requires login" | Expected — the host is up but Access wants a login. Use the external-browser login, or switch to the LAN URL at home. |
| Worker won't start | Connect to the server first, and make sure a token is set (the worker needs it to claim jobs). |
| FFmpeg/Whisper show ○ on the 5090 | The tool isn't on `PATH`. Install it (or set `COMFYUI_BASE_URL`); jobs still complete in simulated mode without them. |
| `cargo`/webkit errors on Linux dev | Install the Tauri Linux deps listed under Prerequisites. The shipped target is Windows; Linux is dev-only. |
| Want two named `.exe`s | Build twice with a per-role `productName` in `tauri.conf.json`; the single-exe role selector is the default. |

---

## Layout

```
desktop/
├── index.html, vite.config.ts, tsconfig.json, package.json
├── src/                     # TypeScript frontend (no framework)
│   ├── main.ts              # role gate → shell (sidebar + topbar + view)
│   ├── lib/                 # tauri bridge, store, types, dom helpers
│   └── ui/                  # role selector, topbar, nav, views, actions, settings
├── src-tauri/               # Rust backend
│   ├── Cargo.toml, tauri.conf.json, build.rs
│   ├── capabilities/        # window permissions
│   ├── icons/               # app icons (committed)
│   └── src/
│       ├── main.rs, lib.rs  # commands + Tauri setup
│       ├── settings.rs      # local settings (JSON in app-config dir)
│       ├── token.rs         # API token in the OS keychain
│       ├── api.rs           # URL-priority resolve + authed API + upload
│       └── worker.rs        # the 5090 render-job loop
└── cloudflare/              # tunnel + Access config that locks the PWA
```

// Settings screen: server URLs, role, worker options, folders, auth, danger zone.

import { el } from "../lib/dom";
import {
  clearSettings,
  connect,
  get,
  loadSettings,
  logout,
  refreshAuth,
  saveSettings,
  setToken,
} from "../lib/store";
import type { AppRole, Settings } from "../lib/types";

function field(
  label: string,
  input: HTMLElement,
  hint?: string,
): HTMLElement {
  return el(
    "label",
    { class: "field" },
    el("span", { class: "field__label" }, label),
    input,
    hint ? el("span", { class: "field__hint" }, hint) : "",
  );
}

function textInput(value: string, placeholder = ""): HTMLInputElement {
  return el("input", { class: "input", type: "text", value, placeholder }) as HTMLInputElement;
}

function checkbox(checked: boolean): HTMLInputElement {
  return el("input", { class: "checkbox", type: "checkbox", checked }) as HTMLInputElement;
}

export function settingsView(onChange: () => void): HTMLElement {
  const s = get().settings;
  if (!s) {
    void loadSettings().then(onChange);
    return el("div", { class: "loading" }, "Loading settings…");
  }

  // --- inputs ---
  const serverUrl = textInput(s.server_url, "https://… (custom override)");
  const apiBase = textInput(s.api_base_url, "blank = same as server URL");
  const lanUrl = textInput(s.lan_url, "http://192.168.x.x:8080");
  const cfUrl = textInput(s.cloudflare_url, "https://media.invisable.co.uk");
  const localhostUrl = textInput(s.localhost_url, "http://localhost:8080");

  const roleSelect = el(
    "select",
    { class: "input" },
    el("option", { value: "command_centre", ...(s.role === "command_centre" ? { selected: "selected" } : {}) }, "Command Centre"),
    el("option", { value: "studio_worker", ...(s.role === "studio_worker" ? { selected: "selected" } : {}) }, "Studio Worker"),
  ) as HTMLSelectElement;

  const autoConnect = checkbox(s.auto_connect_on_launch);
  const workerEnabled = checkbox(s.local_worker_enabled);
  const startOnLaunch = checkbox(s.start_worker_on_launch);
  const workerId = textInput(s.worker_id, "studio-5090");
  const pollSeconds = el("input", { class: "input", type: "number", min: "1", value: String(s.worker_poll_seconds) }) as HTMLInputElement;
  const jobKinds = textInput(s.worker_job_kinds.join(", "), "blank = all kinds");

  const renderFolder = textInput(s.local_render_folder, "C:\\INVISABLE\\render");
  const uploadFolder = textInput(s.upload_folder, "C:\\INVISABLE\\upload");
  const warchestFolder = textInput(s.warchest_folder, "C:\\INVISABLE\\warchest");

  const tokenInput = el("input", { class: "input", type: "password", placeholder: "paste server-issued API token" }) as HTMLInputElement;

  async function save() {
    const next: Settings = {
      ...s!,
      server_url: serverUrl.value.trim(),
      api_base_url: apiBase.value.trim(),
      lan_url: lanUrl.value.trim(),
      cloudflare_url: cfUrl.value.trim(),
      localhost_url: localhostUrl.value.trim(),
      role: roleSelect.value as AppRole,
      auto_connect_on_launch: autoConnect.checked,
      local_worker_enabled: workerEnabled.checked,
      start_worker_on_launch: startOnLaunch.checked,
      worker_id: workerId.value.trim() || "studio-5090",
      worker_poll_seconds: Math.max(1, Number(pollSeconds.value) || 5),
      worker_job_kinds: jobKinds.value
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
      local_render_folder: renderFolder.value.trim(),
      upload_folder: uploadFolder.value.trim(),
      warchest_folder: warchestFolder.value.trim(),
    };
    await saveSettings(next);
    onChange();
  }

  const authenticated = get().authenticated;

  return el(
    "div",
    { class: "settings" },
    el(
      "section",
      { class: "panel" },
      el("h2", { class: "panel__title" }, "Server connection"),
      el("p", { class: "muted" }, "Priority: custom URL → LAN → Cloudflare → localhost. The first that answers /api/health wins."),
      field("Server URL (custom override)", serverUrl),
      field("API Base URL", apiBase, "Leave blank to use the server URL."),
      field("LAN URL", lanUrl, "Preferred when the 5090 is on the home network."),
      field("Cloudflare URL", cfUrl, "The protected public PWA."),
      field("Localhost fallback", localhostUrl),
      field("App Role", roleSelect),
      el("label", { class: "field field--inline" }, autoConnect, el("span", {}, "Auto connect on launch")),
      el(
        "div",
        { class: "btn-row" },
        el("button", { class: "btn btn--ok", onclick: () => void save() }, "Save settings"),
        el("button", { class: "btn btn--info", onclick: () => void connect() }, "Test / Connect now"),
      ),
    ),
    el(
      "section",
      { class: "panel" },
      el("h2", { class: "panel__title" }, "Authentication"),
      el(
        "p",
        { class: authenticated ? "banner banner--ok" : "banner banner--warn" },
        authenticated ? "Authenticated — token stored in OS keychain." : "Not authenticated.",
      ),
      field("Server-issued API token", tokenInput, "Stored securely in the OS keychain — never in plain settings."),
      el(
        "div",
        { class: "btn-row" },
        el(
          "button",
          {
            class: "btn btn--ok",
            onclick: () => {
              if (tokenInput.value.trim()) void setToken(tokenInput.value.trim()).then(onChange);
            },
          },
          "Save token",
        ),
        el("button", { class: "btn btn--ghost", onclick: () => void refreshAuth().then(onChange) }, "Retry login"),
        el("button", { class: "btn btn--bad", onclick: () => void logout().then(onChange) }, "Logout"),
      ),
      el("p", { class: "muted" }, "Cloudflare Access login that an embedded webview can't complete should be done in your browser; the desktop app uses the server-issued token here for the API."),
    ),
    el(
      "section",
      { class: "panel" },
      el("h2", { class: "panel__title" }, "Studio worker (5090)"),
      el("label", { class: "field field--inline" }, workerEnabled, el("span", {}, "Local Worker Enabled")),
      el("label", { class: "field field--inline" }, startOnLaunch, el("span", {}, "Start Worker On Launch")),
      field("Worker ID", workerId),
      field("Poll interval (seconds)", pollSeconds),
      field("Job kinds", jobKinds, "Comma-separated; blank = claim all kinds."),
      el("div", { class: "btn-row" }, el("button", { class: "btn btn--ok", onclick: () => void save() }, "Save")),
    ),
    el(
      "section",
      { class: "panel" },
      el("h2", { class: "panel__title" }, "Folders"),
      field("Local Render Folder", renderFolder),
      field("Upload Folder", uploadFolder),
      field("Warchest Folder", warchestFolder),
      el("div", { class: "btn-row" }, el("button", { class: "btn btn--ok", onclick: () => void save() }, "Save")),
    ),
    el(
      "section",
      { class: "panel panel--danger" },
      el("h2", { class: "panel__title" }, "Danger zone"),
      el(
        "div",
        { class: "btn-row" },
        el(
          "button",
          {
            class: "btn btn--bad",
            onclick: () => {
              void clearSettings()
                .then(() => loadSettings())
                .then(onChange);
            },
          },
          "Clear local settings",
        ),
      ),
      el("p", { class: "muted" }, "Resets this device's settings and returns to the role selector. The token is kept; use Logout to remove it."),
    ),
  );
}

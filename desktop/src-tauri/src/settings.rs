//! Local, on-disk settings for the desktop app.
//!
//! Saved as JSON in the OS app-config directory (e.g. `%APPDATA%/INVISABLE Media
//! Team/settings.json` on Windows). No secrets live here — the server-issued API
//! token is kept separately in the OS keychain (see [`crate::token`]).

use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager};

/// Which face of the app this install runs as.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AppRole {
    /// Not chosen yet — the first-launch role selector is shown.
    #[default]
    Unset,
    /// Server/admin app: full agency dashboard + manual override.
    CommandCentre,
    /// 5090 workstation app: render worker that processes + uploads jobs.
    StudioWorker,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    /// First-launch role choice. `Unset` → show the role selector.
    pub role: AppRole,

    // --- Connection -------------------------------------------------------
    /// Operator-set custom URL (highest priority when reachable).
    pub server_url: String,
    /// Convenience base for the API; defaults to `{server_url}` when blank.
    pub api_base_url: String,
    /// LAN address of the server (preferred at home over Cloudflare).
    pub lan_url: String,
    /// Cloudflare-protected public PWA URL.
    pub cloudflare_url: String,
    /// Localhost fallback (server desktop / co-located dev).
    pub localhost_url: String,
    /// Connect to the server automatically on launch.
    pub auto_connect_on_launch: bool,

    // --- Studio worker ----------------------------------------------------
    /// Enable the local production worker (Studio role).
    pub local_worker_enabled: bool,
    /// Start the worker automatically when the app launches.
    pub start_worker_on_launch: bool,
    /// Stable id this worker reports to the server.
    pub worker_id: String,
    /// How often (seconds) the worker polls for new jobs.
    pub worker_poll_seconds: u64,
    /// Job kinds this worker is allowed to claim (empty = all).
    pub worker_job_kinds: Vec<String>,

    // --- Folders ----------------------------------------------------------
    pub local_render_folder: String,
    pub upload_folder: String,
    pub warchest_folder: String,
}

impl Default for Settings {
    fn default() -> Self {
        Settings {
            role: AppRole::Unset,
            server_url: String::new(),
            api_base_url: String::new(),
            lan_url: "http://192.168.1.10:8080".to_string(),
            cloudflare_url: "https://media.invisable.co.uk".to_string(),
            localhost_url: "http://localhost:8080".to_string(),
            auto_connect_on_launch: true,
            local_worker_enabled: false,
            start_worker_on_launch: false,
            worker_id: "studio-5090".to_string(),
            worker_poll_seconds: 5,
            worker_job_kinds: vec![],
            local_render_folder: String::new(),
            upload_folder: String::new(),
            warchest_folder: String::new(),
        }
    }
}

impl Settings {
    /// The base used for `/api/*` calls: explicit override, else the resolved server.
    pub fn effective_api_base(&self, resolved_server: &str) -> String {
        if !self.api_base_url.trim().is_empty() {
            self.api_base_url.trim_end_matches('/').to_string()
        } else {
            resolved_server.trim_end_matches('/').to_string()
        }
    }
}

fn config_path(app: &AppHandle) -> Result<PathBuf, String> {
    let dir = app
        .path()
        .app_config_dir()
        .map_err(|e| format!("no app config dir: {e}"))?;
    std::fs::create_dir_all(&dir).map_err(|e| format!("create config dir: {e}"))?;
    Ok(dir.join("settings.json"))
}

pub fn load(app: &AppHandle) -> Settings {
    match config_path(app).and_then(|p| {
        std::fs::read_to_string(&p).map_err(|e| format!("read settings: {e}"))
    }) {
        Ok(raw) => serde_json::from_str(&raw).unwrap_or_default(),
        Err(_) => Settings::default(),
    }
}

pub fn save(app: &AppHandle, settings: &Settings) -> Result<(), String> {
    let path = config_path(app)?;
    let raw = serde_json::to_string_pretty(settings).map_err(|e| e.to_string())?;
    std::fs::write(&path, raw).map_err(|e| format!("write settings: {e}"))
}

pub fn clear(app: &AppHandle) -> Result<(), String> {
    if let Ok(path) = config_path(app) {
        if path.exists() {
            std::fs::remove_file(&path).map_err(|e| format!("delete settings: {e}"))?;
        }
    }
    Ok(())
}

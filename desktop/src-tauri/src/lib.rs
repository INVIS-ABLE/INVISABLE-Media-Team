//! INVISABLE® Media Team desktop app — Tauri backend.
//!
//! One executable, two roles (Command Centre / Studio Worker) chosen at first launch.
//! The Rust side owns everything that must not live in the frontend: local settings,
//! the OS-keychain API token, server-URL priority resolution, authenticated API
//! calls, asset uploads, and the 5090 worker loop.

mod api;
mod settings;
mod token;
mod worker;

use std::sync::atomic::Ordering;

use serde::Serialize;
use tauri::{AppHandle, Manager, State};

use settings::Settings;
use worker::{WorkerConfig, WorkerState};

// --- Settings commands ------------------------------------------------------

#[tauri::command]
fn get_settings(app: AppHandle) -> Settings {
    settings::load(&app)
}

#[tauri::command]
fn save_settings(app: AppHandle, new_settings: Settings) -> Result<Settings, String> {
    settings::save(&app, &new_settings)?;
    Ok(new_settings)
}

#[tauri::command]
fn clear_settings(app: AppHandle) -> Result<(), String> {
    settings::clear(&app)
}

// --- Token (auth) commands --------------------------------------------------

#[derive(Serialize)]
struct AuthStatus {
    authenticated: bool,
}

#[tauri::command]
fn auth_status() -> AuthStatus {
    AuthStatus {
        authenticated: token::exists(),
    }
}

#[tauri::command]
fn set_token(value: String) -> Result<(), String> {
    if value.trim().is_empty() {
        return Err("token is empty".into());
    }
    token::set(value.trim())
}

#[tauri::command]
fn logout() -> Result<(), String> {
    token::clear()
}

// --- Connection / API commands ----------------------------------------------

#[tauri::command]
async fn resolve_connection(settings: Settings) -> api::ConnectionReport {
    api::resolve(&settings).await
}

#[tauri::command]
async fn api_request(request: api::ApiRequest) -> api::ApiResponse {
    api::request(request).await
}

#[tauri::command]
async fn upload_asset(
    base_url: String,
    file_path: String,
    job_id: Option<String>,
    queue_item_id: Option<String>,
    kind: Option<String>,
) -> api::ApiResponse {
    api::upload_asset(
        &base_url,
        &file_path,
        &job_id.unwrap_or_default(),
        &queue_item_id.unwrap_or_default(),
        &kind.unwrap_or_else(|| "render".into()),
    )
    .await
}

// --- Worker commands --------------------------------------------------------

#[derive(Serialize)]
struct WorkerStatus {
    running: bool,
    ffmpeg: bool,
    whisper: bool,
    comfyui_env: bool,
}

#[tauri::command]
fn worker_status(state: State<'_, WorkerState>) -> WorkerStatus {
    WorkerStatus {
        running: state.running.load(Ordering::SeqCst),
        ffmpeg: worker::which("ffmpeg").is_some(),
        whisper: worker::which("whisper").is_some(),
        comfyui_env: std::env::var("COMFYUI_BASE_URL").is_ok(),
    }
}

#[tauri::command]
fn start_worker(
    app: AppHandle,
    state: State<'_, WorkerState>,
    config: WorkerConfig,
) -> Result<(), String> {
    if state.running.load(Ordering::SeqCst) {
        return Err("worker already running".into());
    }
    if config.base_url.trim().is_empty() {
        return Err("no server URL — connect first".into());
    }
    worker::spawn(app, state.running.clone(), config);
    Ok(())
}

#[tauri::command]
fn stop_worker(state: State<'_, WorkerState>) -> Result<(), String> {
    worker::stop(&state.running);
    Ok(())
}

// --- External browser (Cloudflare Access login fallback) --------------------

#[tauri::command]
fn open_external(app: AppHandle, url: String) -> Result<(), String> {
    use tauri_plugin_opener::OpenerExt;
    app.opener()
        .open_url(url, None::<String>)
        .map_err(|e| format!("open external: {e}"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .manage(WorkerState::default())
        .invoke_handler(tauri::generate_handler![
            get_settings,
            save_settings,
            clear_settings,
            auth_status,
            set_token,
            logout,
            resolve_connection,
            api_request,
            upload_asset,
            worker_status,
            start_worker,
            stop_worker,
            open_external,
        ])
        .setup(|app| {
            // Ensure the config dir exists early so first save never races.
            let _ = app.path().app_config_dir();
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running INVISABLE Media Team");
}

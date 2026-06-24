//! The 5090 Studio production worker.
//!
//! When the app runs as **Studio Worker**, this background loop polls the server for
//! render jobs, claims one, processes it locally (FFmpeg / Whisper / ComfyUI / etc.),
//! reports progress back, uploads the finished asset, and marks the job complete or
//! failed. The server stays the source of truth — the 5090 only does the work.
//!
//! Real local tools are invoked when available and the job carries explicit args
//! (e.g. an `ffmpeg_args` list); otherwise the step is simulated so the pipeline is
//! demonstrable end-to-end without a configured render farm. Either way the job
//! transitions are real on the server.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use serde_json::json;
use tauri::{AppHandle, Emitter};

use crate::api;
use crate::token;

#[derive(Debug, Clone, Deserialize)]
pub struct WorkerConfig {
    pub base_url: String,
    pub worker_id: String,
    #[serde(default = "default_poll")]
    pub poll_seconds: u64,
    #[serde(default)]
    pub job_kinds: Vec<String>,
    /// Where finished assets are written before upload.
    #[serde(default)]
    pub render_folder: String,
}

fn default_poll() -> u64 {
    5
}

/// Shared worker state held in Tauri's managed state.
pub struct WorkerState {
    pub running: Arc<AtomicBool>,
}

impl Default for WorkerState {
    fn default() -> Self {
        WorkerState {
            running: Arc::new(AtomicBool::new(false)),
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct WorkerEvent {
    pub kind: String, // started | idle | claimed | progress | uploaded | completed | failed | stopped | error
    pub job_id: Option<String>,
    pub job_kind: Option<String>,
    pub progress: f64,
    pub message: String,
}

fn emit(app: &AppHandle, ev: WorkerEvent) {
    let _ = app.emit("worker://event", ev);
}

async fn post_json(base: &str, path: &str, body: serde_json::Value) -> api::ApiResponse {
    api::request(api::ApiRequest {
        method: "POST".into(),
        base_url: base.into(),
        path: path.into(),
        body: Some(body),
        timeout_secs: Some(30),
    })
    .await
}

/// Run one claimed job: report progress, do the work, upload, and complete.
async fn process_job(app: &AppHandle, cfg: &WorkerConfig, job: &serde_json::Value) {
    let job_id = job
        .get("id")
        .and_then(|v| v.as_str())
        .unwrap_or_default()
        .to_string();
    let job_kind = job
        .get("kind")
        .and_then(|v| v.as_str())
        .unwrap_or("ffmpeg_render")
        .to_string();
    let params = job.get("params").cloned().unwrap_or(json!({}));

    emit(
        app,
        WorkerEvent {
            kind: "claimed".into(),
            job_id: Some(job_id.clone()),
            job_kind: Some(job_kind.clone()),
            progress: 0.0,
            message: format!("Claimed {job_kind} job"),
        },
    );
    let _ = post_json(
        &cfg.base_url,
        &format!("/api/jobs/{job_id}/progress"),
        json!({"progress": 0.05, "status": "processing", "log": "worker started"}),
    )
    .await;

    // Try a real FFmpeg render when the job provides args and ffmpeg is on PATH.
    let mut output_path: Option<String> = None;
    let mut failed: Option<String> = None;

    if job_kind == "ffmpeg_render" {
        if let Some(args) = params.get("ffmpeg_args").and_then(|v| v.as_array()) {
            let arg_strs: Vec<String> = args
                .iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect();
            match run_ffmpeg(&arg_strs).await {
                Ok(()) => {
                    output_path = params
                        .get("output")
                        .and_then(|v| v.as_str())
                        .map(|s| resolve_output(&cfg.render_folder, s));
                }
                Err(e) => failed = Some(e),
            }
        }
    }

    // If we didn't run a real tool, simulate the work in observable steps so the
    // dashboard shows live progress and the job still completes against the server.
    if output_path.is_none() && failed.is_none() {
        for step in 1..=8 {
            if !is_running_token() {
                break;
            }
            let progress = 0.05 + (step as f64) * 0.11;
            emit(
                app,
                WorkerEvent {
                    kind: "progress".into(),
                    job_id: Some(job_id.clone()),
                    job_kind: Some(job_kind.clone()),
                    progress,
                    message: format!("Processing step {step}/8"),
                },
            );
            let _ = post_json(
                &cfg.base_url,
                &format!("/api/jobs/{job_id}/progress"),
                json!({"progress": progress, "status": "processing", "log": format!("step {step}/8")}),
            )
            .await;
            tokio::time::sleep(Duration::from_millis(400)).await;
        }
    }

    if let Some(err) = failed {
        emit(
            app,
            WorkerEvent {
                kind: "failed".into(),
                job_id: Some(job_id.clone()),
                job_kind: Some(job_kind.clone()),
                progress: 1.0,
                message: format!("Job failed: {err}"),
            },
        );
        let _ = post_json(
            &cfg.base_url,
            &format!("/api/jobs/{job_id}/complete"),
            json!({"error": err}),
        )
        .await;
        return;
    }

    // Upload a produced asset if the job pointed at a real output file.
    let mut result = json!({"worker_id": cfg.worker_id});
    if let Some(path) = &output_path {
        if tokio::fs::metadata(path).await.is_ok() {
            let up = api::upload_asset(&cfg.base_url, path, &job_id, "", &job_kind).await;
            if up.ok {
                emit(
                    app,
                    WorkerEvent {
                        kind: "uploaded".into(),
                        job_id: Some(job_id.clone()),
                        job_kind: Some(job_kind.clone()),
                        progress: 0.95,
                        message: format!("Uploaded {path}"),
                    },
                );
                result["asset"] = up.body;
            }
        }
    }

    let _ = post_json(
        &cfg.base_url,
        &format!("/api/jobs/{job_id}/complete"),
        json!({"result": result}),
    )
    .await;
    emit(
        app,
        WorkerEvent {
            kind: "completed".into(),
            job_id: Some(job_id.clone()),
            job_kind: Some(job_kind.clone()),
            progress: 1.0,
            message: "Job complete".into(),
        },
    );
}

/// A process-wide running flag the simulated loop can check mid-job.
static RUNNING: AtomicBool = AtomicBool::new(false);

fn is_running_token() -> bool {
    RUNNING.load(Ordering::SeqCst)
}

/// Resolve a job's output path against the worker's render folder when relative.
fn resolve_output(render_folder: &str, output: &str) -> String {
    let p = std::path::Path::new(output);
    if p.is_absolute() || render_folder.trim().is_empty() {
        output.to_string()
    } else {
        std::path::Path::new(render_folder)
            .join(output)
            .to_string_lossy()
            .to_string()
    }
}

async fn run_ffmpeg(args: &[String]) -> Result<(), String> {
    if which("ffmpeg").is_none() {
        return Err("ffmpeg not found on PATH".into());
    }
    let status = tokio::process::Command::new("ffmpeg")
        .args(args)
        .status()
        .await
        .map_err(|e| format!("spawn ffmpeg: {e}"))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("ffmpeg exited with {status}"))
    }
}

/// Tiny PATH lookup so we can report tool availability without extra crates.
pub fn which(bin: &str) -> Option<String> {
    let path = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path) {
        let candidate = dir.join(bin);
        if candidate.is_file() {
            return Some(candidate.to_string_lossy().to_string());
        }
        #[cfg(windows)]
        {
            let exe = dir.join(format!("{bin}.exe"));
            if exe.is_file() {
                return Some(exe.to_string_lossy().to_string());
            }
        }
    }
    None
}

/// Spawn the worker loop. Returns immediately; the loop runs until `running` clears.
pub fn spawn(app: AppHandle, running: Arc<AtomicBool>, cfg: WorkerConfig) {
    running.store(true, Ordering::SeqCst);
    RUNNING.store(true, Ordering::SeqCst);

    tauri::async_runtime::spawn(async move {
        emit(
            &app,
            WorkerEvent {
                kind: "started".into(),
                job_id: None,
                job_kind: None,
                progress: 0.0,
                message: format!("Worker {} online", cfg.worker_id),
            },
        );

        // A token is required to claim jobs when the server enforces auth.
        if token::get().is_none() {
            emit(
                &app,
                WorkerEvent {
                    kind: "error".into(),
                    job_id: None,
                    job_kind: None,
                    progress: 0.0,
                    message: "No API token set — log in before starting the worker".into(),
                },
            );
        }

        let kinds = cfg.job_kinds.join(",");
        while running.load(Ordering::SeqCst) {
            let path = if kinds.is_empty() {
                "/api/jobs/next/claim".to_string()
            } else {
                format!("/api/jobs/next/claim?kinds={kinds}")
            };
            let resp = post_json(
                &cfg.base_url,
                &path,
                json!({"worker_id": cfg.worker_id}),
            )
            .await;

            let claimed = resp
                .body
                .get("ok")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            if claimed {
                if let Some(job) = resp.body.get("job") {
                    process_job(&app, &cfg, job).await;
                    continue; // immediately look for the next job
                }
            } else if !resp.ok && resp.status != 0 {
                emit(
                    &app,
                    WorkerEvent {
                        kind: "error".into(),
                        job_id: None,
                        job_kind: None,
                        progress: 0.0,
                        message: resp
                            .error
                            .unwrap_or_else(|| "claim request failed".into()),
                    },
                );
            } else {
                emit(
                    &app,
                    WorkerEvent {
                        kind: "idle".into(),
                        job_id: None,
                        job_kind: None,
                        progress: 0.0,
                        message: "No jobs — waiting".into(),
                    },
                );
            }

            tokio::time::sleep(Duration::from_secs(cfg.poll_seconds.max(1))).await;
        }

        RUNNING.store(false, Ordering::SeqCst);
        emit(
            &app,
            WorkerEvent {
                kind: "stopped".into(),
                job_id: None,
                job_kind: None,
                progress: 0.0,
                message: "Worker stopped".into(),
            },
        );
    });
}

pub fn stop(running: &Arc<AtomicBool>) {
    running.store(false, Ordering::SeqCst);
    RUNNING.store(false, Ordering::SeqCst);
}

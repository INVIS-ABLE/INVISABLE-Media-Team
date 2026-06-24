//! HTTP client to the INVISABLE server API + server-URL priority resolution.
//!
//! Server URL priority (the spec):
//!   1. saved custom URL
//!   2. LAN URL if available
//!   3. Cloudflare URL
//!   4. localhost fallback
//!
//! Every candidate is health-checked at `/api/health`; the first reachable one wins.
//! The bearer token (from the OS keychain) is attached to every non-health request,
//! so credentials never touch the frontend.

use std::time::Duration;

use serde::{Deserialize, Serialize};

use crate::settings::Settings;
use crate::token;

fn client(timeout: Duration) -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .timeout(timeout)
        // Cloudflare Access / login may redirect; let the app see that explicitly.
        .redirect(reqwest::redirect::Policy::limited(5))
        .user_agent("INVISABLE-Media-Desktop/0.1")
        .build()
        .map_err(|e| format!("http client: {e}"))
}

fn join(base: &str, path: &str) -> String {
    format!(
        "{}/{}",
        base.trim_end_matches('/'),
        path.trim_start_matches('/')
    )
}

/// Per-candidate reachability result, surfaced in the UI status row.
#[derive(Debug, Clone, Serialize)]
pub struct CandidateStatus {
    pub label: String,
    pub url: String,
    pub reachable: bool,
    pub status_code: Option<u16>,
    /// True when the endpoint answered but demands Cloudflare Access / auth login.
    pub auth_required: bool,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ConnectionReport {
    /// The chosen base URL (first reachable by priority), if any.
    pub server_url: Option<String>,
    pub api_base_url: Option<String>,
    pub connected: bool,
    pub candidates: Vec<CandidateStatus>,
}

async fn probe(label: &str, base: &str) -> CandidateStatus {
    let url = join(base, "/api/health");
    let mut out = CandidateStatus {
        label: label.to_string(),
        url: base.to_string(),
        reachable: false,
        status_code: None,
        auth_required: false,
        detail: String::new(),
    };
    let cl = match client(Duration::from_secs(4)) {
        Ok(c) => c,
        Err(e) => {
            out.detail = e;
            return out;
        }
    };
    match cl.get(&url).send().await {
        Ok(resp) => {
            let code = resp.status().as_u16();
            out.status_code = Some(code);
            // A Cloudflare Access challenge typically answers 302/401/403 here.
            if code == 401 || code == 403 || code == 302 {
                out.auth_required = true;
                out.detail = "reachable but requires login (Cloudflare Access)".into();
                out.reachable = true; // the host is up; auth is a separate step
            } else if resp.status().is_success() {
                out.reachable = true;
                out.detail = "ok".into();
            } else {
                out.detail = format!("unexpected status {code}");
            }
        }
        Err(e) => {
            out.detail = if e.is_timeout() {
                "timed out".into()
            } else if e.is_connect() {
                "no route / refused".into()
            } else {
                format!("{e}")
            };
        }
    }
    out
}

/// Ordered, de-duplicated list of (label, url) candidates from settings.
fn candidates(settings: &Settings) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    let mut push = |label: &str, url: &str| {
        let u = url.trim().trim_end_matches('/').to_string();
        if !u.is_empty() && !out.iter().any(|(_, e)| e == &u) {
            out.push((label.to_string(), u));
        }
    };
    push("Custom", &settings.server_url);
    push("LAN", &settings.lan_url);
    push("Cloudflare", &settings.cloudflare_url);
    push("Localhost", &settings.localhost_url);
    out
}

/// Resolve the server URL by priority, health-checking each candidate.
pub async fn resolve(settings: &Settings) -> ConnectionReport {
    let mut report = ConnectionReport {
        server_url: None,
        api_base_url: None,
        connected: false,
        candidates: Vec::new(),
    };
    for (label, url) in candidates(settings) {
        let status = probe(&label, &url).await;
        let chosen = status.reachable;
        if chosen && report.server_url.is_none() {
            report.server_url = Some(url.clone());
            report.api_base_url = Some(settings.effective_api_base(&url));
            report.connected = true;
        }
        report.candidates.push(status);
    }
    report
}

#[derive(Debug, Clone, Serialize)]
pub struct ApiResponse {
    pub ok: bool,
    pub status: u16,
    pub body: serde_json::Value,
    pub error: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ApiRequest {
    pub method: String,
    pub base_url: String,
    pub path: String,
    #[serde(default)]
    pub body: Option<serde_json::Value>,
    #[serde(default)]
    pub timeout_secs: Option<u64>,
}

/// Make an authenticated API call. The bearer token is read from the keychain here,
/// so the frontend issues high-level requests without ever handling the secret.
pub async fn request(req: ApiRequest) -> ApiResponse {
    let timeout = Duration::from_secs(req.timeout_secs.unwrap_or(20));
    let cl = match client(timeout) {
        Ok(c) => c,
        Err(e) => {
            return ApiResponse {
                ok: false,
                status: 0,
                body: serde_json::Value::Null,
                error: Some(e),
            }
        }
    };
    let url = join(&req.base_url, &req.path);
    let method = reqwest::Method::from_bytes(req.method.to_uppercase().as_bytes())
        .unwrap_or(reqwest::Method::GET);

    let mut builder = cl.request(method, &url);
    if let Some(tok) = token::get() {
        builder = builder.bearer_auth(tok);
    }
    if let Some(body) = req.body {
        builder = builder.json(&body);
    }

    match builder.send().await {
        Ok(resp) => {
            let status = resp.status().as_u16();
            let ok = resp.status().is_success();
            let text = resp.text().await.unwrap_or_default();
            let body = serde_json::from_str(&text)
                .unwrap_or(serde_json::Value::String(text));
            ApiResponse {
                ok,
                status,
                body,
                error: if ok {
                    None
                } else {
                    Some(format!("HTTP {status}"))
                },
            }
        }
        Err(e) => ApiResponse {
            ok: false,
            status: 0,
            body: serde_json::Value::Null,
            error: Some(format!("{e}")),
        },
    }
}

/// Upload a finished asset file to the server (multipart) — used by the worker and
/// the "Upload Finished Asset" button.
pub async fn upload_asset(
    base_url: &str,
    file_path: &str,
    job_id: &str,
    queue_item_id: &str,
    kind: &str,
) -> ApiResponse {
    let cl = match client(Duration::from_secs(600)) {
        Ok(c) => c,
        Err(e) => {
            return ApiResponse {
                ok: false,
                status: 0,
                body: serde_json::Value::Null,
                error: Some(e),
            }
        }
    };
    let bytes = match tokio::fs::read(file_path).await {
        Ok(b) => b,
        Err(e) => {
            return ApiResponse {
                ok: false,
                status: 0,
                body: serde_json::Value::Null,
                error: Some(format!("read {file_path}: {e}")),
            }
        }
    };
    let filename = std::path::Path::new(file_path)
        .file_name()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| "asset.bin".to_string());

    let part = reqwest::multipart::Part::bytes(bytes).file_name(filename);
    let form = reqwest::multipart::Form::new().part("file", part);
    let url = format!(
        "{}/api/assets/upload?job_id={}&queue_item_id={}&kind={}",
        base_url.trim_end_matches('/'),
        urlencode(job_id),
        urlencode(queue_item_id),
        urlencode(kind),
    );
    let mut builder = cl.post(&url).multipart(form);
    if let Some(tok) = token::get() {
        builder = builder.bearer_auth(tok);
    }
    match builder.send().await {
        Ok(resp) => {
            let status = resp.status().as_u16();
            let ok = resp.status().is_success();
            let text = resp.text().await.unwrap_or_default();
            let body =
                serde_json::from_str(&text).unwrap_or(serde_json::Value::String(text));
            ApiResponse {
                ok,
                status,
                body,
                error: if ok { None } else { Some(format!("HTTP {status}")) },
            }
        }
        Err(e) => ApiResponse {
            ok: false,
            status: 0,
            body: serde_json::Value::Null,
            error: Some(format!("{e}")),
        },
    }
}

/// Minimal URL-component encoder for query params (avoids pulling a crate).
fn urlencode(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for b in s.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(b as char)
            }
            _ => out.push_str(&format!("%{:02X}", b)),
        }
    }
    out
}

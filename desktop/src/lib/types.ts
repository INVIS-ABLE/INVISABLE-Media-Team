// Shared types mirroring the Rust backend + server API shapes.

export type AppRole = "unset" | "command_centre" | "studio_worker";

export interface Settings {
  role: AppRole;
  server_url: string;
  api_base_url: string;
  lan_url: string;
  cloudflare_url: string;
  localhost_url: string;
  auto_connect_on_launch: boolean;
  local_worker_enabled: boolean;
  start_worker_on_launch: boolean;
  worker_id: string;
  worker_poll_seconds: number;
  worker_job_kinds: string[];
  local_render_folder: string;
  upload_folder: string;
  warchest_folder: string;
}

export interface CandidateStatus {
  label: string;
  url: string;
  reachable: boolean;
  status_code: number | null;
  auth_required: boolean;
  detail: string;
}

export interface ConnectionReport {
  server_url: string | null;
  api_base_url: string | null;
  connected: boolean;
  candidates: CandidateStatus[];
}

export interface ApiResponse<T = unknown> {
  ok: boolean;
  status: number;
  body: T;
  error: string | null;
}

export interface WorkerStatus {
  running: boolean;
  ffmpeg: boolean;
  whisper: boolean;
  comfyui_env: boolean;
}

export interface WorkerEvent {
  kind: string;
  job_id: string | null;
  job_kind: string | null;
  progress: number;
  message: string;
}

export interface SystemStatus {
  ok: boolean;
  version: string;
  queue_counts: Record<string, number>;
  pending_jobs: number;
  processing_jobs: number;
  failed_jobs: number;
  completed_jobs: number;
  job_counts: Record<string, number>;
  posts_scheduled_today: number;
  pending_review: number;
  automation_paused: boolean;
  automation_reason: string;
  posting_paused: boolean;
  paused_accounts: string[];
  emergency_pause: boolean;
  compliance_risk?: string;
  posting_mode?: string;
  account_health?: number;
  mode_downgrade_suggested?: boolean;
  integrations: Record<string, boolean>;
}

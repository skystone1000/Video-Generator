export type RuntimeName = "mock" | "hunyuan_original" | "hunyuan_15" | "diffusers_hunyuan";

export type JobStatus =
  | "queued"
  | "loading_model"
  | "generating"
  | "postprocessing"
  | "completed"
  | "failed"
  | "cancelled";

export interface GenerationRequest {
  prompt: string;
  negative_prompt: string;
  aspect_ratio: string;
  resolution: string;
  width: number;
  height: number;
  video_length: number;
  fps: number;
  steps: number;
  seed: number | null;
  cfg_scale: number;
  flow_shift: number;
  use_cpu_offload: boolean;
  use_fp8: boolean;
  rewrite_prompt: boolean;
  preset: string;
  runtime: RuntimeName;
}

export interface Job {
  id: number;
  status: JobStatus;
  prompt: string;
  negative_prompt: string;
  rewritten_prompt: string | null;
  seed: number;
  runtime: string;
  model_version: string | null;
  settings: GenerationRequest;
  progress: number;
  current_stage: string;
  output_asset_id: number | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Asset {
  id: number;
  job_id: number;
  file_path: string;
  thumbnail_path: string | null;
  preview_path: string | null;
  metadata_path: string | null;
  duration_seconds: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  favorite: boolean;
  tags: string[];
  created_at: string;
}

export interface Preset {
  id: number;
  name: string;
  description: string;
  settings: Partial<GenerationRequest>;
  created_at: string;
  updated_at: string;
}

export interface SystemStatus {
  status: string;
  runtime: string;
  model_loaded: boolean;
  queue_depth: number;
  active_job_id: number | null;
  offline_mode: boolean;
}

import { useSyncExternalStore } from "react";

import type { Asset, GenerationRequest, Job, Preset, SystemStatus } from "../api/types";

interface GenerationState {
  status: SystemStatus | null;
  jobs: Job[];
  assets: Asset[];
  presets: Preset[];
  selectedJobId: number | null;
  selectedAssetId: number | null;
  loading: boolean;
  error: string | null;
}

let state: GenerationState = {
  status: null,
  jobs: [],
  assets: [],
  presets: [],
  selectedJobId: null,
  selectedAssetId: null,
  loading: false,
  error: null
};

const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

export const defaultRequest: GenerationRequest = {
  prompt: "cinematic shot of a futuristic city at sunrise, slow drifting camera",
  negative_prompt: "",
  aspect_ratio: "16:9",
  resolution: "480p",
  width: 854,
  height: 480,
  video_length: 29,
  fps: 24,
  steps: 12,
  seed: null,
  cfg_scale: 6,
  flow_shift: 5,
  use_cpu_offload: true,
  use_fp8: false,
  rewrite_prompt: false,
  preset: "hunyuan-480p-fast",
  runtime: "hunyuan_15"
};

export function setGenerationState(patch: Partial<GenerationState>) {
  state = { ...state, ...patch };
  emit();
}

export function useGenerationStore() {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => state
  );
}

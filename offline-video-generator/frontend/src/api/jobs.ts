import { api } from "./client";
import type { Asset, GenerationRequest, Job, Preset, SystemStatus } from "./types";

export function getStatus() {
  return api.get<SystemStatus>("/api/system/status");
}

export function listPresets() {
  return api.get<Preset[]>("/api/presets");
}

export function createJob(payload: GenerationRequest) {
  return api.post<Job>("/api/jobs", payload);
}

export function listJobs() {
  return api.get<Job[]>("/api/jobs");
}

export function cancelJob(jobId: number) {
  return api.post<Job>(`/api/jobs/${jobId}/cancel`);
}

export function rerunJob(jobId: number) {
  return api.post<Job>(`/api/jobs/${jobId}/rerun`);
}

export function createVariation(jobId: number) {
  return api.post<Job>(`/api/jobs/${jobId}/variation`, {});
}

export function listAssets() {
  return api.get<Asset[]>("/api/assets");
}

export function patchAsset(assetId: number, payload: { favorite?: boolean; tags?: string[] }) {
  return api.patch<Asset>(`/api/assets/${assetId}`, payload);
}

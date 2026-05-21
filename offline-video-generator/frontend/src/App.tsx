import { useEffect, useMemo, useState } from "react";

import { AssetGallery } from "./components/AssetGallery";
import { PreviewPanel } from "./components/PreviewPanel";
import { PromptPanel } from "./components/PromptPanel";
import { QueuePanel } from "./components/QueuePanel";
import { SettingsPanel } from "./components/SettingsPanel";
import {
  cancelJob,
  createJob,
  createVariation,
  getStatus,
  listAssets,
  listJobs,
  listPresets,
  patchAsset,
  rerunJob
} from "./api/jobs";
import type { GenerationRequest, Preset } from "./api/types";
import { defaultRequest, setGenerationState, useGenerationStore } from "./state/useGenerationStore";

function applyPreset(request: GenerationRequest, preset: Preset): GenerationRequest {
  return {
    ...request,
    ...preset.settings,
    prompt: request.prompt,
    negative_prompt: request.negative_prompt,
    seed: request.seed,
    preset: preset.name
  };
}

export default function App() {
  const store = useGenerationStore();
  const [request, setRequest] = useState<GenerationRequest>(defaultRequest);

  const selectedJob = useMemo(
    () => store.jobs.find((job) => job.id === store.selectedJobId) ?? store.jobs[0] ?? null,
    [store.jobs, store.selectedJobId]
  );
  const selectedAsset = useMemo(
    () =>
      store.assets.find((asset) => asset.id === store.selectedAssetId) ??
      store.assets.find((asset) => asset.id === selectedJob?.output_asset_id) ??
      store.assets[0] ??
      null,
    [store.assets, store.selectedAssetId, selectedJob]
  );

  async function refresh() {
    try {
      const [status, jobs, assets, presets] = await Promise.all([
        getStatus(),
        listJobs(),
        listAssets(),
        listPresets()
      ]);
      setGenerationState({ status, jobs, assets, presets, error: null });
    } catch (error) {
      setGenerationState({ error: error instanceof Error ? error.message : "Unable to reach backend." });
    }
  }

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 1500);
    return () => window.clearInterval(timer);
  }, []);

  async function submit() {
    setGenerationState({ loading: true, error: null });
    try {
      const job = await createJob(request);
      setGenerationState({ selectedJobId: job.id, selectedAssetId: null });
      await refresh();
    } catch (error) {
      setGenerationState({ error: error instanceof Error ? error.message : "Job submission failed." });
    } finally {
      setGenerationState({ loading: false });
    }
  }

  async function runJobAction(action: () => Promise<unknown>) {
    try {
      await action();
      await refresh();
    } catch (error) {
      setGenerationState({ error: error instanceof Error ? error.message : "Action failed." });
    }
  }

  const hasActiveJob = store.jobs.some((job) =>
    ["queued", "loading_model", "generating", "postprocessing"].includes(job.status)
  );

  return (
    <main className="appShell">
      <aside className="leftRail">
        <PromptPanel
          request={request}
          presets={store.presets}
          disabled={store.loading}
          onChange={(patch) => setRequest((current) => ({ ...current, ...patch }))}
          onGenerate={submit}
          onRandomSeed={() =>
            setRequest((current) => ({ ...current, seed: Math.floor(Math.random() * 2_147_483_647) }))
          }
          onApplyPreset={(preset) => setRequest((current) => applyPreset(current, preset))}
        />
        <SettingsPanel request={request} onChange={(patch) => setRequest((current) => ({ ...current, ...patch }))} />
      </aside>

      <section className="centerStage">
        <PreviewPanel
          job={selectedJob}
          asset={selectedAsset}
          error={store.error}
          onRerun={(jobId) => runJobAction(() => rerunJob(jobId))}
          onVariation={(jobId) => runJobAction(() => createVariation(jobId))}
        />
        <AssetGallery
          assets={store.assets}
          selectedAssetId={store.selectedAssetId}
          onSelect={(assetId) => setGenerationState({ selectedAssetId: assetId })}
          onFavorite={(asset) => runJobAction(() => patchAsset(asset.id, { favorite: !asset.favorite }))}
        />
      </section>

      <aside className="rightRail">
        <section className="panel systemPanel">
          <div className="panelHeader">
            <h2>System</h2>
            <span className={hasActiveJob ? "activity active" : "activity"} />
          </div>
          <dl className="systemFacts">
            <div>
              <dt>Runtime</dt>
              <dd>{store.status?.runtime ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Queue</dt>
              <dd>{store.status?.queue_depth ?? 0}</dd>
            </div>
            <div>
              <dt>Active</dt>
              <dd>{store.status?.active_job_id ?? "none"}</dd>
            </div>
          </dl>
        </section>
        <QueuePanel
          jobs={store.jobs}
          selectedJobId={store.selectedJobId}
          onSelect={(jobId) => setGenerationState({ selectedJobId: jobId, selectedAssetId: null })}
          onCancel={(jobId) => runJobAction(() => cancelJob(jobId))}
          onRerun={(jobId) => runJobAction(() => rerunJob(jobId))}
        />
      </aside>
    </main>
  );
}

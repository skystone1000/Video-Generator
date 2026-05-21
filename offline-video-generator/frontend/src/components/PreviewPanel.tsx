import { AlertCircle, RotateCcw, Wand2 } from "lucide-react";

import { assetVideoUrl } from "../api/client";
import type { Asset, Job } from "../api/types";
import { JobStatusBadge } from "./JobStatusBadge";

interface PreviewPanelProps {
  job: Job | null;
  asset: Asset | null;
  error: string | null;
  onRerun: (jobId: number) => void;
  onVariation: (jobId: number) => void;
}

export function PreviewPanel({ job, asset, error, onRerun, onVariation }: PreviewPanelProps) {
  const playableAssetId = asset?.id ?? job?.output_asset_id ?? null;

  return (
    <section className="previewSurface">
      <div className="previewHeader">
        <div>
          <h1>Offline Video Generator</h1>
          <p>{job ? job.current_stage : "Ready"}</p>
        </div>
        {job ? <JobStatusBadge status={job.status} /> : null}
      </div>

      <div className="videoFrame">
        {playableAssetId ? (
          <video controls src={assetVideoUrl(playableAssetId)} />
        ) : (
          <div className="emptyPreview">No output selected</div>
        )}
      </div>

      {job ? (
        <div className="progressBlock">
          <div className="progressTrack">
            <div className="progressFill" style={{ width: `${Math.round(job.progress * 100)}%` }} />
          </div>
          <div className="metaRow">
            <span>Job #{job.id}</span>
            <span>{Math.round(job.progress * 100)}%</span>
            <span>{job.runtime}</span>
            <span>Seed {job.seed}</span>
          </div>
        </div>
      ) : null}

      {job?.error_message || error ? (
        <div className="errorBox">
          <AlertCircle size={18} />
          <span>{job?.error_message ?? error}</span>
        </div>
      ) : null}

      {job ? (
        <div className="actionRow">
          <button className="iconTextButton" onClick={() => onRerun(job.id)}>
            <RotateCcw size={17} />
            <span>Rerun</span>
          </button>
          <button className="iconTextButton" onClick={() => onVariation(job.id)}>
            <Wand2 size={17} />
            <span>Variation</span>
          </button>
        </div>
      ) : null}
    </section>
  );
}

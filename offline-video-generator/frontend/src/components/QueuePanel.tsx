import { Ban, RotateCcw } from "lucide-react";

import type { Job } from "../api/types";
import { JobStatusBadge } from "./JobStatusBadge";

interface QueuePanelProps {
  jobs: Job[];
  selectedJobId: number | null;
  onSelect: (jobId: number) => void;
  onCancel: (jobId: number) => void;
  onRerun: (jobId: number) => void;
}

export function QueuePanel({ jobs, selectedJobId, onSelect, onCancel, onRerun }: QueuePanelProps) {
  return (
    <section className="panel queuePanel">
      <div className="panelHeader">
        <h2>Queue</h2>
        <span className="countPill">{jobs.length}</span>
      </div>

      <div className="jobList">
        {jobs.length === 0 ? <div className="quietText">No jobs yet</div> : null}
        {jobs.map((job) => (
          <div
            key={job.id}
            className={`jobItem ${selectedJobId === job.id ? "selected" : ""}`}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(job.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") onSelect(job.id);
            }}
          >
            <div className="jobItemTop">
              <strong>#{job.id}</strong>
              <JobStatusBadge status={job.status} />
            </div>
            <p>{job.prompt}</p>
            <div className="jobActions">
              <button
                type="button"
                title="Cancel"
                onClick={(event) => {
                  event.stopPropagation();
                  onCancel(job.id);
                }}
              >
                <Ban size={15} />
              </button>
              <button
                type="button"
                title="Rerun"
                onClick={(event) => {
                  event.stopPropagation();
                  onRerun(job.id);
                }}
              >
                <RotateCcw size={15} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

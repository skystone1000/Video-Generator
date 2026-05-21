import type { JobStatus } from "../api/types";

const labels: Record<JobStatus, string> = {
  queued: "Queued",
  loading_model: "Loading",
  generating: "Generating",
  postprocessing: "Post",
  completed: "Done",
  failed: "Failed",
  cancelled: "Cancelled"
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return <span className={`statusBadge status-${status}`}>{labels[status]}</span>;
}

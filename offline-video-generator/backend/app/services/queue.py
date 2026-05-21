import json
import random
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Asset, Job, JobStatus
from ..schemas import GenerationRequest
from .model_manager import model_manager
from .storage import job_output_dir, safe_relative_or_absolute, write_metadata
from .thumbnails import create_thumbnail, probe_video


TERMINAL_STATES = {JobStatus.completed.value, JobStatus.failed.value, JobStatus.cancelled.value}


class CancellationRequested(RuntimeError):
    pass


class GenerationQueue:
    def __init__(self) -> None:
        self.active_job_id: int | None = None
        self._cancel_requested: set[int] = set()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, name="generation-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def queue_depth(self, session: Session) -> int:
        return session.scalar(select(func.count()).select_from(Job).where(Job.status == JobStatus.queued.value)) or 0

    def enqueue(self, session: Session, request: GenerationRequest) -> Job:
        seed = request.seed if request.seed is not None else random.randint(0, 2_147_483_647)
        payload = request.model_copy(update={"seed": seed}).model_dump()
        job = Job(
            status=JobStatus.queued.value,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            seed=seed,
            runtime=request.runtime,
            settings_json=json.dumps(payload),
            progress=0.0,
            current_stage="queued",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    def request_cancel(self, session: Session, job_id: int) -> Job:
        job = session.get(Job, job_id)
        if not job:
            raise KeyError(job_id)
        if job.status == JobStatus.queued.value:
            job.status = JobStatus.cancelled.value
            job.current_stage = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(job)
            return job
        if job.id == self.active_job_id and job.status not in TERMINAL_STATES:
            with self._lock:
                self._cancel_requested.add(job_id)
            job.current_stage = "cancellation requested"
            session.commit()
            session.refresh(job)
            return job
        return job

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            with SessionLocal() as session:
                job = session.scalar(
                    select(Job)
                    .where(Job.status == JobStatus.queued.value)
                    .order_by(Job.created_at.asc(), Job.id.asc())
                    .limit(1)
                )
                if job:
                    self._run_job(session, job)
            time.sleep(0.5)

    def _cancel_was_requested(self, job_id: int) -> bool:
        with self._lock:
            return job_id in self._cancel_requested

    def _clear_cancel(self, job_id: int) -> None:
        with self._lock:
            self._cancel_requested.discard(job_id)

    def _update_job(
        self,
        session: Session,
        job: Job,
        *,
        status: JobStatus | None = None,
        progress: float | None = None,
        stage: str | None = None,
        error: str | None = None,
    ) -> None:
        if status is not None:
            job.status = status.value
        if progress is not None:
            job.progress = max(0.0, min(1.0, progress))
        if stage is not None:
            job.current_stage = stage
        if error is not None:
            job.error_message = error
        session.commit()
        session.refresh(job)

    def _run_job(self, session: Session, job: Job) -> None:
        self.active_job_id = job.id
        try:
            request = GenerationRequest.model_validate(json.loads(job.settings_json))
            job.started_at = datetime.now(timezone.utc)
            self._update_job(session, job, status=JobStatus.loading_model, progress=0.01, stage="loading model")

            adapter = model_manager.load(request.runtime)

            output_dir = job_output_dir(job.id, job.created_at)

            def progress_callback(progress: float, stage: str, message: str | None = None) -> None:
                if self._cancel_was_requested(job.id):
                    raise CancellationRequested("Generation was cancelled by the user.")
                mapped_status = JobStatus.postprocessing if stage == "postprocessing" else JobStatus.generating
                self._update_job(
                    session,
                    job,
                    status=mapped_status,
                    progress=progress,
                    stage=message or stage,
                )

            result = adapter.generate(request, output_dir, progress_callback)

            self._update_job(session, job, status=JobStatus.postprocessing, progress=0.92, stage="creating asset")
            thumbnail_path = create_thumbnail(result.video_path, output_dir)
            video_info = probe_video(result.video_path)
            metadata_path = result.metadata_path or write_metadata(
                output_dir,
                {
                    "job_id": job.id,
                    "runtime": request.runtime,
                    "prompt": request.prompt,
                    "negative_prompt": request.negative_prompt,
                    "seed": request.seed,
                    "settings": request.model_dump(),
                    "created_at": job.created_at.isoformat(),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "output_file": result.video_path.name,
                },
            )
            asset = Asset(
                job_id=job.id,
                file_path=safe_relative_or_absolute(result.video_path) or "",
                thumbnail_path=safe_relative_or_absolute(thumbnail_path),
                preview_path=None,
                metadata_path=safe_relative_or_absolute(metadata_path),
                duration_seconds=video_info["duration_seconds"] or max(1, request.video_length / request.fps),
                fps=video_info["fps"] or request.fps,
                width=video_info["width"] or request.width,
                height=video_info["height"] or request.height,
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)

            job.output_asset_id = asset.id
            job.model_version = result.model_version or adapter.model_version
            job.completed_at = datetime.now(timezone.utc)
            self._update_job(session, job, status=JobStatus.completed, progress=1.0, stage="completed")
        except CancellationRequested as exc:
            job.completed_at = datetime.now(timezone.utc)
            self._update_job(session, job, status=JobStatus.cancelled, progress=job.progress, stage="cancelled", error=str(exc))
        except Exception as exc:
            job.completed_at = datetime.now(timezone.utc)
            self._update_job(session, job, status=JobStatus.failed, progress=job.progress, stage="failed", error=str(exc))
        finally:
            self._clear_cancel(job.id)
            self.active_job_id = None


generation_queue = GenerationQueue()

import asyncio
import json
import random

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_session
from ..models import Job, JobStatus
from ..schemas import GenerationRequest, JobRead, JobVariationRequest
from ..services.queue import TERMINAL_STATES, generation_queue
from ..services.serialization import job_to_read

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=201)
def create_job(request: GenerationRequest, session: Session = Depends(get_session)) -> JobRead:
    job = generation_queue.enqueue(session, request)
    return job_to_read(job)


@router.get("", response_model=list[JobRead])
def list_jobs(session: Session = Depends(get_session)) -> list[JobRead]:
    jobs = session.scalars(select(Job).order_by(Job.created_at.desc(), Job.id.desc()).limit(100)).all()
    return [job_to_read(job) for job in jobs]


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, session: Session = Depends(get_session)) -> JobRead:
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job_to_read(job)


@router.post("/{job_id}/cancel", response_model=JobRead)
def cancel_job(job_id: int, session: Session = Depends(get_session)) -> JobRead:
    try:
        job = generation_queue.request_cancel(session, job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found.") from None
    return job_to_read(job)


@router.post("/{job_id}/rerun", response_model=JobRead, status_code=201)
def rerun_job(job_id: int, session: Session = Depends(get_session)) -> JobRead:
    source = session.get(Job, job_id)
    if not source:
        raise HTTPException(status_code=404, detail="Job not found.")
    request = GenerationRequest.model_validate(json.loads(source.settings_json))
    job = generation_queue.enqueue(session, request)
    return job_to_read(job)


@router.post("/{job_id}/variation", response_model=JobRead, status_code=201)
def create_variation(
    job_id: int,
    variation: JobVariationRequest | None = None,
    session: Session = Depends(get_session),
) -> JobRead:
    source = session.get(Job, job_id)
    if not source:
        raise HTTPException(status_code=404, detail="Job not found.")
    payload = json.loads(source.settings_json)
    if variation and variation.prompt:
        payload["prompt"] = variation.prompt
    payload["seed"] = variation.seed if variation and variation.seed is not None else random.randint(0, 2_147_483_647)
    request = GenerationRequest.model_validate(payload)
    job = generation_queue.enqueue(session, request)
    return job_to_read(job)


@router.websocket("/{job_id}/events")
async def job_events(websocket: WebSocket, job_id: int) -> None:
    await websocket.accept()
    try:
        while True:
            with SessionLocal() as session:
                job = session.get(Job, job_id)
                if not job:
                    await websocket.send_json({"type": "error", "detail": "Job not found."})
                    await websocket.close(code=1008)
                    return
                await websocket.send_json({"type": "job", "job": job_to_read(job).model_dump(mode="json")})
                if job.status in TERMINAL_STATES:
                    await websocket.close(code=1000)
                    return
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return

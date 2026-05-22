import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_session
from ..schemas import GpuStatus, SystemStatus
from ..services.model_manager import model_manager
from ..services.queue import generation_queue

router = APIRouter(prefix="/system", tags=["system"])

_gpu_cache: dict = {"ts": 0.0, "result": None}
_GPU_TTL = 15.0  # seconds


@router.get("/status", response_model=SystemStatus)
def get_status(session: Session = Depends(get_session)) -> SystemStatus:
    settings = get_settings()
    return SystemStatus(
        status="ok",
        runtime=settings.video_runtime,
        model_loaded=model_manager.loaded_runtime is not None,
        queue_depth=generation_queue.queue_depth(session),
        active_job_id=generation_queue.active_job_id,
        offline_mode=True,
    )


@router.get("/gpu", response_model=GpuStatus)
def get_gpu() -> GpuStatus:
    now = time.time()
    if _gpu_cache["result"] is not None and now - _gpu_cache["ts"] < _GPU_TTL:
        return _gpu_cache["result"]

    try:
        import torch
    except Exception as exc:
        result = GpuStatus(available=False, error=f"PyTorch unavailable: {exc}")
        _gpu_cache.update({"ts": now, "result": result})
        return result

    try:
        available = bool(torch.cuda.is_available())
        devices = []
        if available:
            for index in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(index)
                devices.append(
                    {
                        "index": index,
                        "name": torch.cuda.get_device_name(index),
                        "total_memory_gb": round(props.total_memory / (1024**3), 2),
                    }
                )
        result = GpuStatus(available=available, devices=devices)
    except Exception as exc:
        result = GpuStatus(available=False, error=str(exc))

    _gpu_cache.update({"ts": now, "result": result})
    return result

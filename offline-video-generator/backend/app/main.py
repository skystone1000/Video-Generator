import logging
import warnings
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import assets, jobs, presets, system
from .config import get_settings
from .database import SessionLocal, init_db
from .services.presets import seed_default_presets
from .services.queue import generation_queue


def _configure_logging() -> None:
    settings = get_settings()
    log_file = settings.resolved_log_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def _warn_missing_paths() -> None:
    settings = get_settings()
    runtime = settings.video_runtime
    if runtime == "hunyuan_15":
        for label, raw in [
            ("HUNYUAN_15_REPO_PATH", settings.hunyuan_15_repo_path),
            ("HUNYUAN_15_MODEL_PATH", settings.hunyuan_15_model_path),
        ]:
            resolved = settings.resolve_path(raw)
            if resolved is None or not resolved.exists():
                warnings.warn(
                    f"{label} is set to {raw!r} but the path does not exist. "
                    "Generation jobs will fail until the path is corrected.",
                    stacklevel=1,
                )
                logging.getLogger(__name__).warning(
                    "%s not found: %s", label, resolved
                )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    _warn_missing_paths()
    init_db()
    with SessionLocal() as session:
        seed_default_presets(session)
    generation_queue.start()
    try:
        yield
    finally:
        generation_queue.stop()


app = FastAPI(
    title="Offline Video Generator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/api")
app.include_router(presets.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(assets.router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "offline-video-generator"}

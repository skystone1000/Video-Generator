from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import assets, jobs, presets, system
from .database import SessionLocal, init_db
from .services.presets import seed_default_presets
from .services.queue import generation_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
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

# Implementation Spec: Offline Text-to-Video Creator Pipeline

Original implementation prompt used to scaffold this project.

## Build Status

All core phases are implemented. Current known gaps tracked in [FEATURES.md](FEATURES.md).

**Completed:**

- FastAPI backend scaffold with system, jobs, assets, and presets endpoints.
- SQLite job, asset, and preset models with full state machine (`queued → loading_model → generating → postprocessing → completed/failed/cancelled`).
- Local single-worker generation queue (daemon thread, polls every 0.5 s).
- Mock video runtime with `ffmpeg testsrc2` or static sample fallback.
- HunyuanVideo-1.5 subprocess adapter — Windows-compatible: calls `python.exe generate.py` directly (not `torchrun`) with `HashStore` for distributed init to avoid the libuv dependency absent from Windows PyTorch builds.
- React + Vite creator workspace wired to backend APIs.
- `ffmpeg`/`ffprobe` verified working; mock MP4 generation confirmed.
- Preset system: `hunyuan-480p-fast`, `standard`, `quality`, `fast` seeded at startup.
- External model path configuration via `HUNYUAN_15_REPO_PATH` and `HUNYUAN_15_MODEL_PATH` absolute paths in `backend/.env`.

**Known gaps (not yet implemented):**

- Active subprocess cancellation (cancel only works for queued jobs).
- Progress parsing from Hunyuan stdout (progress bar stays at 0% during inference).
- Prompt rewriting backend (UI toggle exists, no-op on backend).
- Asset file cleanup on delete (DB record removed, files remain on disk).

See [FEATURES.md](FEATURES.md) for full bug list and roadmap.

---

## Original Prompt

You are a senior full-stack AI engineer. Build a completely local, offline-capable text-to-video content creation application from scratch using Tencent HunyuanVideo as the video generation runtime.

The target system must provide:

- A local Web UI for creators.
- A Python backend.
- A local job queue.
- A reproducible asset library.
- A runtime adapter for Tencent HunyuanVideo.
- A mock generation mode so the app can be developed and tested without a large GPU or model weights.
- No hosted APIs or internet calls during normal runtime.

Primary model target:

- Original HunyuanVideo repo: https://github.com/Tencent-Hunyuan/HunyuanVideo

Optional but strongly recommended runtime target:

- HunyuanVideo-1.5: https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5

Important implementation principle: design the application so the model runtime can be swapped. Do not glue the whole product directly to one inference script. Build a small adapter layer that supports:

- `mock` runtime for development.
- `hunyuan_original` runtime for Tencent-Hunyuan/HunyuanVideo.
- `hunyuan_15` runtime for Tencent-Hunyuan/HunyuanVideo-1.5.
- Optional future `diffusers_hunyuan` runtime.

## Product Goal

Create a local content creation tool where a user can:

1. Enter a text prompt.
2. Optionally enter a negative prompt.
3. Choose aspect ratio, resolution, frame count, inference steps, seed, and quality preset.
4. Submit a generation job.
5. Watch queue and progress status in the browser.
6. Preview completed videos.
7. Rerun a job with the same settings.
8. Create prompt or seed variations.
9. Browse past outputs in a local asset library.
10. Export MP4 files for social/content platforms.

The first version does not need advanced editing, audio generation, or timeline composition. It should be a clean, reliable local text-to-video generator with job history and reproducible metadata.

## Hard Requirements

Runtime behavior:

- The application must run locally.
- Normal generation must not call remote APIs.
- Prompt rewriting must be disabled by default.
- If prompt rewriting is implemented, it must support a local-only backend and gracefully fall back to the original prompt.
- Model weights must be loaded from local paths.
- The app must not auto-download model weights during normal startup.
- The app must validate model paths and show clear errors if weights are missing.
- The app must work in mock mode even when no GPU or model weights are present.

Backend:

- Use Python.
- Use FastAPI for the HTTP API.
- Use SQLite for local persistence.
- Use Pydantic for request and response models.
- Use a single local worker process or background worker for generation jobs.
- Start with one active generation at a time.
- Use WebSocket or Server-Sent Events for job progress.
- Persist every job request and result.
- Store output videos, thumbnails, metadata, and logs on disk.

Frontend:

- Use a local Web UI.
- Prefer React + Vite + TypeScript.
- The first screen should be the creator workspace, not a marketing page.
- The UI must include prompt controls, generation settings, queue status, current preview, and output gallery.
- The UI should remain useful in mock mode.

Offline packaging:

- Provide documentation for online bootstrap and offline runtime.
- Separate one-time dependency/model acquisition from normal offline use.
- Include a plan for wheelhouse or local dependency cache packaging.
- Include `.env.example` or config file examples for local paths.

Testing:

- Include backend tests for API models, queue behavior, and mock generation.
- Include at least one frontend smoke test or documented manual verification path.
- Include a mock generator that creates a tiny placeholder MP4 or uses an existing static sample so the full app flow can be tested without HunyuanVideo.

## Recommended Stack

Backend:

```text
Python 3.10 or 3.11
FastAPI
Uvicorn
Pydantic
SQLModel or SQLAlchemy
SQLite
ffmpeg
PyTorch for real runtime integration
pytest
```

Frontend:

```text
React
Vite
TypeScript
TanStack Query
Zustand or simple React state
CSS modules, Tailwind, or plain CSS
native video element
```

## Expected Repository Structure

```text
offline-video-generator/
  .env.example
  backend/
    pyproject.toml
    app/
      main.py
      config.py
      database.py
      models.py
      schemas.py
      api/
        jobs.py
        assets.py
        presets.py
        system.py
      services/
        queue.py
        storage.py
        thumbnails.py
        model_manager.py
        presets.py
        serialization.py
      runtime/
        base.py
        mock_adapter.py
        hunyuan_original_adapter.py
        hunyuan_15_adapter.py
    tests/
    data/
  frontend/
    package.json
    vite.config.ts
    src/
      main.tsx
      App.tsx
      api/client.ts
      components/
      state/useGenerationStore.ts
docs/
  installation.md
  models_setup.md
  ARCHITECTURE.md
  CODEBASE.md
  FEATURES.md
  app_overview.md
  backend_api.md
  bootstrap_online.md
  package_offline.md
  pipeline_spec.md
```

## Backend Design

### Configuration

Support configuration through environment variables and a local config file.

Example `.env.example`:

```text
APP_ENV=local
APP_HOST=127.0.0.1
APP_PORT=8000

DATABASE_URL=sqlite:///./data/app.db
OUTPUT_DIR=./data/outputs
THUMBNAIL_DIR=./data/thumbnails
LOG_DIR=./data/logs

VIDEO_RUNTIME=hunyuan_15

# Absolute paths to external model locations (any drive)
HUNYUAN_15_REPO_PATH=
HUNYUAN_15_MODEL_PATH=

FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe

MAX_ACTIVE_JOBS=1
DEFAULT_PRESET=standard
```

### Database Models

`jobs`, `assets`, `presets` — see [ARCHITECTURE.md](ARCHITECTURE.md) for full schema.

### Job States

```text
queued → loading_model → generating → postprocessing → completed
                                                      → failed
                                                      → cancelled
```

### API Endpoints

See [backend_api.md](backend_api.md) for the full endpoint list.

### Runtime Adapter Interface

```python
class VideoGenerationAdapter(ABC):
    @abstractmethod
    def generate(self, job, request, settings, on_progress) -> str:
        ...
    def cleanup(self): pass
```

## Development Phases

### Phase 1: Project Skeleton ✓
### Phase 2: Database and Job API ✓
### Phase 3: Mock Generation Worker ✓
### Phase 4: HunyuanVideo-1.5 Adapter ✓
### Phase 5: Creator Features ✓
### Phase 6: Offline Packaging ✓ (docs complete)
### Phase 7: Remaining gaps
- Active job cancellation
- Progress parsing from subprocess stdout
- Prompt rewriting backend
- Asset file cleanup on delete

## Security and Safety

- Never pass user text through `shell=True`.
- Use subprocess argument arrays.
- Sanitize output paths.
- Keep generated files under the configured output directory.
- Do not allow arbitrary command execution from the UI.
- Bind to `127.0.0.1`.
- Make external network use explicit and disabled during runtime.

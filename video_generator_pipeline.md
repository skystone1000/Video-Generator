# Implementation Prompt: Offline Text-to-Video Creator Pipeline

Use the following prompt with an implementation-focused LLM or coding agent.

## Build Progress

Started implementation in `offline-video-generator/`.

Current first slice:

- FastAPI backend scaffold.
- SQLite job, asset, and preset models.
- Local single-worker generation queue.
- Mock video runtime with `ffmpeg` or static sample fallback.
- HunyuanVideo and HunyuanVideo-1.5 subprocess adapter scaffolds.
- React + Vite creator workspace wired to backend APIs.
- Offline bootstrap/runtime docs and focused backend tests.

Next priority:

- Configure `ffmpeg` or `MOCK_SAMPLE_MP4_PATH` so mock generation can complete locally.
- Check the actual local Hunyuan repos before running real adapter commands.
- Add cancellation support for active Hunyuan subprocesses once the real command shape is verified.

## Prompt

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

Optional:

```text
Redis/RQ only if needed later
Diffusers adapter later
Local LLM prompt rewrite later
```

## Expected Repository Structure

Create a monorepo-style project:

```text
offline-video-generator/
  README.md
  .gitignore
  .env.example
  docker-compose.yml                  # optional, local only

  backend/
    pyproject.toml
    README.md
    app/
      __init__.py
      main.py
      config.py
      database.py
      models.py
      schemas.py

      api/
        __init__.py
        jobs.py
        assets.py
        presets.py
        system.py

      services/
        __init__.py
        queue.py
        storage.py
        thumbnails.py
        postprocess.py
        model_manager.py
        prompt_rewrite.py

      runtime/
        __init__.py
        base.py
        mock_adapter.py
        hunyuan_original_adapter.py
        hunyuan_15_adapter.py

      workers/
        __init__.py
        generation_worker.py

    tests/
      test_jobs_api.py
      test_queue.py
      test_mock_generation.py

    data/
      .gitkeep

  frontend/
    package.json
    index.html
    vite.config.ts
    src/
      main.tsx
      App.tsx
      api/
        client.ts
        jobs.ts
      components/
        PromptPanel.tsx
        SettingsPanel.tsx
        QueuePanel.tsx
        PreviewPanel.tsx
        AssetGallery.tsx
        JobStatusBadge.tsx
      state/
        useGenerationStore.ts
      styles/
        app.css

  scripts/
    bootstrap_online.md
    run_backend.sh
    run_frontend.sh
    package_offline.md
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

VIDEO_RUNTIME=mock

HUNYUAN_ORIGINAL_REPO_PATH=/models/HunyuanVideo
HUNYUAN_ORIGINAL_CKPT_PATH=/models/HunyuanVideo/ckpts

HUNYUAN_15_REPO_PATH=/models/HunyuanVideo-1.5
HUNYUAN_15_MODEL_PATH=/models/HunyuanVideo-1.5/weights

FFMPEG_PATH=ffmpeg

MAX_ACTIVE_JOBS=1
DEFAULT_PRESET=standard
```

### Database Models

Implement these tables or equivalent SQLModel/SQLAlchemy models.

`jobs`:

```text
id
status
prompt
negative_prompt
rewritten_prompt
seed
runtime
model_version
settings_json
progress
current_stage
output_asset_id
error_message
created_at
started_at
completed_at
```

`assets`:

```text
id
job_id
file_path
thumbnail_path
preview_path
metadata_path
duration_seconds
fps
width
height
favorite
tags_json
created_at
```

`presets`:

```text
id
name
description
settings_json
created_at
updated_at
```

### Job States

Use these states:

```text
queued
loading_model
generating
postprocessing
completed
failed
cancelled
```

### Generation Request Model

Use a request shape like:

```json
{
  "prompt": "cinematic shot of a futuristic city at sunrise",
  "negative_prompt": "",
  "aspect_ratio": "16:9",
  "resolution": "720p",
  "width": 1280,
  "height": 720,
  "video_length": 129,
  "fps": 24,
  "steps": 50,
  "seed": 42,
  "cfg_scale": 6.0,
  "flow_shift": 7.0,
  "use_cpu_offload": true,
  "use_fp8": false,
  "rewrite_prompt": false,
  "preset": "standard",
  "runtime": "mock"
}
```

Validate fields:

- Prompt must be non-empty.
- Width and height must be positive.
- Steps must be within a safe range.
- Video length must be within a safe range.
- Runtime must be one of the configured adapters.
- If a real Hunyuan runtime is chosen, required model paths must exist.

### API Endpoints

Implement:

```text
GET  /api/system/status
GET  /api/system/gpu
GET  /api/presets
POST /api/presets
PUT  /api/presets/{preset_id}
DELETE /api/presets/{preset_id}

POST /api/jobs
GET  /api/jobs
GET  /api/jobs/{job_id}
POST /api/jobs/{job_id}/cancel
POST /api/jobs/{job_id}/rerun
POST /api/jobs/{job_id}/variation

GET  /api/assets
GET  /api/assets/{asset_id}
GET  /api/assets/{asset_id}/video
GET  /api/assets/{asset_id}/thumbnail
PATCH /api/assets/{asset_id}
DELETE /api/assets/{asset_id}

WS   /api/jobs/{job_id}/events
```

`GET /api/system/status` should return:

```json
{
  "status": "ok",
  "runtime": "mock",
  "model_loaded": false,
  "queue_depth": 0,
  "active_job_id": null,
  "offline_mode": true
}
```

`GET /api/system/gpu` should return available GPU information if PyTorch is installed and CUDA is available. It must not crash if CUDA is unavailable.

### Runtime Adapter Interface

Create `backend/app/runtime/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Callable, Protocol

class ProgressCallback(Protocol):
    def __call__(self, progress: float, stage: str, message: str | None = None) -> None:
        ...

class VideoGenerationAdapter(ABC):
    name: str

    @abstractmethod
    def validate(self) -> None:
        ...

    @abstractmethod
    def load(self) -> None:
        ...

    @abstractmethod
    def generate(self, request, output_dir: str, progress: ProgressCallback):
        ...

    @abstractmethod
    def unload(self) -> None:
        ...
```

### Mock Adapter

Implement the mock adapter first.

Requirements:

- It should simulate progress.
- It should create an output folder.
- It should produce a valid MP4 file.
- It should write `metadata.json`.
- It should work without GPU.

If ffmpeg is available, generate a simple color/video test MP4 with text overlay. If text overlay is hard across platforms, create a simple color source video. If ffmpeg is missing, fail with a clear error message and explain how to install or configure ffmpeg.

### Hunyuan Original Adapter

Implement this adapter as a controlled subprocess wrapper first.

Use the configured repo path and checkpoint path.

Expected upstream command shape resembles:

```text
python3 sample_video.py \
  --video-size HEIGHT WIDTH \
  --video-length 129 \
  --infer-steps 50 \
  --prompt "..." \
  --flow-reverse \
  --use-cpu-offload \
  --save-path OUTPUT_DIR
```

Important:

- Do not assume the command is final without checking the local repo.
- Build command arguments from validated settings.
- Do not use `shell=True`.
- Capture stdout and stderr.
- Persist logs.
- Parse progress from output if possible.
- If progress cannot be parsed, emit coarse stages.
- Provide clear errors when model files or scripts are missing.

Later, direct Python integration can replace subprocess wrapping.

### HunyuanVideo-1.5 Adapter

Implement similarly as a subprocess wrapper first.

The adapter should:

- Validate local repo/model paths.
- Support 480p and 720p where available.
- Support CPU offloading flags.
- Support prompt rewrite disabled by default.
- Capture logs and output file paths.

Because upstream commands may change, implement adapter command construction in one small method and document exactly where to update it.

### Model Manager

Create a `ModelManager` service that:

- Chooses the adapter based on job runtime.
- Lazily loads the model.
- Reuses loaded model when possible.
- Can unload model.
- Validates runtime availability.
- Allows mock mode without model paths.

For subprocess adapters, `load()` can be a lightweight validation step in version 1.

### Queue and Worker

Implement a local queue:

- A job inserted through `POST /api/jobs` starts as `queued`.
- A background worker picks the next queued job.
- Only one job runs at a time in version 1.
- Worker updates job status, progress, and stages.
- Worker emits progress events to WebSocket/SSE subscribers.
- Worker creates asset records when generation completes.
- Worker captures errors and marks jobs as `failed`.

Cancellation:

- Support cancel for queued jobs.
- For active subprocess jobs, attempt graceful termination.
- If immediate cancellation is hard for direct model calls, document that active cancellation is best effort.

### Storage

Use deterministic output paths:

```text
backend/data/outputs/YYYY-MM-DD/job_<job_id>/
  output.mp4
  thumbnail.jpg
  preview.gif
  metadata.json
  logs.txt
```

Metadata should include:

```json
{
  "job_id": 1,
  "runtime": "mock",
  "prompt": "...",
  "negative_prompt": "",
  "seed": 42,
  "settings": {},
  "created_at": "...",
  "completed_at": "...",
  "output_file": "output.mp4"
}
```

### Post-processing

Use ffmpeg to:

- Normalize output to MP4 if needed.
- Generate thumbnail JPEG.
- Optionally generate preview GIF or short web preview.
- Probe video metadata such as duration, fps, width, and height.

Handle ffmpeg missing errors clearly.

## Frontend Design

Build a creator workspace as the first screen.

Layout:

```text
Left panel:
  Prompt editor
  Negative prompt
  Runtime selector
  Preset selector
  Aspect ratio
  Resolution
  Duration / frame count
  Steps
  Seed
  Advanced toggles

Center panel:
  Current job status
  Progress bar
  Main video preview
  Error/status messages

Right panel:
  Queue
  Recent outputs
  Selected job metadata

Bottom or gallery section:
  Asset library grid
```

Controls:

- Generate
- Cancel
- Rerun
- Randomize seed
- Create variation
- Favorite asset
- Delete asset
- Open/download video through browser

Presets:

```text
Draft:
  runtime=mock or real runtime
  480p
  fewer steps
  CPU offload enabled

Standard:
  720p if hardware allows
  balanced steps

High:
  higher steps
  720p or model-supported high quality

Vertical Short:
  9:16
  social video format

Cinematic:
  16:9
  stable seed
  creator-friendly defaults
```

UI behavior:

- Poll or subscribe to job updates.
- Show progress immediately after job submission.
- Disable invalid settings.
- Show helpful local error messages.
- Never imply that cloud generation is being used.
- Make mock runtime visibly marked as mock/test mode.

## Offline Workflow

Document two modes.

### Online Bootstrap Mode

Used once on a connected machine:

1. Clone this app repository.
2. Clone or download HunyuanVideo source.
3. Download required model weights.
4. Download Python wheels into a wheelhouse.
5. Download Node packages or prepare local npm cache.
6. Download or install ffmpeg.
7. Generate checksums.
8. Copy everything to the offline machine.

### Offline Runtime Mode

Used for normal operation:

1. Create Python virtual environment from local wheelhouse.
2. Install frontend dependencies from local package cache or prebuilt frontend.
3. Configure `.env`.
4. Start backend.
5. Start frontend.
6. Generate videos using local weights only.

Include docs in:

```text
scripts/bootstrap_online.md
scripts/package_offline.md
README.md
```

## Development Phases

Implement in phases and keep the app runnable after each phase.

### Phase 1: Project Skeleton

Deliver:

- Backend FastAPI app.
- Frontend Vite app.
- README with local dev commands.
- `.env.example`.
- Basic health endpoint.
- Basic creator workspace UI shell.

Acceptance:

- Backend starts.
- Frontend starts.
- Frontend can call `/api/system/status`.

### Phase 2: Database and Job API

Deliver:

- SQLite database setup.
- Job and asset models.
- Job creation endpoint.
- Job listing and detail endpoints.
- Preset listing endpoint.

Acceptance:

- User can submit a job.
- Job is persisted as `queued`.
- Job list appears in UI.

### Phase 3: Mock Generation Worker

Deliver:

- Background worker.
- Mock adapter.
- Progress updates.
- Output MP4 generation.
- Metadata write.
- Thumbnail generation.

Acceptance:

- User can submit a mock job from UI.
- Progress updates appear.
- A playable MP4 appears in the preview.
- Job changes to `completed`.
- Asset appears in gallery.

### Phase 4: Real Runtime Adapter

Deliver:

- `hunyuan_original` adapter.
- Local path validation.
- Subprocess command wrapper.
- Log capture.
- Output discovery.
- Clear runtime errors.

Acceptance:

- With valid local HunyuanVideo repo and weights, a real generation can be launched.
- With missing weights, the UI shows a clear error.
- Mock mode still works.

### Phase 5: HunyuanVideo-1.5 Adapter

Deliver:

- `hunyuan_15` adapter.
- 480p/720p setting support where upstream supports it.
- CPU offload option.
- Prompt rewrite disabled by default.

Acceptance:

- Adapter validates local setup.
- Real command can be invoked from backend.
- UI can select runtime.

### Phase 6: Creator Features

Deliver:

- Rerun job.
- Variation job with changed seed.
- Favorites.
- Tags.
- Prompt templates.
- Gallery filtering.

Acceptance:

- A user can manage generated assets locally.
- Every output remains reproducible from stored metadata.

### Phase 7: Offline Packaging

Deliver:

- Offline setup docs.
- Wheelhouse instructions.
- Model folder layout docs.
- Startup diagnostics.

Acceptance:

- The app can be installed on a disconnected machine if dependencies and weights were prepared.
- Startup clearly reports missing paths or unavailable GPU.

## Startup Commands

Document commands like these. Adjust for actual package manager choices.

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## Security and Safety

Because this is a local tool that executes model scripts:

- Never pass user text through `shell=True`.
- Use subprocess argument arrays.
- Sanitize output paths.
- Keep generated files under the configured output directory.
- Do not allow arbitrary command execution from the UI.
- Do not expose the server on public interfaces by default.
- Bind to `127.0.0.1`.
- Make external network use explicit and disabled during runtime.

## Error Handling

Handle these cases clearly:

- No GPU available.
- CUDA not available.
- PyTorch not installed.
- ffmpeg not installed.
- Model repo path missing.
- Checkpoint path missing.
- Inference script missing.
- Generation subprocess exits non-zero.
- Output video cannot be found.
- Output video is corrupt or unreadable.
- User cancels queued job.
- User tries invalid settings.

Errors should appear both:

- In backend logs.
- In the Web UI job status.

## Documentation Requirements

Write documentation for:

- What the app does.
- Hardware expectations.
- Difference between mock and real runtime.
- How to configure model paths.
- How to run backend and frontend.
- How to perform a mock generation.
- How to connect HunyuanVideo.
- How to package for offline use.
- Where outputs are stored.
- How reproducibility metadata works.

## Implementation Notes

Start with mock mode. Do not block the entire project on installing HunyuanVideo or downloading huge model weights.

Once mock generation works end to end, implement the Hunyuan adapters behind the same interface.

The final result should let a developer run:

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

and:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Then open the local UI, submit a mock generation, see progress, and preview a generated MP4. Real HunyuanVideo generation should become available by changing config paths and runtime settings.

## Final Acceptance Criteria

The implementation is complete when:

- The backend starts locally.
- The frontend starts locally.
- The UI can create a generation job.
- The backend persists the job.
- The worker processes the job.
- Mock mode generates a playable MP4.
- The UI shows live progress.
- The UI previews the completed video.
- The asset gallery shows completed outputs.
- Job metadata includes prompt, seed, runtime, and settings.
- Hunyuan runtime adapters exist with path validation and subprocess command construction.
- Missing model paths produce clear errors.
- Runtime operation does not require internet access.
- Documentation explains online bootstrap versus offline runtime.

Do not stop at a high-level plan. Create the actual project files, implement the mock end-to-end flow first, then add the Hunyuan runtime adapter scaffolding.

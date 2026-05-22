# Codebase Reference

## Directory Map

```
Video-Generator/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CODEBASE.md          ← this file
│   ├── FEATURES.md
│   └── models_setup.md
├── offline-video-generator/
│   ├── .env.example
│   ├── backend/
│   │   ├── pyproject.toml
│   │   ├── .env             (gitignored — your local config)
│   │   └── app/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── models.py
│   │       ├── schemas.py
│   │       ├── database.py
│   │       ├── api/
│   │       │   ├── jobs.py
│   │       │   ├── assets.py
│   │       │   ├── presets.py
│   │       │   └── system.py
│   │       ├── services/
│   │       │   ├── queue.py
│   │       │   ├── model_manager.py
│   │       │   ├── presets.py
│   │       │   ├── storage.py
│   │       │   ├── thumbnails.py
│   │       │   └── serialization.py
│   │       └── runtime/
│   │           ├── base.py
│   │           ├── mock_adapter.py
│   │           ├── hunyuan_original_adapter.py
│   │           └── hunyuan_15_adapter.py
│   └── frontend/
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       └── src/
│           ├── App.tsx
│           ├── main.tsx
│           ├── api/
│           │   └── client.ts
│           ├── state/
│           │   └── useGenerationStore.ts
│           └── components/
│               ├── PromptPanel.tsx
│               ├── SettingsPanel.tsx
│               ├── PreviewPanel.tsx
│               ├── AssetGallery.tsx
│               ├── QueuePanel.tsx
│               └── SystemInfo.tsx
├── installation.md
├── README.md
└── .gitignore
```

---

## Backend

### `app/main.py`

FastAPI application entry point.

- `lifespan(app)` — async context manager: calls `init_db()`, `seed_default_presets()`, `generation_queue.start()` on startup. Stops the queue on shutdown.
- CORS middleware configured with a regex matching any port on `localhost` or `127.0.0.1`.
- Four routers registered: `jobs_router`, `assets_router`, `presets_router`, `system_router` — all under `/api` prefix.
- Static file mounts: `/outputs` → `OUTPUT_DIR`, `/thumbnails` → `THUMBNAIL_DIR`.

---

### `app/config.py`

`Settings` class — `pydantic_settings.BaseSettings` reading from `BACKEND_ROOT/.env`.

Key items:

```python
BACKEND_ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = "sqlite:///./data/app.db"
    output_dir: str = "./data/outputs"
    thumbnail_dir: str = "./data/thumbnails"
    log_dir: str = "./data/logs"
    video_runtime: str = "hunyuan_15"
    hunyuan_15_repo_path: str = ""
    hunyuan_15_model_path: str = ""
    hunyuan_15_enable_sr: bool = False
    hunyuan_15_use_sage_attn: bool = False
    hunyuan_15_enable_cache: bool = False
    max_active_jobs: int = Field(default=1, ge=1, le=1)  # locked to 1
    default_preset: str = "standard"
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

def resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else BACKEND_ROOT / p
```

`settings` is a module-level singleton imported throughout the app.

---

### `app/database.py`

SQLAlchemy 2.0 setup.

```python
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():           # called at startup — creates tables
def get_db() -> Session  # FastAPI dependency — yields a session, closes on exit
```

---

### `app/models.py`

SQLAlchemy ORM models.

- `JobStatus` — Python `enum.Enum`: `queued, loading_model, generating, postprocessing, completed, failed, cancelled`
- `Job` — maps to `jobs` table (see schema in ARCHITECTURE.md)
- `Asset` — maps to `assets` table
- `Preset` — maps to `presets` table

---

### `app/schemas.py`

Pydantic v2 request/response schemas.

```python
RuntimeName = Literal["mock", "hunyuan_original", "hunyuan_15", "diffusers_hunyuan"]

class GenerationRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    runtime: RuntimeName = "mock"
    resolution: str = "480p"
    width: int = 854
    height: int = 480
    video_length: int = 29
    fps: int = 24
    seed: int = -1
    steps: int = 20
    cfg_scale: float = 6.0
    flow_shift: float = 5.0
    use_cpu_offload: bool = True
    use_fp8: bool = False
    rewrite_prompt: bool = False
    preset: str = "standard"

class JobResponse(BaseModel):   # returned by all job endpoints
class AssetResponse(BaseModel)
class PresetResponse(BaseModel)
class SystemStatusResponse(BaseModel)
```

Note: `diffusers_hunyuan` appears in `RuntimeName` but has no corresponding adapter.

---

### `app/api/jobs.py`

```
POST   /jobs              create_job(request: GenerationRequest) → JobResponse
GET    /jobs              list_jobs() → list[JobResponse]         (last 100, desc)
GET    /jobs/{id}         get_job(id) → JobResponse
POST   /jobs/{id}/cancel  cancel_job(id) → JobResponse
POST   /jobs/{id}/rerun   rerun_job(id) → JobResponse             (clones job, enqueues)
POST   /jobs/{id}/variation create_variation(id, overrides) → JobResponse
WS     /jobs/{id}/events  stream_job_events(id)                   (unused by frontend)
```

`cancel_job` adds the job ID to `GenerationQueue._cancel_requested`. This only works for jobs still in `queued` state — running subprocess jobs cannot be cancelled.

---

### `app/api/assets.py`

```
GET    /assets            list_assets() → list[AssetResponse]    (last 200, desc)
GET    /assets/{id}/video FileResponse (mp4)
GET    /assets/{id}/thumbnail FileResponse (jpeg)
PATCH  /assets/{id}       update favorite/tags → AssetResponse
DELETE /assets/{id}       deletes DB record only (files remain on disk)
```

---

### `app/api/presets.py`

```
GET    /presets           list_presets() → list[PresetResponse]
POST   /presets           create_preset(data) → PresetResponse
PUT    /presets/{id}      update_preset(id, data) → PresetResponse
DELETE /presets/{id}      delete_preset(id)
```

---

### `app/api/system.py`

```
GET /system/status   → SystemStatusResponse
    {
      status: "running",
      queue_length: int,
      active_jobs: int,
      gpu_info: { name, vram_total_gb, vram_used_gb, vram_free_gb } | null
    }
GET /system/config   → dict of non-sensitive settings
```

GPU info uses `subprocess("nvidia-smi ...")` — returns null if nvidia-smi unavailable.

---

### `app/services/queue.py`

`GenerationQueue` — manages the single background daemon thread.

```python
class GenerationQueue:
    _thread: threading.Thread
    _cancel_requested: set[int]     # IDs of jobs user wants cancelled
    _running: bool

    def start()              # launch daemon thread
    def stop()               # set _running=False, join thread
    def request_cancel(job_id: int)
    def _run_loop()          # polls DB every 0.5s
    def _process_job(job_id) # full lifecycle: loading_model → generating → postprocessing
```

`_process_job` updates job status at each transition, calls `model_manager.get_adapter(runtime).generate(...)`, handles exceptions, and creates the Asset record on success.

Progress callbacks are passed into `adapter.generate()`:

```python
def on_progress(progress: float, stage: str):
    # update job.progress and job.current_stage in DB
```

---

### `app/services/model_manager.py`

```python
class ModelManager:
    _current_runtime: str | None
    _adapter: VideoGenerationAdapter | None

    def get_adapter(runtime: str) -> VideoGenerationAdapter:
        # if runtime changed: cleanup old, instantiate new
        # returns cached adapter for same runtime
```

Adapter constructors are called here. `Hunyuan15Adapter.__init__` receives `settings` and validates that `hunyuan_15_repo_path` is set.

---

### `app/services/presets.py`

`DEFAULT_PRESETS` — list of preset dicts seeded at startup by `seed_default_presets()`. First entry is `hunyuan-480p-fast` (fastest real generation config). Includes `standard`, `quality`, `fast`, and `hunyuan-*` variants.

`seed_default_presets()` inserts any default preset not already in the DB (by name). Does not overwrite existing records.

---

### `app/services/storage.py`

`StorageManager` — handles output file placement.

```python
def save_output(job_id, temp_path) -> (output_path, metadata_path):
    # copies temp output to data/outputs/YYYY-MM-DD/job_{id}/output.mp4
    # writes metadata.json with job details
    # returns paths relative to OUTPUT_DIR
```

---

### `app/services/thumbnails.py`

`ThumbnailGenerator` — extracts a single frame from a video file.

```python
def generate(video_path, output_path) -> bool:
    # runs: ffmpeg -i video -vf "select=eq(n\,0)" -vframes 1 output.jpg
    # returns True on success
```

---

### `app/services/serialization.py`

Helper for converting between SQLAlchemy models and Pydantic response schemas. Provides `job_to_response()`, `asset_to_response()`, `preset_to_response()`.

---

### `app/runtime/base.py`

```python
class VideoGenerationAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        job: Job,
        request: GenerationRequest,
        settings: Settings,
        on_progress: Callable[[float, str], None],
    ) -> str:  # returns path to output video
        ...

    def cleanup(self):
        pass
```

---

### `app/runtime/mock_adapter.py`

Simulates generation for development/testing.

- 5 progress steps, 0.15 s sleep each
- If `FFMPEG_PATH` is available: generates a 5-second `testsrc2` video at the requested resolution
- Fallback: copies a bundled sample MP4

---

### `app/runtime/hunyuan_original_adapter.py`

Calls the original HunyuanVideo (not 1.5) via:

```bash
python3 sample_video.py --video-size H W --video-length N --infer-steps S ...
```

No Windows compatibility fix applied. Likely broken on Windows for the same libuv reason.

---

### `app/runtime/hunyuan_15_adapter.py`

Calls HunyuanVideo-1.5.

Key design:

```python
def _python_from_torchrun(torchrun_path: str) -> str:
    # derives python.exe from torchrun.exe (same Scripts/ directory)
    # e.g. .venv/Scripts/torchrun.exe → .venv/Scripts/python.exe

def build_command(request, settings) -> list[str]:
    # returns: [python_exe, generate.py, --model-base, ..., --prompt, ...]

def generate(job, request, settings, on_progress) -> str:
    env = {**os.environ, "USE_LIBUV": "0"}
    proc = subprocess.Popen(cmd, stdout=PIPE, stderr=STDOUT, env=env, cwd=repo_path)
    # streams output to logs.txt
    # returns output video path
```

Arguments passed to `generate.py`:

| Arg | Source |
|---|---|
| `--model-base` | `HUNYUAN_15_MODEL_PATH` |
| `--dit` | `transformer/480p_t2v` (hardcoded for 480p) |
| `--height`, `--width` | request |
| `--video-length` | request |
| `--infer-steps` | request |
| `--cfg-scale` | request |
| `--flow-shift` | request |
| `--prompt` | request (rewritten_prompt if set, else prompt) |
| `--seed` | request (-1 → random) |
| `--cpu-offload` | if `use_cpu_offload` |
| `--use-fp8` | if `use_fp8` |
| `--enable-cache` | if `enable_cache` |
| `--save-path` | job output directory |

---

## Frontend

### `src/App.tsx`

Root component. Sets up the polling interval (`setInterval(refresh, 1500)`) and three-column layout.

`refresh()` calls `Promise.all([getSystemStatus(), listJobs(), listAssets(), listPresets()])` and updates the store.

---

### `src/state/useGenerationStore.ts`

Module-level singleton state. No React Context. Exposed via `useSyncExternalStore`.

```typescript
type GenerationStore = {
  jobs: Job[]
  assets: Asset[]
  presets: Preset[]
  systemStatus: SystemStatus | null
  activeJobId: number | null
  selectedAssetId: number | null
  generationRequest: GenerationRequest
  isSubmitting: boolean
  error: string | null
}

// Actions
setGenerationState(patch: Partial<GenerationStore>)
submitJob(): Promise<void>
cancelJob(id: number): Promise<void>
```

Default `generationRequest.runtime` is `"mock"` — user must switch to `"hunyuan_15"` via the preset selector.

---

### `src/api/client.ts`

Thin wrapper around `fetch`. Base URL hardcoded to `http://127.0.0.1:8000/api`.

```typescript
getSystemStatus(): Promise<SystemStatus>
listJobs(): Promise<Job[]>
createJob(req: GenerationRequest): Promise<Job>
cancelJob(id: number): Promise<Job>
listAssets(): Promise<Asset[]>
updateAsset(id, patch): Promise<Asset>
deleteAsset(id): Promise<void>
listPresets(): Promise<Preset[]>
```

---

## Adding a New Runtime Adapter

1. Create `app/runtime/my_adapter.py`, implement `VideoGenerationAdapter`.
2. Add the runtime name to `RuntimeName` in `schemas.py`.
3. In `model_manager.py`, add a branch to instantiate your adapter.
4. Add a preset in `services/presets.py` with `"runtime": "my_runtime"`.
5. Update `.env.example` with any new required env vars.

---

## Python Dependencies

From `pyproject.toml`:

```toml
[project]
requires-python = ">=3.10,<3.14"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "sqlalchemy>=2.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["httpx", "pytest", "pytest-asyncio"]
```

Virtual environment: `.venv/` inside `offline-video-generator/backend/` (gitignored).

---

## Running the Backend

```powershell
cd offline-video-generator/backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or via the configured script if defined in `pyproject.toml`.

## Running the Frontend

```powershell
cd offline-video-generator/frontend
npm install
npm run dev
```

Vite dev server proxies `/api` → `http://127.0.0.1:8000` (configured in `vite.config.ts`).

# Architecture

## System Overview

Video-Generator is an offline, single-machine video generation application. The frontend communicates with a local FastAPI backend over HTTP. The backend orchestrates a queue of generation jobs, delegates work to runtime adapters (mock or HunyuanVideo-1.5), and stores results on disk.

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (React + TypeScript)                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ PromptPanel  │  │SettingsPanel │  │  AssetGallery      │     │
│  └──────────────┘  └──────────────┘  └────────────────────┘     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  useGenerationStore (useSyncExternalStore singleton)    │    │
│  └─────────────────────────────────────────────────────────┘    │
│            │ HTTP polling every 1.5 s                           │
└────────────┼────────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────────┐
│  FastAPI (uvicorn)  — offline-video-generator/backend/          │
│                                                                 │
│  Routers                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │ /jobs    │ │ /assets  │ │ /presets │ │ /system          │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
│                                                                 │
│  Services                                                       │
│  ┌────────────────────┐    ┌──────────────────────────────┐     │
│  │ GenerationQueue    │    │ ModelManager                 │     │
│  │ (daemon thread)    │ -> │ (lazy adapter loader)        │     │
│  └────────────────────┘    └──────────────────────────────┘     │
│                                          │                      │
│  Runtime Adapters                        │                      │
│  ┌──────────────┐ ┌────────────────────┐ │ ┌─────────────────┐  │
│  │ MockAdapter  │ │ HunyuanOriginal    │ │ │ Hunyuan15       │  │
│  │              │ │ Adapter            │◀┘ │ Adapter        │  │
│  └──────────────┘ └────────────────────┘   └─────────────────┘  │
│                                                                 │
│  Persistence                                                    │
│  ┌───────────────────┐    ┌────────────────────────────────┐    │
│  │ SQLite (SQLAlch.) │    │ Filesystem (outputs/, thumbs/) │    │
│  └───────────────────┘    └────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────────┐
│  External (user-provided, any drive)                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ HunyuanVideo-1.5 code repo  (HUNYUAN_15_REPO_PATH)     │     │
│  │ Model checkpoints / ckpts/  (HUNYUAN_15_MODEL_PATH)    │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layers

### 1. Frontend

Single-page React app (TypeScript + Vite). No server-side rendering. Talks to the backend via `fetch()` only — no WebSocket use despite one existing on the backend.

State is managed by a module-level singleton (`useGenerationStore.ts`) exposed through React's `useSyncExternalStore`. This avoids React Context and keeps state outside the component tree.

Polling: adaptive `setTimeout` loop in `App.tsx`. Fires every 1.5 s when any job is in an active state (`queued`, `loading_model`, `generating`, `postprocessing`), backs off to 8 s when idle.

An `<ErrorBoundary>` component wraps `<App>` in `main.tsx` to catch unhandled React exceptions and display an error screen with a "Try again" button instead of a blank page.

### 2. API Layer (FastAPI)

Four routers mounted at `/api`:

| Router | Prefix | Key routes |
|---|---|---|
| `jobs.py` | `/api/jobs` | POST (create), GET (list/get), POST cancel/rerun/variation |
| `assets.py` | `/api/assets` | GET list, GET video/thumbnail files, PATCH, DELETE |
| `presets.py` | `/api/presets` | GET list, POST, PUT, DELETE |
| `system.py` | `/api/system` | GET status, GET config |

CORS is configured with a compiled regex allowing any port on localhost/127.0.0.1.

### 3. Service Layer

**`GenerationQueue`** — a single daemon thread that polls SQLite every 0.5 s for `queued` jobs, picks the oldest, delegates to `ModelManager`, updates job status as it progresses, and writes the output asset record.

**`ModelManager`** — holds a single loaded adapter at a time. When a new runtime is requested it unloads the current adapter and loads the new one. Adapter loading is lazy — nothing is loaded until the first job of that runtime type runs.

### 4. Runtime Adapters

All adapters inherit `VideoGenerationAdapter` (ABC):

```
VideoGenerationAdapter (ABC)
├── generate(job, request, settings, callbacks) → str  (output path)
├── cancel()   — terminates the running subprocess (SIGTERM then SIGKILL)
└── cleanup()

Concrete:
├── MockVideoAdapter       — ffmpeg testsrc2, simulated progress
├── HunyuanOriginalAdapter — calls sys.executable sample_video.py (original HunyuanVideo)
└── Hunyuan15Adapter       — calls python.exe generate.py (HunyuanVideo-1.5, Windows-safe)
```

Both real adapters store `_proc: subprocess.Popen | None`. On `cancel()` they call `proc.terminate()` and wait up to 5 s before `proc.kill()`. Progress is parsed from subprocess stdout via `_STEP_RE = re.compile(r"\b(\d+)/(\d+)\b")`, matching tqdm-style (`15/30`) and log-style (`step 5/30`) output.

`Hunyuan15Adapter` derives the python executable path from the configured `torchrun.exe` path (same `Scripts/` directory), then spawns `python.exe generate.py` with the model arguments. Stdout/stderr are piped to `logs.txt` in the job output directory.

### 5. Persistence

**SQLite** via SQLAlchemy 2.0 (sync sessions, `StaticPool` for thread safety). Database file: `backend/data/app.db`. Three tables: `jobs`, `assets`, `presets`. `init_db()` runs an idempotent ALTER TABLE migration to add any missing columns (e.g. `updated_at`) to existing databases.

**Filesystem** layout under `backend/data/`:
```
data/
├── app.db
├── outputs/
│   └── YYYY-MM-DD/
│       └── job_{id}/
│           ├── output.mp4
│           ├── logs.txt
│           └── metadata.json
├── thumbnails/
│   └── {id}.jpg
└── logs/
```

---

## Job Lifecycle (Data Flow)

```
POST /api/jobs
      │
      ▼
   Create Job record (status=queued) in SQLite
      │
      ▼
   GenerationQueue daemon picks up job (polls every 0.5 s)
      │
      ├─ status → loading_model
      │     ModelManager.get_adapter(runtime)
      │
      ├─ status → generating
      │     adapter.generate(job, request, settings, callbacks)
      │       ├─ Spawns subprocess (python.exe generate.py)
      │       ├─ Streams stdout → logs.txt
      │       └─ Progress callbacks update job.progress in DB
      │
      ├─ status → postprocessing
      │     StorageManager: copy output to outputs/YYYY-MM-DD/job_{id}/
      │     ThumbnailGenerator: extract frame → thumbnails/{id}.jpg
      │     Create Asset record in SQLite
      │
      └─ status → completed  (or failed / cancelled)

Frontend polls GET /api/jobs every 1.5 s → reflects current status
```

---

## Database Schema

### `jobs`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto-increment |
| status | VARCHAR | enum: queued/loading_model/generating/postprocessing/completed/failed/cancelled |
| prompt | TEXT | |
| negative_prompt | TEXT | nullable |
| rewritten_prompt | TEXT | nullable — unused (no rewrite backend) |
| seed | INTEGER | -1 = random |
| runtime | VARCHAR | mock / hunyuan_15 / hunyuan_original |
| model_version | VARCHAR | nullable |
| settings_json | TEXT | full GenerationRequest JSON |
| progress | FLOAT | 0.0–1.0 |
| current_stage | VARCHAR | human-readable stage label |
| output_asset_id | INTEGER | FK → assets.id, nullable |
| error_message | TEXT | nullable |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| completed_at | DATETIME | nullable |

### `assets`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| job_id | INTEGER | FK → jobs.id |
| file_path | TEXT | relative to OUTPUT_DIR |
| thumbnail_path | TEXT | relative to THUMBNAIL_DIR |
| preview_path | TEXT | nullable |
| metadata_path | TEXT | |
| duration | FLOAT | seconds |
| fps | FLOAT | |
| width | INTEGER | |
| height | INTEGER | |
| favorite | BOOLEAN | |
| tags_json | TEXT | JSON array |
| created_at | DATETIME | |

### `presets`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | VARCHAR | unique |
| description | TEXT | nullable |
| settings_json | TEXT | full GenerationRequest JSON |
| created_at | DATETIME | |
| updated_at | DATETIME | |

---

## Configuration System

Settings are loaded by `pydantic_settings.BaseSettings` from `backend/.env`. All paths go through `config.resolve_path()` which transparently handles both relative (resolved against `BACKEND_ROOT`) and absolute paths.

Key environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `APP_HOST` | `127.0.0.1` | uvicorn bind address |
| `APP_PORT` | `8000` | uvicorn port |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy URL |
| `OUTPUT_DIR` | `./data/outputs` | video output root |
| `THUMBNAIL_DIR` | `./data/thumbnails` | thumbnail root |
| `LOG_DIR` | `./data/logs` | application logs |
| `VIDEO_RUNTIME` | `hunyuan_15` | default runtime (overridden by preset) |
| `HUNYUAN_15_REPO_PATH` | *(required)* | path to cloned HunyuanVideo-1.5 repo |
| `HUNYUAN_15_MODEL_PATH` | *(required)* | path to `ckpts/` directory |
| `HUNYUAN_15_ENABLE_SR` | `false` | super-resolution |
| `HUNYUAN_15_USE_SAGE_ATTN` | `false` | SageAttention |
| `HUNYUAN_15_ENABLE_CACHE` | `false` | TeaCache |
| `MAX_ACTIVE_JOBS` | `1` | concurrent jobs (1–8, validated) |
| `DEFAULT_PRESET` | `standard` | preset name used when none specified |
| `FFMPEG_PATH` | `ffmpeg` | ffmpeg binary |
| `FFPROBE_PATH` | `ffprobe` | ffprobe binary |

---

## Frontend Component Tree

```
main.tsx
└── ErrorBoundary           — catches unhandled React exceptions; shows error + "Try again"
    └── App.tsx
        ├── leftRail
        │   ├── PromptPanel         — textarea, negative prompt, generate button
        │   └── SettingsPanel       — preset selector, resolution, steps, CFG, etc.
        ├── centerStage
        │   ├── PreviewPanel        — displays currently selected asset
        │   └── AssetGallery        — grid of completed assets with thumbnails
        └── rightRail
            ├── SystemInfo          — backend status, GPU info
            └── QueuePanel          — active + queued jobs with progress bars
```

State shape (`useGenerationStore`):

```typescript
{
  jobs: Job[]
  assets: Asset[]
  presets: Preset[]
  systemStatus: SystemStatus | null
  activeJobId: number | null
  selectedAssetId: number | null
  generationRequest: GenerationRequest   // mirrors backend schema
  isSubmitting: boolean
  error: string | null
}
```

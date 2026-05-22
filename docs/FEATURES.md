# Features, Bugs & Roadmap

## Current Features

### Video Generation
- Submit a text prompt and generate a video using HunyuanVideo-1.5 (480p T2V) or the mock adapter
- Preset system: select from named generation profiles (hunyuan-480p-fast, standard, quality, fast, etc.)
- Settings panel: resolution, frame count, FPS, inference steps, CFG scale, flow shift, seed, CPU offload, FP8
- Real-time progress display: status label + progress bar updated every 1.5 s via polling
- Job queue: jobs processed one at a time in FIFO order
- Job history: last 100 jobs shown in the queue panel

### Asset Management
- Asset gallery: grid of completed videos with thumbnails
- Video preview: click any asset to play it in the center panel
- Favorite/unfavorite assets
- Tag assets (freeform JSON array)
- Delete asset (removes DB record)

### Preset Management
- Create, edit, and delete presets via the UI
- Default presets seeded at startup (hunyuan-480p-fast, standard, quality, fast)
- Presets store the full `GenerationRequest` including runtime selection

### Job Operations
- Cancel a queued job (before it starts processing)
- Rerun a completed/failed job (clones settings, enqueues new job)
- Create a variation (rerun with partial setting overrides)

### System
- System status panel: backend health, queue depth, active job count, GPU VRAM info
- Offline-first: no external services required at runtime (models stored locally)
- Windows + NVIDIA GPU support

---

## Bugs

### Critical

**1. `max_active_jobs` locked to exactly 1**
- File: `app/config.py`, `max_active_jobs: int = Field(default=1, ge=1, le=1)`
- The validator `ge=1, le=1` enforces exactly 1. Setting `MAX_ACTIVE_JOBS=2` in `.env` is silently clamped to 1. The queue logic (`queue.py`) checks `active_jobs >= max_active_jobs` but can never scale up.
- Impact: multi-GPU or future parallel generation is impossible without a code change.

**2. Active job subprocess cannot be cancelled**
- File: `app/services/queue.py`, `_process_job()`
- `_cancel_requested` only prevents a queued job from starting. Once `subprocess.Popen` is called, no process handle is stored — there is no way to kill the running inference.
- Impact: clicking "Cancel" on a running job has no effect. The job runs to completion (or error), and the cancel flag is ignored.

**3. Asset file cleanup missing on delete**
- File: `app/api/assets.py`, `DELETE /assets/{id}`
- The handler deletes the SQLite record but leaves `output.mp4`, `thumbnail.jpg`, and `metadata.json` on disk.
- Impact: disk fills up silently over time.

**4. `diffusers_hunyuan` runtime stub**
- File: `app/schemas.py` — `RuntimeName` includes `"diffusers_hunyuan"`.
- File: `app/services/model_manager.py` — no branch handles this runtime.
- Impact: selecting this runtime raises an unhandled exception in the queue thread, marking the job failed with an opaque error.

**5. Prompt rewriting wired in UI but absent in backend**
- File: `app/schemas.py` — `rewrite_prompt: bool = False` accepted.
- File: `app/models.py` — `rewritten_prompt` column exists.
- File: `app/api/jobs.py` — no code performs rewriting; `rewritten_prompt` is never populated.
- File: `app/runtime/hunyuan_15_adapter.py` — uses `rewritten_prompt if set, else prompt`, so it correctly falls through to `prompt`, but the feature appears broken to the user who enabled it.
- Impact: "Rewrite prompt" toggle is a no-op silently.

**6. `HunyuanOriginalAdapter` missing Windows fix**
- File: `app/runtime/hunyuan_original_adapter.py`
- Still calls `python3 sample_video.py` (not `python.exe`) and does not set `USE_LIBUV=0`. On Windows this will fail with the same libuv error that was fixed in `Hunyuan15Adapter`.
- Impact: `hunyuan_original` runtime always fails on Windows.

---

### Moderate

**7. Aggressive frontend polling**
- File: `offline-video-generator/frontend/src/App.tsx`, `setInterval(refresh, 1500)`
- Every 1.5 s fires four simultaneous API requests (status, jobs, assets, presets). When no jobs are running this is pure overhead and inflates battery/CPU usage.
- Fix: back off to 5–10 s when no active jobs; use the existing WebSocket endpoint (`/jobs/{id}/events`) to drive real-time updates during generation.

**8. WebSocket endpoint unused**
- File: `app/api/jobs.py`, `@router.websocket("/jobs/{id}/events")`
- The endpoint polls DB every 1 s and streams JSON updates over WS. The frontend never connects to it — everything goes through REST polling. The WS code is dead weight.

**9. No progress parsing from HunyuanVideo output**
- File: `app/runtime/hunyuan_15_adapter.py`
- Subprocess stdout is written to `logs.txt` but never parsed for progress information. `on_progress` is never called during actual inference — the job stays at 0% until it completes or fails.
- Impact: progress bar shows 0% for the entire inference duration (can be 10–30 minutes).

**10. No asset pagination**
- File: `app/api/assets.py` — `list_assets()` returns up to 200 records.
- File: `app/api/jobs.py` — `list_jobs()` returns up to 100 records.
- Both values are hardcoded. Heavy users will hit these limits. The frontend fetches the full list every 1.5 s.

**11. Default runtime in store is `"mock"`**
- File: `frontend/src/state/useGenerationStore.ts`, `defaultRequest`
- New users who submit without selecting a preset will get a mock video. The UI doesn't make this obvious. They may think real generation failed because they see a test-pattern output.

---

### Minor

**12. CORS regex too permissive**
- File: `app/main.py`
- Pattern matches any port on `localhost`/`127.0.0.1`. This is intentional for development but should be locked to the known frontend port in a hardened setup.

**13. No authentication**
- All API endpoints are unauthenticated. Acceptable for a strictly local app, but needs attention if the backend is ever exposed beyond loopback.

**14. No rate limiting**
- A client can flood `POST /jobs` and exhaust queue depth, disk space, or model VRAM without any throttle.

**15. `nvidia-smi` called via subprocess on every `/system/status` request**
- File: `app/api/system.py`
- Called synchronously in the request handler. Adds latency (50–200 ms) to every status poll. Result should be cached with a short TTL.

**16. `seed: -1` not resolved to a fixed seed before storage**
- File: `app/api/jobs.py`, `create_job()`
- When `seed=-1`, a random seed is chosen by the adapter at generation time, but the stored `settings_json` still shows `-1`. Rerun/variation jobs cannot reproduce the exact output because the actual seed is never persisted.

**17. `LOG_DIR` created but never written to**
- `data/logs/` is created by the storage initialisation, but the app writes logs to `stdout` and per-job `logs.txt`. The directory is unused.

---

## Security Issues

| Issue | Severity | Location |
|---|---|---|
| No authentication on any endpoint | High (if exposed) | all routers |
| No rate limiting | Medium | `POST /jobs` |
| CORS allows any localhost port | Low | `main.py` |
| subprocess args not sanitised | Low | adapters (prompt goes to CLI arg; Pydantic validation is the only guard) |

---

## Future Scope

### High Priority

**Real-time progress during inference**
Parse HunyuanVideo-1.5 stdout for step progress (`step X/Y`) and feed it to `on_progress()`. This makes long generations usable — users can see progress rather than a stuck bar.

**Active job cancellation**
Store `subprocess.Popen` handle in the queue. On cancel request, call `proc.terminate()` (SIGTERM) followed by `proc.kill()` if it doesn't exit. Mark job as `cancelled` and clean up partial output.

**Asset file cleanup**
When `DELETE /assets/{id}` is called, delete the video file, thumbnail, and metadata from disk (using the stored relative paths). Add a bulk "clear all" action to the UI.

**Prompt rewriting (LLM expansion)**
Implement the `rewrite_prompt` feature using the already-downloaded `Qwen2.5-VL-7B-Instruct` text encoder as a local LLM. The infrastructure (model, column, UI toggle) is already in place; only the backend logic is missing.

**Fix `diffusers_hunyuan` or remove it**
Either implement a Diffusers-based adapter or remove the name from `RuntimeName` and the UI to prevent silent failures.

---

### Medium Priority

**WebSocket-driven frontend**
Replace the 1.5 s polling loop with a WebSocket connection to `/jobs/{id}/events` when a job is active. Fall back to slow polling (5–10 s) when idle. Reduces CPU/battery use and improves perceived responsiveness.

**Scalable concurrency**
Fix `max_active_jobs` validator (change `le=1` to `le=8`). Update `GenerationQueue` to run N workers concurrently using a thread pool. Required for multi-GPU setups.

**Asset pagination**
Add `?limit=&offset=` or cursor-based pagination to `GET /assets` and `GET /jobs`. Update the frontend gallery to load-more rather than fetching everything every poll.

**Seed persistence**
Resolve `seed=-1` to an actual random integer before storing `settings_json`, so rerun/variation jobs reproduce the exact output.

**Model pre-load on startup**
Optionally load the Hunyuan adapter at startup (controlled by a new env var `PRELOAD_RUNTIME=hunyuan_15`) to eliminate the loading_model delay on the first job.

---

### Low Priority / Future Ideas

**Image-to-video (I2V) support**
HunyuanVideo-1.5 supports image conditioning. Add an image upload input to the UI and pass `--image-path` to `generate.py`. The adapter already has a placeholder for `image_path` argument handling.

**Super-resolution (SR) post-processing**
`HUNYUAN_15_ENABLE_SR=true` env var exists but the SR pipeline is not wired up in the adapter. Implement SR as a postprocessing step after generation.

**SageAttention integration**
`HUNYUAN_15_USE_SAGE_ATTN` flag exists. Wire it into the adapter command and document the installation of the `sageattention` package.

**Multiple model versions**
Support switching between `480p_t2v`, `720p_t2v`, and `1080p_t2v` transformer variants at the preset level. Currently `480p_t2v` is hardcoded in the adapter.

**Video-to-video (V2V)**
Add a video input panel for video conditioning / style transfer.

**Export / share**
Add an export button to copy/move a video to a user-chosen location. Add metadata export (prompt, seed, settings) alongside the video file.

**Batch generation**
Queue multiple prompt variants in a single submission (prompt list or wildcard expansion).

**Plugin / custom adapter system**
A formal plugin interface where users can drop in a new adapter directory and have it auto-discovered, without modifying core files.

**Authentication + multi-user**
If the backend is ever network-exposed (e.g. LAN sharing), add token-based auth and per-user job/asset isolation.

**Docker / container packaging**
A `docker-compose.yml` that bundles the backend + frontend, with model paths volume-mounted. Reduces Windows setup friction.

**Frontend dark/light theme toggle**
Currently always dark. A simple CSS variable swap would complete the UI polish.

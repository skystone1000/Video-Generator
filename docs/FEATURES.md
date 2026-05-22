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
- Delete asset (removes DB record **and** video/thumbnail/metadata files from disk)

### Preset Management
- Create, edit, and delete presets via the UI
- Default presets seeded at startup (hunyuan-480p-fast, standard, quality, fast)
- Presets store the full `GenerationRequest` including runtime selection

### Job Operations
- Cancel a queued or running job (queued jobs are dropped; running subprocess is terminated via SIGTERM/SIGKILL)
- Rerun a completed/failed job (clones settings, enqueues new job)
- Create a variation (rerun with partial setting overrides)

### System
- System status panel: backend health, queue depth, active job count, GPU VRAM info (cached 15 s)
- Real-time step progress: `Inference step X/Y` parsed from subprocess stdout and pushed to the progress bar
- Adaptive frontend polling: 1.5 s while jobs are active, 8 s when idle
- Startup warnings logged if model paths are missing or misconfigured
- Offline-first: no external services required at runtime (models stored locally)
- Windows + NVIDIA GPU support

---

## Known Limitations

**WebSocket endpoint unused**
- File: `app/api/jobs.py`, `@router.websocket("/jobs/{id}/events")`
- The WS endpoint exists but the frontend polls REST instead. Left in place for potential future use.

**Prompt rewriting unimplemented**
- `rewrite_prompt` field is accepted by the API and stored in `settings_json` but the backend never performs rewriting. The UI toggle is disabled (greyed out) to make this clear. Column `rewritten_prompt` on `Job` remains for future use.

**`seed: -1` not resolved before storage**
- When `seed=-1`, a random seed is chosen by the adapter at generation time, but `settings_json` still stores `-1`. Rerun/variation jobs may not reproduce the exact output.

**No authentication / rate limiting**
- All endpoints are unauthenticated. Acceptable for strictly local offline use. Not suitable for network exposure without adding auth.

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

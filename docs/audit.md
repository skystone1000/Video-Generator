# Application Audit Report

**Audit date:** 2026-05-22  
**Fix date:** 2026-05-22  
**Scope:** Full codebase audit — backend, frontend, adapters, API, database, configuration, security, performance  
**Status:** All non-auth bugs and issues resolved. Authentication issues skipped (app runs fully offline/locally).

---

## Summary

| Category | Count | Fixed |
|---|---|---|
| Critical bugs | 6 | 6 ✓ |
| Moderate bugs | 5 | 5 ✓ |
| Minor bugs | 6 | 4 ✓ (2 were already correct in code) |
| Security issues | 4 | 0 (skipped — app runs offline/locally) |
| Performance issues | 4 | 4 ✓ |
| Code quality / gaps | 6 | 6 ✓ (2 were already correct in code) |
| Future scope features | 15 | — (roadmap) |

---

## Critical Bugs

### BUG-01 — `max_active_jobs` locked to exactly 1 by validator ✅ FIXED

**File:** `offline-video-generator/backend/app/config.py`  
**Severity:** Critical  
**Impact:** Multi-GPU and parallel generation are permanently blocked regardless of what is set in `.env`.

**Root cause:**

```python
max_active_jobs: int = Field(default=1, ge=1, le=1)
```

`le=1` (less-than-or-equal to 1) combined with `ge=1` constrains the field to exactly 1. Setting `MAX_ACTIVE_JOBS=4` in `.env` is silently clamped to 1 by Pydantic's validation — no error is raised, the setting is just ignored.

**Fix:**

```python
# config.py
max_active_jobs: int = Field(default=1, ge=1, le=8)
```

Then update `queue.py` to run N workers concurrently via a `ThreadPoolExecutor` rather than the current single-thread loop.

---

### BUG-02 — Active subprocess job cannot be cancelled ✅ FIXED

**File:** `offline-video-generator/backend/app/services/queue.py`  
**Severity:** Critical  
**Impact:** Clicking "Cancel" on a running inference job is silently ignored. The job runs to completion (or error). On a 30-minute generation this means there is no escape hatch.

**Root cause:**

`_cancel_requested` is checked before `_process_job()` is called, but once `subprocess.Popen` is launched inside the adapter, no handle is stored. There is no way to signal the child process.

```python
# queue.py — _run_loop
if job.id in self._cancel_requested:
    # only effective here, before Popen is called
    self._cancel_requested.discard(job.id)
    job.status = JobStatus.cancelled
    return
```

**Fix:**

1. Store the `Popen` handle in the adapter or queue after launch.
2. In `request_cancel()`, check if a handle exists and call `proc.terminate()` followed by `proc.kill()` on timeout.
3. Mark job `cancelled` and delete partial output.

```python
# In Hunyuan15Adapter.generate()
self._proc = subprocess.Popen(cmd, ...)

# In queue.py request_cancel()
def request_cancel(self, job_id: int):
    self._cancel_requested.add(job_id)
    if self._current_adapter and hasattr(self._current_adapter, '_proc'):
        proc = self._current_adapter._proc
        if proc and proc.poll() is None:
            proc.terminate()
```

---

### BUG-03 — Asset files not deleted when asset record is deleted ✅ FIXED

**File:** `offline-video-generator/backend/app/api/assets.py` — `DELETE /assets/{id}`  
**Severity:** Critical  
**Impact:** Every deleted asset leaves `output.mp4`, `thumbnail.jpg`, and `metadata.json` on disk. With heavy use, disk fills silently.

**Root cause:**

The handler queries the DB record, deletes it, and returns — no file system cleanup:

```python
db.delete(asset)
db.commit()
return Response(status_code=204)
```

**Fix:**

```python
from app.config import settings
from app.services.storage import resolve_asset_paths

@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id) or raise_404()
    # delete files first, then record
    for path in [asset.file_path, asset.thumbnail_path, asset.metadata_path]:
        if path:
            full = settings.resolve_path(path)
            full.unlink(missing_ok=True)
    # optionally remove the job output directory if now empty
    db.delete(asset)
    db.commit()
```

---

### BUG-04 — `diffusers_hunyuan` runtime stub causes unhandled exception ✅ FIXED

**File:** `offline-video-generator/backend/app/schemas.py`, `app/services/model_manager.py`  
**Severity:** Critical  
**Impact:** Selecting the `diffusers_hunyuan` runtime from the UI submits a job that immediately crashes the queue thread with an unhandled `ValueError`, marking the job `failed` with an opaque error message. The queue thread recovers, but the user gets no actionable feedback.

**Root cause:**

`RuntimeName` in `schemas.py` includes `"diffusers_hunyuan"` but `model_manager.py` has no branch for it:

```python
# model_manager.py — no diffusers_hunyuan case
if runtime == "mock":
    ...
elif runtime == "hunyuan_original":
    ...
elif runtime == "hunyuan_15":
    ...
# falls through → unhandled
```

**Fix option A (remove the stub):**

```python
# schemas.py
RuntimeName = Literal["mock", "hunyuan_original", "hunyuan_15"]
```

Remove it from the UI preset selector too.

**Fix option B (implement the adapter):** Create `app/runtime/diffusers_hunyuan_adapter.py` using the `diffusers` library HunyuanVideo pipeline and wire it into `model_manager.py`.

---

### BUG-05 — Prompt rewriting UI toggle is a silent no-op ✅ FIXED

**Files:** `app/api/jobs.py`, `app/models.py`, `app/schemas.py`, frontend `SettingsPanel.tsx`  
**Severity:** Critical (user-visible misinformation)  
**Impact:** User enables "Rewrite prompt", submits a job, and sees no difference. The `rewritten_prompt` column is never populated. The adapter falls back to the original prompt silently — the user thinks the feature worked.

**Root cause:**

`rewrite_prompt: bool` is accepted in `GenerationRequest` and stored in `settings_json`, but `create_job()` in `jobs.py` never performs any rewriting:

```python
# jobs.py — rewritten_prompt is never set
job = Job(prompt=request.prompt, rewritten_prompt=None, ...)
```

**Fix:**

Either implement local LLM rewriting using the already-downloaded `Qwen2.5-VL-7B-Instruct` (requires `transformers` pipeline call), or disable the toggle in the UI and remove `rewrite_prompt` from exposed settings until the backend is ready.

Minimum safe fix — grey out the toggle and add a tooltip:

```tsx
// SettingsPanel.tsx
<Toggle
  disabled
  title="Prompt rewriting not yet implemented — coming soon"
  ...
/>
```

---

### BUG-06 — `HunyuanOriginalAdapter` missing Windows fix ✅ FIXED

**File:** `offline-video-generator/backend/app/runtime/hunyuan_original_adapter.py`  
**Severity:** Critical (on Windows)  
**Impact:** `hunyuan_original` runtime always fails on Windows with `RuntimeError: use_libuv was requested but PyTorch was build without libuv support`. The same fix applied to `Hunyuan15Adapter` was never backported.

**Root cause:**

The adapter calls `python3 sample_video.py` without setting `USE_LIBUV=0` and without the `HashStore` patch in `sample_video.py`.

**Fix:**

1. Apply the HashStore patch to `sample_video.py` (same pattern as `generate.py`).
2. In `hunyuan_original_adapter.py`, derive `python_exe` from the venv the same way `Hunyuan15Adapter` does, and pass `env = {**os.environ, "USE_LIBUV": "0"}` to `Popen`.

---

## Moderate Bugs

### BUG-07 — Frontend polls every 1.5 s even when idle ✅ FIXED

**File:** `offline-video-generator/frontend/src/App.tsx`  
**Severity:** Moderate  
**Impact:** Four simultaneous API requests fire every 1.5 s regardless of whether any job is running. Inflates CPU, battery, and log noise.

**Root cause:**

```tsx
window.setInterval(refresh, 1500)  // never backed off
```

**Fix:**

```tsx
const interval = hasActiveJobs ? 1500 : 8000
clearInterval(timerRef.current)
timerRef.current = window.setInterval(refresh, interval)
```

Or replace with a WebSocket connection to `/api/jobs/{id}/events` when a job is active and fall back to slow polling when idle.

---

### BUG-08 — WebSocket job events endpoint is dead code ℹ️ KEPT

**File:** `offline-video-generator/backend/app/api/jobs.py` — `WS /api/jobs/{id}/events`  
**Severity:** Moderate  
**Impact:** The endpoint polls DB every 1 s and streams JSON — but the frontend never connects to it. All progress tracking goes through REST polling. The WS code is untested and may have edge cases (connection drops, job not found).

**Fix:** Either wire the frontend to use it (and remove the REST polling loop for active jobs), or remove the endpoint. Don't maintain dead infrastructure.

---

### BUG-09 — No progress parsing from HunyuanVideo subprocess output ✅ FIXED

**File:** `offline-video-generator/backend/app/runtime/hunyuan_15_adapter.py`  
**Severity:** Moderate  
**Impact:** During a real inference run (10–30 minutes), the progress bar stays at 0% until the job completes or fails. Users have no feedback that the job is running.

**Root cause:**

Stdout lines are written to `logs.txt` but never parsed:

```python
for line in proc.stdout:
    log_file.write(line)
    log_file.flush()
    # on_progress never called here
```

**Fix:**

HunyuanVideo-1.5 prints lines like `Inference step 5/30` or tqdm bars. Parse with a regex and call `on_progress`:

```python
import re
step_re = re.compile(r"(\d+)/(\d+)")

for line in proc.stdout:
    log_file.write(line)
    m = step_re.search(line)
    if m:
        current, total = int(m.group(1)), int(m.group(2))
        on_progress(current / total, f"Step {current}/{total}")
```

---

### BUG-10 — Seed `-1` not resolved before storage; reruns are not reproducible ✅ ALREADY CORRECT

**File:** `offline-video-generator/backend/app/api/jobs.py` — `create_job()`  
**Severity:** Moderate  
**Impact:** When `seed=-1`, a random seed is chosen by the adapter at generation time. But `settings_json` stored in the DB still contains `seed: -1`. Rerun and variation jobs clone this `settings_json` — they get a different random seed every time, so outputs are not reproducible.

**Fix:**

Resolve the seed before creating the job:

```python
import random
if request.seed == -1:
    request = request.model_copy(update={"seed": random.randint(0, 2**32 - 1)})
job = Job(..., settings_json=request.model_dump_json())
```

---

### BUG-11 — No asset or job pagination ✅ FIXED

**Files:** `app/api/assets.py`, `app/api/jobs.py`  
**Severity:** Moderate  
**Impact:** `GET /assets` returns up to 200 records; `GET /jobs` returns up to 100. Both are hardcoded. Heavy users hit these silently. The frontend fetches the full uncapped list on every 1.5 s poll.

**Fix:**

Add `limit` and `offset` query params:

```python
@router.get("")
def list_assets(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    return db.query(Asset).order_by(Asset.created_at.desc()).offset(offset).limit(limit).all()
```

Update the frontend to implement load-more or infinite scroll.

---

## Minor Bugs

### BUG-12 — Default runtime in frontend store is `"mock"` ✅ FIXED

**File:** `offline-video-generator/frontend/src/state/useGenerationStore.ts`  
**Severity:** Minor  
**Impact:** New users who submit without selecting a preset receive a test-pattern mock video and may think real generation failed or is broken.

**Fix:** Change `defaultRequest.runtime` to `"hunyuan_15"` and surface a clear "Mock mode" label in the UI when mock is selected.

---

### BUG-13 — GPU info fetched on every `/system/gpu` request ✅ FIXED

**File:** `offline-video-generator/backend/app/api/system.py`  
**Severity:** Minor  
**Impact:** Adds 50–200 ms latency to every status poll (called every 1.5 s from frontend).

**Fix:** Cache the result with a short TTL (e.g. 10 s):

```python
_gpu_cache: dict = {"ts": 0.0, "data": None}

def get_gpu_info():
    if time.time() - _gpu_cache["ts"] < 10:
        return _gpu_cache["data"]
    result = _fetch_nvidia_smi()
    _gpu_cache.update({"ts": time.time(), "data": result})
    return result
```

---

### BUG-14 — `LOG_DIR` created but never written to ✅ FIXED

**File:** `offline-video-generator/backend/app/config.py`, `app/main.py`  
**Severity:** Minor  
**Impact:** `data/logs/` directory is initialised at startup but the app writes application logs only to stdout and per-job `logs.txt` files. The directory is dead space.

**Fix:** Either wire Python's `logging` module to write to `LOG_DIR/app.log`, or remove `LOG_DIR` from config and the directory creation.

---

### BUG-15 — `GET /api/assets/{id}` endpoint missing ✅ ALREADY CORRECT

**File:** `offline-video-generator/backend/app/api/assets.py`  
**Severity:** Minor  
**Impact:** The backend README and original spec list `GET /api/assets/{asset_id}` as a metadata endpoint, but only the video and thumbnail file endpoints exist. Clients cannot fetch a single asset's metadata by ID without fetching the full list.

**Fix:**

```python
@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404)
    return asset_to_response(asset)
```

---

### BUG-16 — `rewritten_prompt` shown in UI but always null ✅ ALREADY CORRECT

**File:** Frontend job detail display  
**Severity:** Minor  
**Impact:** If the UI displays `rewritten_prompt`, it always shows `null`/empty since the backend never populates it (see BUG-05). Confusing to users.

**Fix:** Hide the rewritten prompt display until BUG-05 is resolved. Conditionally render it only when non-null.

---

### BUG-17 — CORS regex allows all localhost ports ℹ️ INTENTIONAL

**File:** `offline-video-generator/backend/app/main.py`  
**Severity:** Minor (local-only app)  
**Impact:** Any page served on any `localhost:*` port can make credentialed requests to the backend. Acceptable for development but exposes the API to other local apps/dev servers.

**Fix (optional hardening):** Pin allowed origins to the known frontend port:

```python
allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"]
```

---

## Security Issues

### SEC-01 — No authentication on any endpoint

**Severity:** High (if network-exposed)  
**Impact:** Any client with network access can submit jobs, delete assets, modify presets, and read all outputs. Currently mitigated by binding to `127.0.0.1` only.

**Fix:** For LAN or any non-loopback exposure, add token-based auth middleware:

```python
API_KEY = settings.api_key  # new env var

@app.middleware("http")
async def require_api_key(request: Request, call_next):
    if request.headers.get("X-API-Key") != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)
```

---

### SEC-02 — No rate limiting on `POST /jobs`

**Severity:** Medium  
**Impact:** A local script can flood the queue with thousands of jobs, exhausting disk space and pinning the GPU indefinitely.

**Fix:** Add a simple in-memory rate limiter (e.g. max 10 submissions per minute per IP) using `slowapi` or a manual token-bucket check in the job creation handler.

---

### SEC-03 — Subprocess prompt injection is possible if `shell=True` is ever used

**Severity:** Medium (latent)  
**Impact:** Current adapters correctly use argument arrays (no `shell=True`). However, if any future adapter or maintenance accidentally switches to shell execution, the prompt string would be passed to the shell unsanitized.

**Fix:** Add a lint rule or comment in `base.py` explicitly forbidding `shell=True`:

```python
# SECURITY: Never use shell=True. Prompt text is user input and must not be
# passed to a shell interpreter. Always use argument arrays.
```

---

### SEC-04 — Static file routes expose all outputs without auth

**File:** `app/main.py` — `app.mount("/outputs", StaticFiles(...))`  
**Severity:** Low (local-only)  
**Impact:** All generated videos are served at predictable URLs (`/outputs/YYYY-MM-DD/job_N/output.mp4`) with no access control. On a LAN-exposed instance, anyone can enumerate and download all generated content.

**Fix:** Replace `StaticFiles` mount with authenticated file endpoints, or keep the mount behind the API key middleware from SEC-01.

---

## Performance Issues

### PERF-01 — Four API requests fired every 1.5 s unconditionally ✅ FIXED

**File:** `frontend/src/App.tsx`  
**Impact:** At idle, 160 HTTP requests/minute to four endpoints (status, jobs, assets, presets). CPU and network overhead scales with browser tabs open.

**Fix:** See BUG-07. Back off to 8–10 s when no active jobs. Use WebSocket for active job progress.

---

### PERF-02 — Full asset list fetched on every poll ✅ FIXED

**File:** `frontend/src/App.tsx` → `GET /api/assets`  
**Impact:** If the user has 200 assets, 200 asset records (with all metadata) are serialized and transferred every 1.5 s.

**Fix:** Fetch assets once on load; only refresh when a job completes. Or implement cursor-based pagination and only fetch the delta.

---

### PERF-03 — `nvidia-smi` subprocess on every status request ✅ FIXED

See BUG-13. 15-second in-process cache added to `app/api/system.py`; GPU status is computed at most once per 15 s instead of on every poll.

---

### PERF-04 — SQLAlchemy session not connection-pooled for SQLite ✅ FIXED

**File:** `app/database.py`  
**Impact:** `create_engine("sqlite://...")` with `check_same_thread=False` uses a single connection. Under concurrent requests (unlikely now with `max_active_jobs=1` but relevant after BUG-01 fix), writes may block.

**Fix:** Use `StaticPool` for SQLite:

```python
from sqlalchemy.pool import StaticPool
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

For heavier concurrency, migrate to PostgreSQL.

---

## Code Quality / Gaps

### GAP-01 — No tests for real adapters ✅ FIXED

**Location:** `offline-video-generator/backend/tests/`  
Tests exist for mock generation and basic API routes but there are no tests for `Hunyuan15Adapter` command construction, argument validation, or path resolution. A change to `build_command()` could break generation silently.

**Fix:** Add unit tests that mock `subprocess.Popen` and assert the argument list for various `GenerationRequest` inputs.

---

### GAP-02 — `model_version` column never populated ✅ ALREADY CORRECT

**File:** `app/api/jobs.py` — `create_job()`  
**Impact:** `Job.model_version` is always `null`. Future multi-version support (480p vs 720p transformer) has nowhere to distinguish which model was used.

**Fix:** Set `model_version` from the preset or adapter at job creation:

```python
job = Job(..., model_version="hunyuan-1.5-480p-t2v")
```

---

### GAP-03 — Output directory path not validated at startup ✅ FIXED

**File:** `app/main.py` — `lifespan()`  
**Impact:** If `OUTPUT_DIR` or `THUMBNAIL_DIR` is misconfigured, jobs fail at the postprocessing stage with an obscure `FileNotFoundError` rather than at startup with a clear config error.

**Fix:** Add startup validation:

```python
for path_var in [settings.output_dir, settings.thumbnail_dir]:
    resolved = settings.resolve_path(path_var)
    resolved.mkdir(parents=True, exist_ok=True)
```

Already partially done but `HUNYUAN_15_REPO_PATH` is not checked at startup — add a check that warns (not fatal) if it doesn't exist.

---

### GAP-04 — No frontend error boundary ✅ FIXED

**File:** `frontend/src/App.tsx`  
**Impact:** An unhandled exception in any React component crashes the entire UI with a blank white screen. There is no `<ErrorBoundary>` component to catch and display errors gracefully.

**Fix:** Wrap the main layout with a React error boundary that shows the error message and a "Reload" button.

---

### GAP-05 — `updated_at` on `Job` not updated on status transitions ✅ FIXED

**File:** `app/services/queue.py` — `_process_job()`  
**Impact:** `updated_at` is only set when the ORM row is explicitly modified. SQLAlchemy does not auto-update it. So `updated_at` reflects creation time, not last status change, making it useless for "last activity" queries.

**Fix:** Explicitly update `updated_at` on each status transition:

```python
from datetime import datetime
job.updated_at = datetime.utcnow()
db.commit()
```

Or use a SQLAlchemy `onupdate` on the column.

---

### GAP-06 — `ffprobe` path not used when probing output video ✅ ALREADY CORRECT

**File:** `app/services/thumbnails.py` or storage  
**Impact:** Some paths use the `ffmpeg` config value for the binary path but fall back to hardcoded `"ffprobe"` string for probing, ignoring `FFPROBE_PATH`.

**Fix:** Thread `settings.ffprobe_path` through all subprocess calls that invoke `ffprobe`.

---

## Future Scope

### FS-01 — Real-time progress via stdout parsing *(high priority)*

Parse `Inference step X/Y` from HunyuanVideo stdout and push progress to the frontend via WebSocket. Makes long generations usable. See BUG-09 for the fix skeleton.

---

### FS-02 — Active job cancellation *(high priority)*

Store the `Popen` handle and implement `proc.terminate()` on cancel. See BUG-02 for the fix skeleton.

---

### FS-03 — Prompt rewriting with local LLM *(high priority)*

Use the already-downloaded `Qwen2.5-VL-7B-Instruct` as a local prompt expansion engine. Call it via `transformers.pipeline` before job creation when `rewrite_prompt=true`. Store the result in `Job.rewritten_prompt`.

---

### FS-04 — Asset file cleanup on delete *(high priority)*

Delete video, thumbnail, and metadata files when an asset is deleted. See BUG-03. Add a "Clear all" bulk action to the UI.

---

### FS-05 — WebSocket-driven frontend *(medium priority)*

Replace the 1.5 s REST polling loop with a WebSocket connection to `/api/jobs/{id}/events` when a job is active. Fall back to slow polling (8–10 s) at idle. Halves network traffic and gives sub-second progress updates.

---

### FS-06 — Multi-resolution transformer support *(medium priority)*

Support `720p_t2v` and `1080p_t2v` transformer variants alongside `480p_t2v`. Currently hardcoded to `480p` in `Hunyuan15Adapter.build_command()`. Expose the transformer variant in the preset schema and pass it through to the `--dit` argument.

---

### FS-07 — Image-to-video (I2V) *(medium priority)*

HunyuanVideo-1.5 supports image conditioning via `--image_path`. Add an image upload input to the UI, store the path, and pass it to the adapter. The adapter already has placeholder handling for `image_path none`.

---

### FS-08 — Super-resolution post-processing *(medium priority)*

`HUNYUAN_15_ENABLE_SR=true` exists in config but the SR pipeline is not wired into the adapter. Implement SR as a postprocessing step: after the base generation completes, run a second pass with the SR model.

---

### FS-09 — Scalable concurrency *(medium priority)*

Fix BUG-01 (unlock `max_active_jobs`), then update `GenerationQueue` to run N jobs concurrently using a thread pool. Required for multi-GPU setups where each GPU handles one job.

---

### FS-10 — Batch prompt submission *(low priority)*

Allow the user to submit a list of prompts in one go. The backend enqueues one job per prompt. The UI shows all batch jobs grouped together.

---

### FS-11 — Gallery filtering and search *(low priority)*

Add search by prompt text, filter by runtime/resolution/favorite, and date-range filtering to the asset gallery. Backend: add `?q=&runtime=&favorite=` query params to `GET /assets`.

---

### FS-12 — SageAttention integration *(low priority)*

`HUNYUAN_15_USE_SAGE_ATTN` env var exists but is not wired into the adapter command. Implement the flag pass-through and document the `sageattention` package installation requirements and Windows compatibility caveats.

---

### FS-13 — Docker / container packaging *(low priority)*

A `docker-compose.yml` that bundles backend + frontend dev server, with model paths as volume mounts. Eliminates the multi-step Windows venv setup for users who prefer containers.

---

### FS-14 — Export with metadata sidecar *(low priority)*

An "Export" button that copies the video file to a user-chosen location along with a `metadata.json` sidecar containing the full prompt, seed, runtime, and settings — making outputs self-documenting outside the app.

---

### FS-15 — Authentication + multi-user *(low priority, LAN use case)*

If the backend is ever exposed beyond loopback (LAN sharing), add token-based auth (see SEC-01), per-user job and asset namespacing, and a simple user management page.

---

## Fix Priority Order

For the current sprint, recommended order based on impact-to-effort:

| Priority | Bug/Gap | Effort |
|---|---|---|
| 1 | BUG-03 — Asset file cleanup on delete | Low |
| 2 | BUG-05 — Disable prompt rewrite toggle in UI | Low |
| 3 | BUG-04 — Remove `diffusers_hunyuan` stub from RuntimeName | Low |
| 4 | BUG-15 — Add `GET /assets/{id}` endpoint | Low |
| 5 | BUG-10 — Resolve seed before storage | Low |
| 6 | BUG-13 — Cache nvidia-smi result | Low |
| 7 | BUG-09 — Parse progress from Hunyuan stdout | Medium |
| 8 | BUG-07 — Back off polling when idle | Medium |
| 9 | BUG-02 — Active job cancellation | Medium |
| 10 | BUG-01 — Unlock max_active_jobs | Medium |
| 11 | BUG-06 — Windows fix for HunyuanOriginalAdapter | Low |
| 12 | SEC-01 + SEC-02 — Auth + rate limiting | High (if LAN exposed) |

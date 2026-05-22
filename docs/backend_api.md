# Backend API Reference

FastAPI backend for the offline video generator.

## Running the Backend

```powershell
cd offline-video-generator\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy ..\.env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## API Surface

### System

- `GET  /api/system/status` — backend health, queue depth, active jobs, GPU VRAM info
- `GET  /api/system/config` — non-sensitive settings snapshot

### Presets

- `GET    /api/presets` — list all presets
- `POST   /api/presets` — create preset
- `PUT    /api/presets/{preset_id}` — update preset
- `DELETE /api/presets/{preset_id}` — delete preset

### Jobs

- `POST /api/jobs` — submit a new generation job
- `GET  /api/jobs` — list jobs (last 100, newest first)
- `GET  /api/jobs/{job_id}` — get single job
- `POST /api/jobs/{job_id}/cancel` — cancel a queued job
- `POST /api/jobs/{job_id}/rerun` — clone and requeue a completed/failed job
- `POST /api/jobs/{job_id}/variation` — rerun with partial setting overrides
- `WS   /api/jobs/{job_id}/events` — WebSocket stream of job progress (polls DB every 1 s)

### Assets

- `GET    /api/assets` — list assets (last 200, newest first)
- `GET    /api/assets/{asset_id}` — get asset metadata
- `GET    /api/assets/{asset_id}/video` — serve video file (MP4)
- `GET    /api/assets/{asset_id}/thumbnail` — serve thumbnail (JPEG)
- `PATCH  /api/assets/{asset_id}` — update favorite flag or tags
- `DELETE /api/assets/{asset_id}` — delete asset DB record

## Job Status Values

```text
queued → loading_model → generating → postprocessing → completed
                                                      → failed
                                                      → cancelled
```

## Notes

- Cancel only works for jobs still in `queued` state. Running subprocess jobs cannot be interrupted.
- The WebSocket `/api/jobs/{job_id}/events` endpoint exists but is not consumed by the frontend (frontend uses REST polling every 1.5 s instead).
- Asset delete removes the database record but does not delete files on disk.
- For full architecture and design decisions see [ARCHITECTURE.md](ARCHITECTURE.md).

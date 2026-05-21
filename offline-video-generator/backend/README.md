# Backend

FastAPI backend for the offline video generator.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## API Surface

- `GET /api/system/status`
- `GET /api/system/gpu`
- `GET /api/presets`
- `POST /api/jobs`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/{job_id}/rerun`
- `POST /api/jobs/{job_id}/variation`
- `GET /api/assets`
- `GET /api/assets/{asset_id}`
- `GET /api/assets/{asset_id}/video`
- `GET /api/assets/{asset_id}/thumbnail`
- `WS /api/jobs/{job_id}/events`

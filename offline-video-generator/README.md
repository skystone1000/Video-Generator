# Offline Video Generator

Local text-to-video creator workspace with a Python backend, React frontend, SQLite persistence, a single-machine job queue, and runtime adapters for mock generation plus Tencent HunyuanVideo variants.

This project starts with an end-to-end mock runtime so the UI, job queue, asset library, and reproducibility metadata can be developed before large model weights or GPU hardware are available.

## Current Slice

- FastAPI backend with system, job, asset, and preset endpoints.
- SQLite job and asset persistence.
- Background generation worker with one active job at a time.
- Mock runtime that uses `ffmpeg` or an optional static sample MP4.
- HunyuanVideo and HunyuanVideo-1.5 adapter scaffolds with path validation and subprocess command construction.
- React + Vite creator workspace wired to the API.

## Local Development

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

## Mock Runtime

The mock runtime does not require a GPU or model weights. It needs either:

- `ffmpeg` on `PATH`, or
- `MOCK_SAMPLE_MP4_PATH` pointing to an existing local MP4 that can be copied for each completed job.

If neither is available, jobs fail with a clear local tooling error.

## Real Runtime Setup

Set these paths in `backend/.env`:

```text
VIDEO_RUNTIME=hunyuan_original
HUNYUAN_ORIGINAL_REPO_PATH=/models/HunyuanVideo
HUNYUAN_ORIGINAL_CKPT_PATH=/models/HunyuanVideo/ckpts
```

or:

```text
VIDEO_RUNTIME=hunyuan_15
HUNYUAN_15_REPO_PATH=/models/HunyuanVideo-1.5
HUNYUAN_15_MODEL_PATH=/models/HunyuanVideo-1.5/weights
```

The adapters intentionally shell out with argument arrays, not `shell=True`. Check the local upstream repos before running real inference and update the adapter command builders if the upstream scripts differ.

## Offline Use

Normal runtime is designed to use only local assets, wheels, npm packages, model source, and model weights. See:

- `scripts/bootstrap_online.md`
- `scripts/package_offline.md`

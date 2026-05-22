# Offline Video Generator — App Overview

Local text-to-video creator workspace with a Python backend, React frontend, SQLite persistence, a single-machine job queue, and runtime adapters for mock generation plus Tencent HunyuanVideo-1.5.

This project starts with an end-to-end mock runtime so the UI, job queue, asset library, and reproducibility metadata can be developed before large model weights or GPU hardware are available.

## Current State

- FastAPI backend with system, job, asset, and preset endpoints.
- SQLite job and asset persistence.
- Background generation worker with one active job at a time.
- Mock runtime that uses `ffmpeg` or an optional static sample MP4.
- HunyuanVideo-1.5 adapter with Windows-compatible subprocess execution (calls `python.exe generate.py` directly, not `torchrun`).
- React + Vite creator workspace wired to the API.

## Local Development

Backend (Windows):

```powershell
cd offline-video-generator\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy ..\.env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```powershell
cd offline-video-generator\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

## Mock Runtime

The mock runtime does not require a GPU or model weights. It needs either:

- `ffmpeg` on `PATH`, or
- `MOCK_SAMPLE_MP4_PATH` pointing to an existing local MP4 that can be copied for each completed job.

If neither is available, jobs fail with a clear local tooling error.

## Real Runtime Setup (HunyuanVideo-1.5)

Set these paths in `backend/.env` using **absolute paths**:

```text
VIDEO_RUNTIME=hunyuan_15
HUNYUAN_15_REPO_PATH=E:\models\HunyuanVideo-1.5
HUNYUAN_15_MODEL_PATH=E:\models\HunyuanVideo-1.5\ckpts
```

Models are stored outside the project repository on any drive you choose. Relative paths will not work correctly at runtime.

For model download instructions, file placement, and the required Windows compatibility patch for `generate.py`, see **[models_setup.md](models_setup.md)**.

## Offline Use

Normal runtime uses only local assets, wheels, npm packages, model source, and model weights. See:

- [bootstrap_online.md](bootstrap_online.md) — one-time online setup steps
- [package_offline.md](package_offline.md) — offline runtime packaging
- [installation.md](installation.md) — full Windows + NVIDIA GPU installation guide

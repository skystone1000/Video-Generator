# Offline Runtime Package

Expected package contents:

```text
offline-video-generator/
wheelhouse/
models/
  HunyuanVideo/
  HunyuanVideo-1.5/
ffmpeg/
checksums.txt
```

## Backend Install

```bash
cd offline-video-generator/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links ../../wheelhouse -e ".[dev]"
cp ../.env.example .env
```

Edit `backend/.env` so all model and ffmpeg paths point to local files.

## Frontend Install

Either run from a prepared npm cache or serve a prebuilt `frontend/dist` bundle. For development:

```bash
cd offline-video-generator/frontend
npm install --offline
npm run dev -- --host 127.0.0.1 --port 5173
```

## Runtime

```bash
cd offline-video-generator/backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The app binds to `127.0.0.1` by default and uses local SQLite plus local output folders.

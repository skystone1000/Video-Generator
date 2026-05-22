# Offline Runtime Package

Expected package contents after completing [bootstrap_online.md](bootstrap_online.md):

```text
Video-Generator\
wheelhouse\
<YOUR_MODELS_DRIVE>\
  HunyuanVideo-1.5\
    generate.py
    ckpts\
ffmpeg\       (if bundled separately)
checksums.csv
```

Models live outside the project at whatever absolute path you configured. See [models_setup.md](models_setup.md) for the expected `ckpts\` directory structure.

## Backend Install

```powershell
cd offline-video-generator\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --no-index --find-links ..\..\wheelhouse -e ".[dev]"
copy ..\.env.example .env
```

Edit `backend\.env` so `HUNYUAN_15_REPO_PATH` and `HUNYUAN_15_MODEL_PATH` point to the absolute local paths where you placed the model code and checkpoints.

## Frontend Install

Either serve from a prebuilt `frontend\dist` bundle (built during bootstrap) or install from a prepared npm cache:

```powershell
cd offline-video-generator\frontend
npm install --offline
npm run dev -- --host 127.0.0.1 --port 5173
```

To serve the prebuilt bundle without Node at runtime:

```powershell
# Serve dist/ with any static file server, e.g. python -m http.server
cd offline-video-generator\frontend\dist
python -m http.server 5173
```

## Runtime

Open two PowerShell terminals.

**Terminal 1 — Backend:**

```powershell
cd offline-video-generator\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — Frontend:**

```powershell
cd offline-video-generator\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

The app binds to `127.0.0.1` by default and uses local SQLite plus local output folders under `backend\data\`.

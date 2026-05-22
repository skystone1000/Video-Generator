# Video-Generator

Offline video generation app powered by HunyuanVideo-1.5. See [docs/installation.md](docs/installation.md) for the full Windows + NVIDIA GPU setup guide.

---

## Model Configuration

Models are stored **outside the project** on any drive you choose. The project itself contains no model files.

You configure two paths in `offline-video-generator/backend/.env`:

| Variable | What it points to |
|---|---|
| `HUNYUAN_15_REPO_PATH` | The cloned [HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) code repository (contains `generate.py`) |
| `HUNYUAN_15_MODEL_PATH` | The downloaded model checkpoints folder (`ckpts/`) |

Both accept absolute paths and can point to different drives.

**Example `backend/.env` entries:**

```env
HUNYUAN_15_REPO_PATH=E:\models\HunyuanVideo-1.5
HUNYUAN_15_MODEL_PATH=E:\models\HunyuanVideo-1.5\ckpts
```

Or with the code repo and checkpoints on separate drives:

```env
HUNYUAN_15_REPO_PATH=C:\AI\HunyuanVideo-1.5
HUNYUAN_15_MODEL_PATH=E:\models\ckpts\HunyuanVideo-1.5
```

Copy `offline-video-generator/.env.example` to `offline-video-generator/backend/.env` and fill in these two paths before starting the backend.

For the full list of models to download, download links, file placement, and the Windows compatibility patch for `generate.py`, see **[docs/models_setup.md](docs/models_setup.md)**.

## Documentation

All documentation lives in [`docs/`](docs/):

| File | Purpose |
|---|---|
| [installation.md](docs/installation.md) | Full Windows + NVIDIA GPU setup guide |
| [models_setup.md](docs/models_setup.md) | Model download guide, file placement, current status |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, layers, data flow, DB schema |
| [CODEBASE.md](docs/CODEBASE.md) | File-by-file code reference |
| [FEATURES.md](docs/FEATURES.md) | Current features, known bugs, future roadmap |
| [app_overview.md](docs/app_overview.md) | App-level overview and quick-start |
| [backend_api.md](docs/backend_api.md) | API endpoint reference |
| [bootstrap_online.md](docs/bootstrap_online.md) | One-time online bootstrap steps |
| [package_offline.md](docs/package_offline.md) | Offline runtime packaging |
| [audit.md](docs/audit.md) | Full audit: bugs with fixes, security, performance, future scope |
| [pipeline_spec.md](docs/pipeline_spec.md) | Original implementation spec and build status |

---

## Project Structure

```
Video-Generator/
├── docs/
│   ├── installation.md          # Full Windows setup guide
│   ├── models_setup.md          # Model download guide
│   ├── ARCHITECTURE.md          # System architecture
│   ├── CODEBASE.md              # File-by-file code reference
│   ├── FEATURES.md              # Features, bugs, roadmap
│   ├── app_overview.md          # App overview and quick-start
│   ├── backend_api.md           # API endpoint reference
│   ├── bootstrap_online.md      # Online bootstrap steps
│   ├── package_offline.md       # Offline packaging
│   ├── pipeline_spec.md         # Original implementation spec
│   └── audit.md                 # Full audit report with fixes
├── offline-video-generator/
│   ├── .env.example             # Copy to backend/.env and fill in model paths
│   ├── backend/
│   │   ├── .env                 # Your local config (gitignored)
│   │   ├── .venv/               # Python venv (gitignored)
│   │   └── app/
│   └── frontend/
└── README.md
```

Models live at whatever path you set in `.env` — not inside this repository.

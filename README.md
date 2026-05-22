# Video-Generator

Offline video generation app powered by HunyuanVideo-1.5. See [installation.md](installation.md) for the full Windows + NVIDIA GPU setup guide.

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

---

## Project Structure

```
Video-Generator/
├── docs/
│   └── models_setup.md          # Model download guide
├── offline-video-generator/
│   ├── .env.example             # Copy to backend/.env and fill in model paths
│   ├── backend/
│   │   ├── .env                 # Your local config (gitignored)
│   │   ├── .venv/               # Python venv (gitignored)
│   │   └── app/
│   └── frontend/
├── installation.md              # Full Windows setup guide
└── README.md
```

Models live at whatever path you set in `.env` — not inside this repository.

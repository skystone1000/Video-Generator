# Models Setup Guide

This guide covers every model required to run the HunyuanVideo-1.5 pipeline, where to download each one, and where to place the files.

Models live **outside the project** — on any drive you choose. The project repository contains no model files.

---

## Configuration

Two paths must be set in `offline-video-generator/backend/.env` before the backend will start real generation:

| Variable | What it points to |
|---|---|
| `HUNYUAN_15_REPO_PATH` | The cloned HunyuanVideo-1.5 code repository (folder containing `generate.py`) |
| `HUNYUAN_15_MODEL_PATH` | The downloaded model checkpoints (`ckpts/` folder) |

Both accept **absolute paths** and can be on different drives.

**Example:**

```env
HUNYUAN_15_REPO_PATH=E:\models\HunyuanVideo-1.5
HUNYUAN_15_MODEL_PATH=E:\models\HunyuanVideo-1.5\ckpts
```

Copy `offline-video-generator/.env.example` to `offline-video-generator/backend/.env` and fill in these two values.

---

## Step 1 — Clone the HunyuanVideo-1.5 Code Repository

```powershell
git clone https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5.git E:\models\HunyuanVideo-1.5
```

Replace `E:\models\HunyuanVideo-1.5` with your chosen path. Set that same path as `HUNYUAN_15_REPO_PATH`.

### Apply the Windows Compatibility Patch

On Windows, PyTorch is typically built without libuv support, which causes `torchrun` to crash. The app calls `python generate.py` directly instead, but `generate.py` must initialise the distributed process group using `HashStore`.

Open `<HUNYUAN_15_REPO_PATH>\generate.py` and add the following block immediately after the `from torch import distributed as dist` import (around line 32):

```python
# Windows fix: initialize process group with HashStore to avoid libuv dependency.
if not dist.is_initialized():
    _store = dist.HashStore()
    dist.init_process_group(
        backend="gloo",
        store=_store,
        rank=int(os.environ.get("RANK", "0")),
        world_size=int(os.environ.get("WORLD_SIZE", "1")),
    )
```

This patch is required on Windows. Without it all generation jobs will fail with:
```
RuntimeError: use_libuv was requested but PyTorch was build without libuv support
```

---

## Step 2 — Download Model Checkpoints

---

All checkpoints go inside the folder you set as `HUNYUAN_15_MODEL_PATH` (referred to below as `ckpts\`).

## Download Checklist

| Model | Source | Size | Status |
|---|---|---|---|
| HunyuanVideo-1.5 transformer (480p T2V) | HuggingFace | ~9.8 GB | Incomplete |
| HunyuanVideo-1.5 VAE | HuggingFace | ~400 MB | Missing |
| HunyuanVideo-1.5 Scheduler | HuggingFace | ~1 KB | Done ✓ |
| Qwen2.5-VL-7B-Instruct (LLM text encoder) | HuggingFace | ~15.5 GB | Incomplete (shard 5/5 only) |
| byt5-small (character text encoder) | HuggingFace | ~300 MB | Incomplete (weights missing) |
| Glyph-SDXL-v2 (glyph encoder) | ModelScope | ~500 MB | Done ✓ |
| SigLIP vision encoder | HuggingFace (gated) | ~880 MB | Missing |

**Total remaining to download: ~27 GB**

---

## Models

### 1. HunyuanVideo-1.5 — Transformer, VAE, Scheduler

**Source:** https://huggingface.co/tencent/HunyuanVideo-1.5/tree/main

Download only the folders needed for 480p Text-to-Video (smallest configuration). Skip all other transformer versions to save ~60 GB.

**Files to download:**

| Repo path | Local destination | Size |
|---|---|---|
| `transformer/480p_t2v/diffusion_pytorch_model.safetensors` | `ckpts\transformer\480p_t2v\` | ~9.8 GB |
| `vae/` (entire folder) | `ckpts\vae\` | ~400 MB |
| `scheduler/scheduler_config.json` | `ckpts\scheduler\` | Done ✓ |

> **Note:** `config.json` for `480p_t2v` is already present. Only the `.safetensors` weight file is missing.

---

### 2. Qwen2.5-VL-7B-Instruct — LLM Text Encoder

**Source:** https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/tree/main

Download all files from the repository root.

**Destination:** `ckpts\text_encoder\llm\`

**Missing files (shards 1–4 of 5):**

| File | Size |
|---|---|
| `model-00001-of-00005.safetensors` | ~3.8 GB |
| `model-00002-of-00005.safetensors` | ~3.8 GB |
| `model-00003-of-00005.safetensors` | ~3.8 GB |
| `model-00004-of-00005.safetensors` | ~3.8 GB |
| `model-00005-of-00005.safetensors` | Done ✓ |
| All config/tokenizer files | Done ✓ |

---

### 3. byt5-small — Character-level Text Encoder

**Source:** https://huggingface.co/google/byt5-small/tree/main

**Destination:** `ckpts\text_encoder\byt5-small\`

**Missing file:**

| File | Size |
|---|---|
| `pytorch_model.bin` | ~300 MB |

> Config, tokenizer, and other files are already present. Only the PyTorch weights are missing.

---

### 4. Glyph-SDXL-v2 — Glyph/ByT5 Encoder

**Already fully downloaded ✓**

**Source (for reference):** https://modelscope.cn/models/AI-ModelScope/Glyph-SDXL-v2/files

**Location:** `ckpts\text_encoder\Glyph-SDXL-v2\`

---

### 5. SigLIP Vision Encoder — from FLUX.1-Redux-dev

**Source:** https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev/tree/main

> **GATED MODEL** — You must request access at the link above and wait for approval before downloading. Log in to HuggingFace and click "Request access" on that page.

Download only two subfolders (do not download the full FLUX model):

| Repo path | Local destination | Size |
|---|---|---|
| `image_encoder/` (entire folder) | `ckpts\vision_encoder\siglip\image_encoder\` | ~878 MB |
| `feature_extractor/` (entire folder) | `ckpts\vision_encoder\siglip\feature_extractor\` | ~1 KB |

---

## Final Directory Structure

After all downloads complete, `ckpts\` should look like this:

```
E:\models\HunyuanVideo-1.5\ckpts\
│
├── config.json
├── LICENSE
├── NOTICE
├── README.md
│
├── transformer\
│   └── 480p_t2v\
│       ├── config.json
│       └── diffusion_pytorch_model.safetensors        ← download from HunyuanVideo-1.5
│
├── vae\                                                ← download entire folder from HunyuanVideo-1.5
│   ├── config.json
│   └── diffusion_pytorch_model.safetensors
│
├── scheduler\
│   └── scheduler_config.json                          ✓ done
│
└── text_encoder\
    │
    ├── llm\                                            ← Qwen2.5-VL-7B-Instruct
    │   ├── config.json                                 ✓ done
    │   ├── tokenizer.json                              ✓ done
    │   ├── tokenizer_config.json                       ✓ done
    │   ├── merges.txt                                  ✓ done
    │   ├── vocab.json                                  ✓ done
    │   ├── generation_config.json                      ✓ done
    │   ├── model.safetensors.index.json                ✓ done
    │   ├── model-00001-of-00005.safetensors            ← download
    │   ├── model-00002-of-00005.safetensors            ← download
    │   ├── model-00003-of-00005.safetensors            ← download
    │   ├── model-00004-of-00005.safetensors            ← download
    │   └── model-00005-of-00005.safetensors            ✓ done
    │
    ├── byt5-small\                                     ← google/byt5-small
    │   ├── config.json                                 ✓ done
    │   ├── tokenizer_config.json                       ✓ done
    │   ├── special_tokens_map.json                     ✓ done
    │   └── pytorch_model.bin                           ← download
    │
    └── Glyph-SDXL-v2\                                 ✓ fully done
        └── checkpoints\
            ├── byt5_model.pt
            ├── byt5_mapper.pt
            ├── unet_inserted_attn.pt
            └── unet_lora.pt

vision_encoder\                                         ← from FLUX.1-Redux-dev (gated)
    └── siglip\
        ├── image_encoder\                              ← download image_encoder/ subfolder
        │   ├── config.json
        │   └── model.safetensors
        └── feature_extractor\                          ← download feature_extractor/ subfolder
            └── preprocessor_config.json
```

---

## Download Method (CLI)

If you prefer CLI downloads over manual file placement, install the HuggingFace CLI first:

```bash
pip install -U "huggingface_hub[cli]"
```

Then run each command from your `HUNYUAN_15_MODEL_PATH` folder (e.g. `E:\models\HunyuanVideo-1.5\ckpts\`):

```bash
# 1. HunyuanVideo-1.5 transformer (480p T2V only) + VAE + scheduler
hf download tencent/HunyuanVideo-1.5 \
  --include "transformer/480p_t2v/**" "vae/**" "scheduler/**" \
  --local-dir .

# 2. LLM text encoder (Qwen2.5-VL-7B-Instruct) — resumes incomplete download
hf download Qwen/Qwen2.5-VL-7B-Instruct \
  --local-dir ./text_encoder/llm

# 3. byt5-small — only the pytorch weights
hf download google/byt5-small \
  --include "pytorch_model.bin" \
  --local-dir ./text_encoder/byt5-small

# 4. SigLIP vision encoder — requires HF token + prior access approval
hf download black-forest-labs/FLUX.1-Redux-dev \
  --include "image_encoder/**" "feature_extractor/**" \
  --local-dir ./vision_encoder/siglip \
  --token YOUR_HF_TOKEN_HERE
```

---

## After Downloads Complete

1. Restart the backend server — the new `hunyuan-480p-fast` preset will be seeded into the database.
2. In the UI, select the **`hunyuan-480p-fast`** preset when submitting a job.
3. This preset uses `runtime: hunyuan_15`, `resolution: 480p`, 29 frames, 12 inference steps — the fastest real generation configuration.

---

## Troubleshooting

**`FileNotFoundError: .../text_encoder/llm not found`**
→ LLM shards 1–4 are missing. Download all files from `Qwen/Qwen2.5-VL-7B-Instruct`.

**`FileNotFoundError: .../vision_encoder/siglip not found`**
→ Vision encoder is missing. Request access to `black-forest-labs/FLUX.1-Redux-dev` on HuggingFace, then download `image_encoder/` and `feature_extractor/` subfolders.

**`RuntimeError: use_libuv was requested but PyTorch was build without libuv support`**
→ This was caused by the old adapter calling `torchrun` directly on Windows. Fixed in `hunyuan_15_adapter.py` (uses `python.exe generate.py` now) and `generate.py` (uses `HashStore` for single-GPU init). No action needed if running the latest code.

**`Could not find 480p_t2v in ckpts/transformer`**
→ The transformer weights file (`diffusion_pytorch_model.safetensors`) is missing from `ckpts\transformer\480p_t2v\`. Download it from `tencent/HunyuanVideo-1.5`.

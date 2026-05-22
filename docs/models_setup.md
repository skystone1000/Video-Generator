# Models Setup Guide

This guide covers every model required to run the HunyuanVideo-1.5 pipeline, where to place the files, and how to configure the system to run generation. It also records the full troubleshooting history so no context is lost between sessions.

---

## Current Status (as of 2026-05-22)

| Item | Status |
|---|---|
| Code repo cloned (`generate.py`) | Done ✓ — `E:\models\HunyuanVideo-1.5\src` |
| Windows FileStore patch applied to `generate.py` | Done ✓ |
| `huggingface-hub` version fixed in backend venv | Done ✓ — downgraded to 0.36.2 |
| All model files downloaded | Done ✓ — see checklist below |
| Mock pipeline (runtime: mock) | Working ✓ — verified job completion |
| Real generation (runtime: hunyuan_15) | **Blocked — insufficient virtual memory** |

**What's blocking real generation:** The `480p_t2v` transformer is 33.3 GB (BF16). The system has 16 GB RAM + 10.7 GB pagefile = 26.7 GB total virtual memory, which is 6.6 GB less than the transformer alone. Generating a video requires all models to be in memory simultaneously (~55 GB total). **Fix: increase pagefile.** Two options documented below.

---

## Hardware Profile (this machine)

| Component | Spec |
|---|---|
| RAM | 16 GB |
| GPU | RTX 2060 (6 GB VRAM) |
| C: drive (NTFS) | 458 GB total, 47.7 GB free |
| E: drive (exFAT) | 5 TB, ~1.25 TB free — models stored here |
| Current pagefile | 10.7 GB on C: (system-managed) |
| Current total virtual memory | 26.7 GB (RAM + pagefile) |

### Minimum requirements to run real generation

| Component | Required | Why |
|---|---|---|
| Total virtual memory | ≥ 60 GB | Transformer (33.3 GB) + LLM (15.5 GB) + VAE (4.8 GB) + others = ~55 GB loaded simultaneously |
| GPU VRAM | 6 GB | Group offloading keeps one transformer block on GPU at a time |
| Pagefile (with 16 GB RAM) | ≥ 44 GB | To bring total virtual memory to ≥ 60 GB |

---

## Fix: Increase Virtual Memory (pagefile)

Windows pagefiles **require NTFS**. The E: drive is formatted as **exFAT** and cannot directly host a pagefile. Two options:

---

### Option A — 40 GB pagefile on C: drive (recommended, simplest)

C: has 47.7 GB free. A 40 GB pagefile leaves 7.7 GB free, which Windows handles fine.

Run in **PowerShell as Administrator**, then **reboot**:

```powershell
$cs = Get-CimInstance -ClassName Win32_ComputerSystem
$cs | Invoke-CimMethod -MethodName SetAutomaticManagedPagefile -Arguments @{AutomaticManagedPagefile=$false}
$pf = Get-CimInstance -ClassName Win32_PageFileSetting -Filter "Name='C:\\pagefile.sys'"
if ($pf) {
    $pf | Set-CimInstance -Property @{InitialSize=40960; MaximumSize=40960}
} else {
    New-CimInstance -ClassName Win32_PageFileSetting -Property @{Name='C:\pagefile.sys'; InitialSize=40960; MaximumSize=40960}
}
Write-Host "Pagefile set to 40 GB on C:. Reboot required."
```

After reboot: 16 GB RAM + 40 GB pagefile = **56 GB total virtual memory** — sufficient for the full model stack.

**Trade-off:** C: free space drops from 47.7 GB to ~7.7 GB. If C: fills up later, reduce the pagefile first.

---

### Option B — NTFS VHD on E: drive (no C: space used)

Create a fixed-size NTFS container file (VHD) on E:, mount it as drive `V:`, and place the pagefile there. E: has ~1.25 TB free.

**Step 1 — Create and format the VHD.** Run in **PowerShell as Administrator**:

```powershell
# Create a fixed 48 GB VHD on E: (fixed-size is required for pagefile use)
New-VHD -Path "E:\ntfs_pagefile.vhd" -SizeBytes 48GB -Fixed

# Mount and format as NTFS with drive letter V:
$vhd = Mount-VHD -Path "E:\ntfs_pagefile.vhd" -PassThru
$disk = Get-Disk -Number $vhd.DiskNumber
Initialize-Disk -Number $disk.Number -PartitionStyle MBR -Confirm:$false
New-Partition -DiskNumber $disk.Number -UseMaximumSize -DriveLetter V
Format-Volume -DriveLetter V -FileSystem NTFS -NewFileSystemLabel "PagefileVol" -Confirm:$false
Write-Host "VHD created and mounted as V:"
```

**Step 2 — Set pagefile on V:**

```powershell
$cs = Get-CimInstance -ClassName Win32_ComputerSystem
$cs | Invoke-CimMethod -MethodName SetAutomaticManagedPagefile -Arguments @{AutomaticManagedPagefile=$false}
# Remove any existing C: pagefile if desired (optional — keeping both is fine)
New-CimInstance -ClassName Win32_PageFileSetting -Property @{Name='V:\pagefile.sys'; InitialSize=40960; MaximumSize=40960}
Write-Host "Pagefile configured on V:."
```

**Step 3 — Auto-mount the VHD on every boot** (required — pagefile must exist before Windows login):

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument '-NonInteractive -Command "Mount-VHD -Path ''E:\ntfs_pagefile.vhd''"'
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "MountPagefileVHD" -Action $action -Trigger $trigger `
    -RunLevel Highest -User "SYSTEM"
Write-Host "Auto-mount task registered. Reboot to apply."
```

Then **reboot**. Windows will mount the VHD at startup before pagefile initialization.

**Trade-off:** More moving parts — if the VHD fails to mount at boot, the pagefile won't exist and Windows will fall back to a small default. Suitable if C: is very tight on space.

---

### After applying either option: verify

After rebooting, run this in PowerShell to confirm virtual memory increased:

```powershell
$os = Get-CimInstance Win32_OperatingSystem
$total = [math]::Round($os.TotalVirtualMemorySize / 1MB, 1)
$free  = [math]::Round($os.FreeVirtualMemory / 1MB, 1)
Write-Host "Total virtual memory: $total GB (need ≥ 60 GB)"
Write-Host "Free virtual memory:  $free GB"
Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize | Format-Table
```

Then restart the backend and submit a job with the `hunyuan-480p-fast` preset. First run loads ~55 GB of models from disk — expect **30–90 minutes** on an HDD or slow SSD.

---

## Configuration

Two paths in `offline-video-generator/backend/.env`:

| Variable | Value (this machine) |
|---|---|
| `HUNYUAN_15_REPO_PATH` | `E:\models\HunyuanVideo-1.5\src` |
| `HUNYUAN_15_MODEL_PATH` | `E:\models\HunyuanVideo-1.5\ckpts` |

Current `.env` (already configured):

```env
HUNYUAN_15_REPO_PATH=E:\models\HunyuanVideo-1.5\src
HUNYUAN_15_MODEL_PATH=E:\models\HunyuanVideo-1.5\ckpts
HUNYUAN_15_TORCHRUN_PATH=.venv/Scripts/torchrun.exe
HUNYUAN_15_NPROC_PER_NODE=1
HUNYUAN_15_ENABLE_SR=false
HUNYUAN_15_USE_SAGE_ATTN=false
HUNYUAN_15_ENABLE_CACHE=false
```

---

## Model Checklist (all present as of 2026-05-22)

| Model | Actual size on disk | Status |
|---|---|---|
| `transformer/480p_t2v/diffusion_pytorch_model.safetensors` | 33.3 GB | Done ✓ |
| `transformer/1080p_sr_distilled/diffusion_pytorch_model.safetensors` | 31.7 GB | Done ✓ (SR upscaler — needs 480p_t2v output as input) |
| `vae/diffusion_pytorch_model.safetensors` | 4.8 GB | Done ✓ |
| `scheduler/scheduler_config.json` | <1 KB | Done ✓ |
| `text_encoder/llm/` (Qwen2.5-VL-7B, all 5 shards) | 15.5 GB | Done ✓ |
| `text_encoder/byt5-small/pytorch_model.bin` | 1.1 GB | Done ✓ |
| `text_encoder/Glyph-SDXL-v2/checkpoints/` | ~0.8 GB | Done ✓ |
| `vision_encoder/siglip/image_encoder/model.safetensors` | 0.8 GB | Done ✓ |
| `E:\models\HunyuanVideo-1.5\src\generate.py` (code repo) | — | Done ✓ |

> **Note:** Actual sizes differ from original estimates. The VAE is 4.8 GB (not 400 MB) and the transformer is 33.3 GB (not 9.8 GB). These are the full BF16 weights.

---

## Directory Structure (current state)

```
E:\models\HunyuanVideo-1.5\
│
├── src\                                                ✓ cloned (HUNYUAN_15_REPO_PATH)
│   ├── generate.py                                     ✓ patched (FileStore init)
│   ├── hyvideo\
│   └── ...
│
└── ckpts\                                              ✓ (HUNYUAN_15_MODEL_PATH)
    │
    ├── config.json / LICENSE / NOTICE / README.md
    │
    ├── transformer\
    │   ├── 480p_t2v\
    │   │   ├── config.json                             ✓
    │   │   └── diffusion_pytorch_model.safetensors     ✓ 33.3 GB
    │   ├── 1080p_sr_distilled\
    │   │   ├── config.json                             ✓
    │   │   └── diffusion_pytorch_model.safetensors     ✓ 31.7 GB (SR upscaler)
    │   └── [other variants — config.json only, no weights]
    │
    ├── vae\
    │   ├── config.json                                 ✓
    │   └── diffusion_pytorch_model.safetensors         ✓ 4.8 GB
    │
    ├── scheduler\
    │   └── scheduler_config.json                      ✓
    │
    ├── text_encoder\
    │   ├── llm\                                        ✓ all 5 shards (Qwen2.5-VL-7B)
    │   ├── byt5-small\                                 ✓ pytorch_model.bin present
    │   └── Glyph-SDXL-v2\                             ✓ all checkpoints
    │
    └── vision_encoder\
        └── siglip\                                     ✓ image_encoder + feature_extractor
```

---

## Step-by-Step Setup (for a fresh machine)

### Step 1 — Clone the code repository

The model weights go in `ckpts\` and the code goes in a separate `src\` subfolder (they share the same parent to keep things tidy):

```powershell
git clone https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5.git E:\models\HunyuanVideo-1.5\src
```

If git shows a `post-checkout hook blocked` warning, it is safe to ignore — the files are checked out regardless. If the checkout fails entirely, run:

```powershell
git -C E:\models\HunyuanVideo-1.5\src restore --source=HEAD :/
```

### Step 2 — Apply the Windows compatibility patch to `generate.py`

`generate.py` calls `torch.distributed.init_process_group` at module level. On Windows, PyTorch 2.6 does not have `HashStore`; use `FileStore` instead. Insert the following block in `generate.py` **between the last import line and the `parallel_dims = initialize_parallel_state(...)` call** (around line 38):

```python
# Windows fix: initialize process group with FileStore to avoid libuv/TCPStore dependency.
if not dist.is_initialized():
    import tempfile as _tempfile
    import pathlib as _pathlib
    _store_path = str(_pathlib.Path(_tempfile.gettempdir()) / "hyvideo_dist.store")
    _store = dist.FileStore(_store_path, int(os.environ.get("WORLD_SIZE", "1")))
    dist.init_process_group(
        backend="gloo",
        store=_store,
        rank=int(os.environ.get("RANK", "0")),
        world_size=int(os.environ.get("WORLD_SIZE", "1")),
    )
```

**This patch is already applied** to `E:\models\HunyuanVideo-1.5\src\generate.py`. If you re-clone, re-apply it.

Without this patch, all generation jobs fail with:
```
RuntimeError: use_libuv was requested but PyTorch was built without libuv support
```

### Step 3 — Download model checkpoints

All checkpoints go in `HUNYUAN_15_MODEL_PATH` (`ckpts\`). All files are already present on this machine. For a fresh machine, run from within `ckpts\`:

```powershell
# Install HuggingFace CLI (use a version <1.0 for compatibility with transformers 4.57)
pip install "huggingface-hub[cli]>=0.34.0,<1.0"

# Transformer (480p T2V) + VAE + scheduler
hf download tencent/HunyuanVideo-1.5 `
  --include "transformer/480p_t2v/**" "vae/**" "scheduler/**" `
  --local-dir .

# LLM text encoder
hf download Qwen/Qwen2.5-VL-7B-Instruct --local-dir ./text_encoder/llm

# byt5-small
hf download google/byt5-small --local-dir ./text_encoder/byt5-small

# SigLIP vision encoder (requires HuggingFace account with access to FLUX.1-Redux-dev)
hf download black-forest-labs/FLUX.1-Redux-dev `
  --include "image_encoder/**" "feature_extractor/**" `
  --local-dir ./vision_encoder/siglip `
  --token YOUR_HF_TOKEN_HERE
```

### Step 4 — Fix the huggingface-hub version in the backend venv

The HunyuanVideo-1.5 `requirements.txt` has two conflicting entries that cause `huggingface-hub` to be upgraded to v1.x. `transformers==4.57.1` rejects v1.x with an `ImportError`. Fix:

```powershell
& "offline-video-generator\backend\.venv\Scripts\pip.exe" install "huggingface-hub>=0.34.0,<1.0"
```

**This fix is already applied** on this machine (currently `0.36.2`). Re-apply after any `pip install -r requirements.txt`.

### Step 5 — Increase virtual memory (pagefile)

See the **Fix: Increase Virtual Memory** section above. Choose Option A or Option B, then reboot.

### Step 6 — Start the app and submit a job

```powershell
# Backend
cd offline-video-generator\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (separate terminal)
cd offline-video-generator\frontend
npm run dev
```

Open `http://localhost:5173`, select the **`hunyuan-480p-fast`** preset, enter a prompt, and click Generate.

---

## Troubleshooting Log

All errors encountered and their fixes, in order.

---

### Error: `use_libuv was requested but PyTorch was built without libuv support`

**Cause:** The old adapter called `torchrun.exe` which uses TCPStore (requires libuv). PyTorch 2.6 Windows builds do not include libuv.

**Fix (already applied):**
- `hunyuan_15_adapter.py` now calls `python.exe generate.py` directly (not torchrun).
- `generate.py` initializes `dist.init_process_group` with `FileStore` before `initialize_parallel_state` is called.

---

### Error: `module 'torch.distributed' has no attribute 'HashStore'`

**Cause:** The original Windows patch used `dist.HashStore()` which does not exist in PyTorch 2.6. Only `FileStore` and `TCPStore` are available.

**Fix (already applied):** Replaced `dist.HashStore()` with `dist.FileStore(path, world_size)` in the `generate.py` patch. See Step 2 above for the correct patch text.

---

### Error: `ImportError: huggingface-hub>=0.34.0,<1.0 is required ... found huggingface-hub==1.16.0`

**Cause:** The HunyuanVideo-1.5 `requirements.txt` contains two conflicting entries:
```
huggingface-hub==0.34.0
huggingface_hub[cli]          ← no pin — pip upgrades to latest (1.16.0)
```
When both are processed, pip ends up installing the latest v1.x which `transformers==4.57.1` rejects.

**Fix (already applied):** `pip install "huggingface-hub>=0.34.0,<1.0"` in the backend venv. Currently at `0.36.2`.

---

### Error: `git clone` — `fatal: active post-checkout hook found`

**Cause:** The HunyuanVideo-1.5 repo has a post-checkout hook. Git 2.x blocks it by default for security.

**Effect:** Clone succeeds; only the checkout step is skipped. All files are present despite the error message.

**Fix:** If files are missing, run:
```powershell
git config --global --add safe.directory E:/models/HunyuanVideo-1.5/src
git -C E:\models\HunyuanVideo-1.5\src restore --source=HEAD :/
```

---

### Error: Windows fatal exception — access violation during transformer loading

**Cause:** The `480p_t2v` transformer is 33.3 GB. With `low_cpu_mem_usage=True`, diffusers loads all parameters into CPU RAM incrementally. When physical RAM fills (16 GB), Windows pages to pagefile. With only 10.7 GB pagefile, total virtual memory = 26.7 GB, which is less than the transformer alone (33.3 GB). Windows raises `STATUS_ACCESS_VIOLATION` (Python exit code `3221225477`) inside `safetensors.torch.load_file → torch.storage.__getitem__`.

**Full traceback:**
```
Windows fatal exception: access violation
  torch.storage.__getitem__
  safetensors.torch.load_file
  diffusers.models.model_loading_utils.load_state_dict
  diffusers.models.modeling_utils.from_pretrained
  hyvideo.pipelines.hunyuan_video_pipeline.create_pipeline (line 1507)
  generate.py line 195 (generate_video → main)
Exit code: 3221225477
```

**Additional notes:**
- exFAT (the E: drive filesystem) was investigated as a possible cause. It is NOT the cause — Python `mmap` works fine on exFAT, including full-file mapping of 33+ GB files.
- `low_cpu_mem_usage=True` is already set in the pipeline but does not help: it reduces peak RAM by loading one tensor at a time, but the total CPU RAM occupied after loading is still the full 33.3 GB.
- All other transformer variants (`480p_t2v_distilled`, `480p_t2v_step_distilled`) have the same architecture and the same file size (~33 GB). There is no smaller variant to switch to — distillation affects inference steps, not parameter count.
- The 1080p_sr_distilled transformer (also 31.7 GB) is an SR upscaler that takes a 480p video as input and upscales it; it cannot generate video independently.

**Fix:** Increase pagefile to bring total virtual memory to ≥ 60 GB. See Options A and B above.

**Expected performance after fix:** Loading ~55 GB of models from a USB/external HDD will take 30–90 minutes on first run. Subsequent runs are faster if models stay in RAM between jobs. Disk read speed on E: is approximately 80 MB/s (measured).

---

## Pipeline Architecture Summary

```
generate.py (subprocess)
    ↓
HunyuanVideo_1_5_Pipeline.create_pipeline()
    ├─ Transformer  (480p_t2v, 33.3 GB) → CPU RAM, then blocks move to GPU one at a time
    ├─ VAE          (4.8 GB)             → GPU (6 GB VRAM, just fits with group offloading)
    ├─ LLM          (15.5 GB)            → CPU RAM / GPU (text encoding, then unloaded)
    ├─ byt5-small   (1.1 GB)             → CPU/GPU
    └─ SigLIP       (0.8 GB)             → CPU/GPU
```

Group offloading (`--group_offloading true`, passed automatically when `use_cpu_offload=True`) ensures only one transformer block is on the GPU at any time, keeping VRAM usage within the RTX 2060's 6 GB limit. The trade-off is slower inference due to repeated CPU↔GPU transfers.

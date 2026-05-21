# Native Windows Installation Guide: Offline Video Generator + HunyuanVideo-1.5

This guide is for your Windows machine with an NVIDIA GPU. Your Mac can remain the development/mock-mode machine; this Windows setup is for real HunyuanVideo-1.5 generation.

Everything app-related lives inside the cloned project root:

```text
<PROJECT_ROOT>\
  README.md
  installation.md
  models\
    HunyuanVideo-1.5\
      generate.py
      requirements.txt
      ckpts\
  offline-video-generator\
    backend\
      .venv\
      .env
    frontend\
```

Important caveat: the official HunyuanVideo-1.5 documentation targets Linux/CUDA. Native Windows is an experimental setup path. The base Python/PyTorch stack may work, but optional CUDA extensions such as SageAttention, flex-block attention, Flash Attention, or sparse-attention paths may be harder or unsupported on native Windows. If native Windows hits a CUDA extension or distributed runtime wall, use WSL2/Linux as the fallback.

Official references:

- [HunyuanVideo-1.5 repo](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5)
- [HunyuanVideo-1.5 checkpoint download guide](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/checkpoints-download.md)
- [PyTorch local install selector](https://pytorch.org/get-started/locally/)

## 1. Windows Prerequisites

Open PowerShell as Administrator and install the core tools:

```powershell
winget install --id Git.Git -e
winget install --id GitHub.GitLFS -e
winget install --id Python.Python.3.10 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Gyan.FFmpeg -e
winget install --id Microsoft.VisualStudio.2022.BuildTools -e
```

During Visual Studio Build Tools installation, include:

```text
Desktop development with C++
MSVC v143 toolset
Windows 10/11 SDK
C++ CMake tools for Windows
```

Install or update your NVIDIA driver from NVIDIA. Use the latest Game Ready, Studio, or RTX driver for your GPU.

Restart Windows after installing drivers and tools.

## 2. PowerShell Setup

Open a new normal PowerShell window.

Allow local virtual-environment activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Enable long paths for Git:

```powershell
git config --global core.longpaths true
git lfs install
```

Verify tools:

```powershell
python --version
git --version
git lfs version
node --version
npm --version
ffmpeg -version
ffprobe -version
nvidia-smi
```

If `nvidia-smi` fails, fix the NVIDIA driver before continuing.

## 3. Clone or Copy This App

Clone into any parent folder you like:

```powershell
cd <PARENT_FOLDER_FOR_PROJECTS>
git clone <YOUR_VIDEO_GENERATOR_REPO_URL> Video-Generator
cd .\Video-Generator
```

If you are copying from the Mac, copy the full `Video-Generator` folder anywhere you like, then `cd` into that copied folder.

From the project root, define reusable PowerShell variables:

```powershell
$PROJECT_ROOT = (Get-Location).Path
$APP_ROOT = Join-Path $PROJECT_ROOT "offline-video-generator"
$BACKEND_ROOT = Join-Path $APP_ROOT "backend"
$FRONTEND_ROOT = Join-Path $APP_ROOT "frontend"
$MODELS_ROOT = Join-Path $PROJECT_ROOT "models"
$HUNYUAN_ROOT = Join-Path $MODELS_ROOT "HunyuanVideo-1.5"

Write-Host "PROJECT_ROOT = $PROJECT_ROOT"
```

Expected file:

```powershell
Test-Path (Join-Path $APP_ROOT "README.md")
```

This should print `True`.

## 4. Create the Python Environment

Use one Python environment for both the app backend and HunyuanVideo-1.5 so the backend can find `torchrun.exe`.

```powershell
cd $BACKEND_ROOT
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel setuptools
```

Install CUDA-enabled PyTorch. Start with the command from the current [PyTorch install selector](https://pytorch.org/get-started/locally/). A commonly compatible HunyuanVideo-1.5 baseline is PyTorch 2.6 with CUDA 12.4:

```powershell
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
```

Verify CUDA:

```powershell
python -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

`cuda: True` is required before continuing.

Install the app backend:

```powershell
cd $BACKEND_ROOT
pip install -e ".[dev]"
```

## 5. Clone HunyuanVideo-1.5 Inside the Project

```powershell
mkdir $MODELS_ROOT -Force
cd $MODELS_ROOT
git clone https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5.git
cd $HUNYUAN_ROOT
```

Install HunyuanVideo-1.5 dependencies into the same backend venv:

```powershell
& (Join-Path $BACKEND_ROOT ".venv\Scripts\Activate.ps1")
cd $HUNYUAN_ROOT
pip install -r requirements.txt
pip install -i https://mirrors.tencent.com/pypi/simple/ --upgrade tencentcloud-sdk-python
```

If `pip install -r requirements.txt` replaces your CUDA PyTorch build with an unwanted CPU build, reinstall the CUDA PyTorch command from step 4 afterward and verify `torch.cuda.is_available()` again.

## 6. Optional Native Windows Speed Libraries

Skip this section for the first successful run. Get the base 480p generation working first.

FP8 GEMM:

```powershell
pip install sgl-kernel==0.3.18
```

SageAttention and flex-block attention may require CUDA Toolkit, Visual Studio Build Tools, and source compilation. They may fail on native Windows. Leave these disabled in `.env` unless you have verified them independently:

```text
HUNYUAN_15_USE_SAGE_ATTN=false
HUNYUAN_15_ENABLE_CACHE=false
```

## 7. Download HunyuanVideo-1.5 Models

Activate the backend venv:

```powershell
& (Join-Path $BACKEND_ROOT ".venv\Scripts\Activate.ps1")
```

Install download CLIs:

```powershell
pip install -U "huggingface_hub[cli]" modelscope
```

Optional but recommended:

```powershell
huggingface-cli login
```

Download main checkpoints:

```powershell
cd $HUNYUAN_ROOT
hf download tencent/HunyuanVideo-1.5 --local-dir .\ckpts
```

Download text encoders:

```powershell
hf download Qwen/Qwen2.5-VL-7B-Instruct --local-dir .\ckpts\text_encoder\llm
hf download google/byt5-small --local-dir .\ckpts\text_encoder\byt5-small
modelscope download --model AI-ModelScope/Glyph-SDXL-v2 --local_dir .\ckpts\text_encoder\Glyph-SDXL-v2
```

For text-to-video, this is the main set. For image-to-video later, you may also need the gated FLUX.1-Redux-dev vision encoder after requesting access on Hugging Face:

```powershell
hf download black-forest-labs/FLUX.1-Redux-dev `
  --local-dir .\ckpts\vision_encoder\siglip `
  --token <YOUR_HUGGING_FACE_TOKEN>
```

If a download is interrupted, rerun the same command. Hugging Face downloads can resume.

## 8. Direct Hunyuan Smoke Test

Before using the app, test Hunyuan directly.

```powershell
& (Join-Path $BACKEND_ROOT ".venv\Scripts\Activate.ps1")
cd $HUNYUAN_ROOT
mkdir outputs -Force

$env:PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,max_split_size_mb:128"

torchrun --nproc_per_node=1 generate.py `
  --prompt "a cinematic shot of a small robot watering flowers at sunrise" `
  --image_path none `
  --resolution 480p `
  --aspect_ratio 16:9 `
  --seed 1 `
  --rewrite false `
  --offloading true `
  --group_offloading true `
  --overlap_group_offloading false `
  --sr false `
  --output_path .\outputs\smoke_test.mp4 `
  --model_path .\ckpts
```

Verify the MP4:

```powershell
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,duration -of json .\outputs\smoke_test.mp4
```

If direct Hunyuan generation fails, fix that before using the app. Common native Windows failure points are CUDA/PyTorch mismatch, missing model files, optional CUDA extension imports, or PyTorch distributed/runtime behavior.

## 9. Configure the App Backend

Create the env file:

```powershell
cd $BACKEND_ROOT
copy ..\.env.example .env
```

Edit `offline-video-generator\backend\.env`.

Use relative paths from the backend directory so the project folder can be moved later:

```text
APP_ENV=local
APP_HOST=127.0.0.1
APP_PORT=8000

DATABASE_URL=sqlite:///./data/app.db
OUTPUT_DIR=./data/outputs
THUMBNAIL_DIR=./data/thumbnails
LOG_DIR=./data/logs

VIDEO_RUNTIME=hunyuan_15

HUNYUAN_15_REPO_PATH=../../models/HunyuanVideo-1.5
HUNYUAN_15_MODEL_PATH=../../models/HunyuanVideo-1.5/ckpts
HUNYUAN_15_TORCHRUN_PATH=.venv/Scripts/torchrun.exe
HUNYUAN_15_NPROC_PER_NODE=1
HUNYUAN_15_ENABLE_SR=false
HUNYUAN_15_USE_SAGE_ATTN=false
HUNYUAN_15_ENABLE_CACHE=false

FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe

MAX_ACTIVE_JOBS=1
DEFAULT_PRESET=standard
```

Keep prompt rewriting disabled in the UI. HunyuanVideo-1.5 supports rewriting, but you should only enable it after setting up a local vLLM-compatible rewrite server.

## 10. Install and Build the Frontend

```powershell
cd $FRONTEND_ROOT
npm install
npm run build
```

## 11. Run the Backend

Open PowerShell terminal 1, `cd` into the project root again, and redefine the variables:

```powershell
$PROJECT_ROOT = (Get-Location).Path
$BACKEND_ROOT = Join-Path $PROJECT_ROOT "offline-video-generator\backend"
cd $BACKEND_ROOT
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000/api/system/status
```

You should see JSON with `"status": "ok"`.

## 12. Run the Frontend

Open PowerShell terminal 2, `cd` into the project root again, and run:

```powershell
$PROJECT_ROOT = (Get-Location).Path
$FRONTEND_ROOT = Join-Path $PROJECT_ROOT "offline-video-generator\frontend"
cd $FRONTEND_ROOT
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

## 13. First App Generation Settings

Use conservative settings:

```text
Runtime: hunyuan 1.5
Resolution: 480p
Aspect ratio: 16:9
Frames / video_length: 121
Steps: 50
CPU offload: on
FP8: off
Prompt rewrite: off
Super resolution: off
SageAttention/cache/sparse attention: off
```

After one successful generation:

```text
Try 720p only if VRAM allows.
Enable FP8 only after sgl-kernel is verified.
Enable SR only after base generation is stable.
Enable one optimization at a time.
```

## 14. Validation Commands

Backend API:

```powershell
curl http://127.0.0.1:8000/api/system/status
curl http://127.0.0.1:8000/api/jobs
curl http://127.0.0.1:8000/api/assets
```

Backend tests:

```powershell
cd $BACKEND_ROOT
.\.venv\Scripts\Activate.ps1
pytest
```

Frontend build:

```powershell
cd $FRONTEND_ROOT
npm run build
```

Find generated app videos:

```powershell
Get-ChildItem (Join-Path $BACKEND_ROOT "data\outputs") -Recurse -Filter *.mp4
```

## 15. Troubleshooting

`nvidia-smi` fails:

- Update/reinstall the Windows NVIDIA driver.
- Restart Windows.
- Confirm your GPU supports CUDA.

`torch.cuda.is_available()` is false:

- Reinstall CUDA-enabled PyTorch.
- Confirm the backend `.venv` is active.
- Confirm `nvidia-smi` works in the same PowerShell session.

`torchrun.exe` missing:

- Activate `offline-video-generator\backend\.venv`.
- Install PyTorch.
- Confirm:

```powershell
where torchrun
```

Hunyuan model path errors:

- Confirm `models\HunyuanVideo-1.5\ckpts` exists under the project root.
- Confirm the text encoders exist under `models\HunyuanVideo-1.5\ckpts\text_encoder`.
- Keep `.env` paths relative to `offline-video-generator\backend`.

Out of memory:

- Start with `480p`.
- Keep CPU offload on.
- Keep SR off.
- Use `--overlap_group_offloading false` in direct Hunyuan tests.
- Try fewer frames or steps.
- Close other GPU apps.

Prompt rewrite errors:

- Keep rewrite disabled.
- In the app, leave `rewrite_prompt=false`.
- In direct Hunyuan commands, pass `--rewrite false`.

Native Windows CUDA extension failure:

- Disable optional accelerators first: SageAttention, flex-block attention, sparse attention, cache, FP8.
- Get the plain 480p path working before adding speed libraries.
- If the base path still fails due to upstream Linux assumptions, switch to WSL2/Linux for the runtime machine.

No app MP4 appears:

- Check:

```text
offline-video-generator\backend\data\outputs\YYYY-MM-DD\job_<id>\logs.txt
```

- Run the direct Hunyuan smoke test outside the app.
- Confirm `ffmpeg` and `ffprobe` work.

## 16. Prompt for Another LLM or Coding Agent

Use this prompt if you want another LLM to perform the native Windows setup:

```text
You are setting up a native Windows local text-to-video app using HunyuanVideo-1.5 on a Windows machine with an NVIDIA GPU.

Follow installation.md exactly. Use native PowerShell, not WSL. Keep everything inside the cloned project root. Install Git, Git LFS, Python 3.10, Node LTS, ffmpeg, Visual Studio Build Tools, and the NVIDIA driver. Clone or copy the app, cd into the project root, define PROJECT_ROOT/APP_ROOT/BACKEND_ROOT/FRONTEND_ROOT/MODELS_ROOT/HUNYUAN_ROOT variables as shown, create the backend venv at offline-video-generator\backend\.venv, install CUDA-enabled PyTorch, verify torch.cuda.is_available() is true, install the app backend, clone Tencent-Hunyuan/HunyuanVideo-1.5 into models\HunyuanVideo-1.5 under the project root, install Hunyuan requirements into the same backend venv, download all required checkpoints into models\HunyuanVideo-1.5\ckpts, run the direct torchrun smoke test with --rewrite false and --sr false, configure backend\.env for VIDEO_RUNTIME=hunyuan_15 using relative paths, then run backend and frontend.

Stop and report the exact command output if nvidia-smi, torch.cuda.is_available(), checkpoint download, direct Hunyuan generation, backend startup, or frontend startup fails.
```

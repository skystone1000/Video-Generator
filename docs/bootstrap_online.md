# Online Bootstrap

Use this mode once on a connected Windows machine to prepare everything needed for offline use.

## Steps

1. Clone this application repository:

   ```powershell
   git clone <YOUR_VIDEO_GENERATOR_REPO_URL> Video-Generator
   cd Video-Generator
   ```

2. Create the backend virtual environment and download wheels:

   ```powershell
   cd offline-video-generator\backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip download -d ..\..\wheelhouse -e ".[dev]"
   ```

3. Install frontend packages and build the static frontend:

   ```powershell
   cd ..\frontend
   npm install
   npm run build
   ```

4. Clone the HunyuanVideo-1.5 source repository to your chosen external location:

   ```powershell
   git clone https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5.git E:\models\HunyuanVideo-1.5
   ```

   Apply the Windows HashStore patch to `generate.py` — see [installation.md](installation.md) step 5 for the exact code block.

5. Download model weights into your `ckpts\` folder. See [models_setup.md](models_setup.md) for the full list, download commands, and expected directory structure. Do not rely on runtime auto-downloads.

6. Install or verify `ffmpeg` and `ffprobe` are on PATH:

   ```powershell
   winget install --id Gyan.FFmpeg -e
   ffmpeg -version
   ```

7. Generate checksums for portability verification:

   ```powershell
   Get-ChildItem -Recurse offline-video-generator | Get-FileHash | Export-Csv checksums.csv
   ```

8. Copy the prepared folders to the offline machine.

Normal runtime must not call hosted APIs or download model weights.

# Online Bootstrap

Use this mode once on a connected machine to prepare everything needed for offline use.

1. Clone this application repository.
2. Create the backend virtual environment and download wheels:

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip download -d ../wheelhouse -e ".[dev]"
   ```

3. Install frontend packages and preserve a local package cache or build the static frontend:

   ```bash
   cd frontend
   npm install
   npm run build
   ```

4. Clone the HunyuanVideo source repositories you plan to use:

   ```bash
   git clone https://github.com/Tencent-Hunyuan/HunyuanVideo /models/HunyuanVideo
   git clone https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5 /models/HunyuanVideo-1.5
   ```

5. Download model weights into local folders. Do not rely on runtime auto-downloads.
6. Install or package `ffmpeg` and `ffprobe`.
7. Generate checksums for app code, wheels, npm cache or frontend build, model repos, weights, and ffmpeg binaries.
8. Copy the prepared folders to the offline machine.

Normal runtime should not call hosted APIs or download model weights.

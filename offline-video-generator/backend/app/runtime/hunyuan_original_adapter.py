import os
import re
import subprocess
import sys
from pathlib import Path

from ..config import get_settings
from .base import GenerationResult, ProgressCallback, VideoGenerationAdapter

_STEP_RE = re.compile(r"\b(\d+)/(\d+)\b")


class HunyuanOriginalAdapter(VideoGenerationAdapter):
    name = "hunyuan_original"
    model_version = "Tencent-Hunyuan/HunyuanVideo"

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None

    def cancel(self) -> None:
        proc = self._proc
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def validate(self) -> None:
        settings = get_settings()
        repo_path = settings.resolve_path(settings.hunyuan_original_repo_path)
        ckpt_path = settings.resolve_path(settings.hunyuan_original_ckpt_path)
        if repo_path is None or not repo_path.exists():
            raise RuntimeError(f"HunyuanVideo repo path is missing: {repo_path}")
        if ckpt_path is None or not ckpt_path.exists():
            raise RuntimeError(f"HunyuanVideo checkpoint path is missing: {ckpt_path}")
        script_path = repo_path / "sample_video.py"
        if not script_path.exists():
            raise RuntimeError(f"HunyuanVideo sample script is missing: {script_path}")

    def load(self) -> None:
        self.validate()

    def build_command(self, request, output_dir: Path) -> list[str]:
        settings = get_settings()
        repo_path = settings.resolve_path(settings.hunyuan_original_repo_path)
        ckpt_path = settings.resolve_path(settings.hunyuan_original_ckpt_path)
        assert repo_path is not None
        assert ckpt_path is not None

        command = [
            sys.executable,
            str(repo_path / "sample_video.py"),
            "--video-size",
            str(request.height),
            str(request.width),
            "--video-length",
            str(request.video_length),
            "--infer-steps",
            str(request.steps),
            "--prompt",
            request.prompt,
            "--flow-shift",
            str(request.flow_shift),
            "--save-path",
            str(output_dir),
            "--ckpt-path",
            str(ckpt_path),
        ]
        if request.use_cpu_offload:
            command.append("--use-cpu-offload")
        if request.use_fp8:
            command.append("--use-fp8")
        return command

    def generate(self, request, output_dir: str | Path, progress: ProgressCallback) -> GenerationResult:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        logs_path = output_path / "logs.txt"
        command = self.build_command(request, output_path)
        progress(0.05, "generating", "starting HunyuanVideo subprocess")

        env = {**os.environ, "USE_LIBUV": "0"}
        last_progress = 0.05
        with logs_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(get_settings().resolve_path(get_settings().hunyuan_original_repo_path)),
                env=env,
            )
            assert process.stdout is not None
            self._proc = process
            try:
                for line in process.stdout:
                    log_file.write(line)
                    log_file.flush()
                    m = _STEP_RE.search(line)
                    if m:
                        current, total = int(m.group(1)), int(m.group(2))
                        if total > 0 and 0 <= current <= total:
                            last_progress = 0.05 + 0.90 * (current / total)
                            progress(last_progress, "generating", f"Step {current}/{total}")
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait()
                self._proc = None

        return_code = process.returncode
        if return_code != 0:
            progress(last_progress, "generating")
            raise RuntimeError(f"HunyuanVideo exited with code {return_code}. See {logs_path}.")

        candidates = sorted(output_path.glob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            raise RuntimeError(f"HunyuanVideo completed but no MP4 was found in {output_path}.")

        progress(1.0, "postprocessing", "HunyuanVideo output discovered")
        return GenerationResult(video_path=candidates[0], logs_path=logs_path, model_version=self.model_version)

    def unload(self) -> None:
        return None

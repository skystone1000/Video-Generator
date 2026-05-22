import os
import re
import subprocess
from pathlib import Path
import shutil

from ..config import get_settings
from .base import GenerationResult, ProgressCallback, VideoGenerationAdapter

_STEP_RE = re.compile(r"\b(\d+)/(\d+)\b")


class Hunyuan15Adapter(VideoGenerationAdapter):
    name = "hunyuan_15"
    model_version = "Tencent-Hunyuan/HunyuanVideo-1.5"

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

    def _resolve_executable(self, raw_path: str) -> str:
        if "/" in raw_path or "\\" in raw_path or raw_path.startswith("."):
            resolved = get_settings().resolve_path(raw_path)
            return str(resolved) if resolved is not None else raw_path
        return raw_path

    def _python_from_torchrun(self, torchrun_path: str) -> str:
        p = Path(torchrun_path)
        python = p.parent / ("python.exe" if p.suffix == ".exe" else "python")
        return str(python)

    def validate(self) -> None:
        settings = get_settings()
        repo_path = settings.resolve_path(settings.hunyuan_15_repo_path)
        model_path = settings.resolve_path(settings.hunyuan_15_model_path)
        if repo_path is None or not repo_path.exists():
            raise RuntimeError(f"HunyuanVideo-1.5 repo path is missing: {repo_path}")
        if model_path is None or not model_path.exists():
            raise RuntimeError(f"HunyuanVideo-1.5 model path is missing: {model_path}")
        script_path = repo_path / "generate.py"
        if not script_path.exists():
            raise RuntimeError(
                f"HunyuanVideo-1.5 generate script is missing: {script_path}. "
                "Update Hunyuan15Adapter.build_command if the upstream entrypoint has changed."
            )
        torchrun_path = self._resolve_executable(settings.hunyuan_15_torchrun_path)
        python_path = self._python_from_torchrun(torchrun_path)
        if shutil.which(python_path) is None and not Path(python_path).exists():
            raise RuntimeError(
                f"HunyuanVideo-1.5 python executable is missing: {python_path}. "
                "Install PyTorch in the runtime environment or set HUNYUAN_15_TORCHRUN_PATH."
            )

    def load(self) -> None:
        self.validate()

    def build_command(self, request, output_dir: Path) -> list[str]:
        settings = get_settings()
        repo_path = settings.resolve_path(settings.hunyuan_15_repo_path)
        model_path = settings.resolve_path(settings.hunyuan_15_model_path)
        assert repo_path is not None
        assert model_path is not None

        torchrun_path = self._resolve_executable(settings.hunyuan_15_torchrun_path)
        python_path = self._python_from_torchrun(torchrun_path)

        command = [
            python_path,
            str(repo_path / "generate.py"),
            "--prompt",
            request.prompt,
            "--negative_prompt",
            request.negative_prompt,
            "--resolution",
            request.resolution,
            "--model_path",
            str(model_path),
            "--aspect_ratio",
            request.aspect_ratio,
            "--num_inference_steps",
            str(request.steps),
            "--video_length",
            str(request.video_length),
            "--seed",
            str(request.seed),
            "--image_path",
            "none",
            "--output_path",
            str(output_dir / "output.mp4"),
            "--rewrite",
            "true" if request.rewrite_prompt else "false",
            "--offloading",
            "true" if request.use_cpu_offload else "false",
            "--sr",
            "true" if settings.hunyuan_15_enable_sr else "false",
            "--use_sageattn",
            "true" if settings.hunyuan_15_use_sage_attn else "false",
            "--enable_cache",
            "true" if settings.hunyuan_15_enable_cache else "false",
        ]
        if request.use_cpu_offload:
            command.extend(["--group_offloading", "true"])
        if request.use_fp8:
            command.extend(["--use_fp8_gemm", "true"])
        return command

    def generate(self, request, output_dir: str | Path, progress: ProgressCallback) -> GenerationResult:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        logs_path = output_path / "logs.txt"
        command = self.build_command(request, output_path)
        progress(0.05, "generating", "starting HunyuanVideo-1.5 subprocess")

        env = {**os.environ, "USE_LIBUV": "0"}
        last_progress = 0.05
        with logs_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(get_settings().resolve_path(get_settings().hunyuan_15_repo_path)),
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
            # Raises CancellationRequested if user cancelled; otherwise raises RuntimeError
            progress(last_progress, "generating")
            raise RuntimeError(f"HunyuanVideo-1.5 exited with code {return_code}. See {logs_path}.")

        candidates = sorted(output_path.glob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            raise RuntimeError(f"HunyuanVideo-1.5 completed but no MP4 was found in {output_path}.")

        progress(1.0, "postprocessing", "HunyuanVideo-1.5 output discovered")
        return GenerationResult(video_path=candidates[0], logs_path=logs_path, model_version=self.model_version)

    def unload(self) -> None:
        return None

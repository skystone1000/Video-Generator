import subprocess
from pathlib import Path

from ..config import get_settings
from .base import GenerationResult, ProgressCallback, VideoGenerationAdapter


class HunyuanOriginalAdapter(VideoGenerationAdapter):
    name = "hunyuan_original"
    model_version = "Tencent-Hunyuan/HunyuanVideo"

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
            "python3",
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

        with logs_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(get_settings().resolve_path(get_settings().hunyuan_original_repo_path)),
            )
            assert process.stdout is not None
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()
            return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(f"HunyuanVideo exited with code {return_code}. See {logs_path}.")

        candidates = sorted(output_path.glob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            raise RuntimeError(f"HunyuanVideo completed but no MP4 was found in {output_path}.")

        progress(1.0, "postprocessing", "HunyuanVideo output discovered")
        return GenerationResult(video_path=candidates[0], logs_path=logs_path, model_version=self.model_version)

    def unload(self) -> None:
        return None

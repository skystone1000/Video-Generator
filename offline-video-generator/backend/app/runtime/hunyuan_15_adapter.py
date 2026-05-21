import subprocess
from pathlib import Path

from ..config import get_settings
from .base import GenerationResult, ProgressCallback, VideoGenerationAdapter


class Hunyuan15Adapter(VideoGenerationAdapter):
    name = "hunyuan_15"
    model_version = "Tencent-Hunyuan/HunyuanVideo-1.5"

    def validate(self) -> None:
        settings = get_settings()
        repo_path = settings.resolve_path(settings.hunyuan_15_repo_path)
        model_path = settings.resolve_path(settings.hunyuan_15_model_path)
        if repo_path is None or not repo_path.exists():
            raise RuntimeError(f"HunyuanVideo-1.5 repo path is missing: {repo_path}")
        if model_path is None or not model_path.exists():
            raise RuntimeError(f"HunyuanVideo-1.5 model path is missing: {model_path}")
        script_path = repo_path / "sample_video.py"
        if not script_path.exists():
            raise RuntimeError(
                f"HunyuanVideo-1.5 sample script is missing: {script_path}. "
                "Update Hunyuan15Adapter.build_command if the upstream entrypoint has changed."
            )

    def load(self) -> None:
        self.validate()

    def build_command(self, request, output_dir: Path) -> list[str]:
        settings = get_settings()
        repo_path = settings.resolve_path(settings.hunyuan_15_repo_path)
        model_path = settings.resolve_path(settings.hunyuan_15_model_path)
        assert repo_path is not None
        assert model_path is not None

        command = [
            "python3",
            str(repo_path / "sample_video.py"),
            "--model-path",
            str(model_path),
            "--prompt",
            request.prompt,
            "--negative-prompt",
            request.negative_prompt,
            "--resolution",
            request.resolution,
            "--video-size",
            str(request.height),
            str(request.width),
            "--video-length",
            str(request.video_length),
            "--infer-steps",
            str(request.steps),
            "--seed",
            str(request.seed),
            "--save-path",
            str(output_dir),
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
        progress(0.05, "generating", "starting HunyuanVideo-1.5 subprocess")

        with logs_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(get_settings().resolve_path(get_settings().hunyuan_15_repo_path)),
            )
            assert process.stdout is not None
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()
            return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(f"HunyuanVideo-1.5 exited with code {return_code}. See {logs_path}.")

        candidates = sorted(output_path.glob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            raise RuntimeError(f"HunyuanVideo-1.5 completed but no MP4 was found in {output_path}.")

        progress(1.0, "postprocessing", "HunyuanVideo-1.5 output discovered")
        return GenerationResult(video_path=candidates[0], logs_path=logs_path, model_version=self.model_version)

    def unload(self) -> None:
        return None

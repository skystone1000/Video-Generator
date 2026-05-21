import shutil
import subprocess
import time
from pathlib import Path

from ..config import get_settings
from ..services.storage import write_metadata
from .base import GenerationResult, ProgressCallback, VideoGenerationAdapter


class MockVideoAdapter(VideoGenerationAdapter):
    name = "mock"
    model_version = "mock-ffmpeg-or-sample"

    def validate(self) -> None:
        settings = get_settings()
        sample_path = settings.resolve_path(settings.mock_sample_mp4_path)
        has_sample = sample_path is not None and sample_path.exists()
        has_ffmpeg = shutil.which(settings.ffmpeg_path) is not None or Path(settings.ffmpeg_path).exists()
        if not has_sample and not has_ffmpeg:
            raise RuntimeError(
                "Mock runtime needs ffmpeg or MOCK_SAMPLE_MP4_PATH. "
                "Install ffmpeg, set FFMPEG_PATH, or point MOCK_SAMPLE_MP4_PATH at a local MP4."
            )

    def load(self) -> None:
        return None

    def generate(self, request, output_dir: str | Path, progress: ProgressCallback) -> GenerationResult:
        settings = get_settings()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        video_path = output_path / "output.mp4"

        for step in range(1, 6):
            time.sleep(0.15)
            progress(step * 0.12, "generating", "mock progress")

        sample_path = settings.resolve_path(settings.mock_sample_mp4_path)
        if sample_path is not None and sample_path.exists():
            shutil.copy2(sample_path, video_path)
        else:
            duration = max(1, round(request.video_length / request.fps))
            command = [
                settings.ffmpeg_path,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"testsrc2=size={request.width}x{request.height}:rate={request.fps}:duration={duration}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(video_path),
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            logs_path = output_path / "logs.txt"
            logs_path.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
            if result.returncode != 0 or not video_path.exists():
                raise RuntimeError(
                    "ffmpeg failed while creating the mock MP4. "
                    f"See {logs_path} for details."
                )

        metadata_path = write_metadata(
            output_path,
            {
                "runtime": self.name,
                "model_version": self.model_version,
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "seed": request.seed,
                "settings": request.model_dump(),
                "output_file": video_path.name,
            },
        )
        progress(1.0, "postprocessing", "mock output ready")
        return GenerationResult(video_path=video_path, metadata_path=metadata_path, model_version=self.model_version)

    def unload(self) -> None:
        return None

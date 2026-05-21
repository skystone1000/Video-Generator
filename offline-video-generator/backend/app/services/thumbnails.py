import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from ..config import get_settings


def ffmpeg_available() -> bool:
    settings = get_settings()
    return shutil.which(settings.ffmpeg_path) is not None or Path(settings.ffmpeg_path).exists()


def create_thumbnail(video_path: Path, output_dir: Path) -> Path | None:
    settings = get_settings()
    if not ffmpeg_available():
        return None
    thumbnail_path = output_dir / "thumbnail.jpg"
    command = [
        settings.ffmpeg_path,
        "-y",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(thumbnail_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not thumbnail_path.exists():
        return None
    return thumbnail_path


def probe_video(video_path: Path) -> dict[str, float | int | None]:
    settings = get_settings()
    if shutil.which(settings.ffprobe_path) is None and not Path(settings.ffprobe_path).exists():
        return {"duration_seconds": None, "fps": None, "width": None, "height": None}

    command = [
        settings.ffprobe_path,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,duration",
        "-of",
        "json",
        str(video_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {"duration_seconds": None, "fps": None, "width": None, "height": None}

    try:
        payload = json.loads(result.stdout)
        stream = payload["streams"][0]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return {"duration_seconds": None, "fps": None, "width": None, "height": None}

    fps = None
    raw_rate = stream.get("r_frame_rate")
    if raw_rate:
        try:
            fps = float(Fraction(raw_rate))
        except (ValueError, ZeroDivisionError):
            fps = None

    duration = None
    if stream.get("duration"):
        try:
            duration = float(stream["duration"])
        except ValueError:
            duration = None

    return {
        "duration_seconds": duration,
        "fps": fps,
        "width": stream.get("width"),
        "height": stream.get("height"),
    }

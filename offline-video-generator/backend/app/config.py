from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_env: str = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    database_url: str = "sqlite:///./data/app.db"
    output_dir: str = "./data/outputs"
    thumbnail_dir: str = "./data/thumbnails"
    log_dir: str = "./data/logs"

    video_runtime: str = "mock"
    mock_sample_mp4_path: str | None = None

    hunyuan_original_repo_path: str = "../../models/HunyuanVideo"
    hunyuan_original_ckpt_path: str = "../../models/HunyuanVideo/ckpts"
    hunyuan_15_repo_path: str = "../../models/HunyuanVideo-1.5"
    hunyuan_15_model_path: str = "../../models/HunyuanVideo-1.5/ckpts"
    hunyuan_15_torchrun_path: str = "torchrun"
    hunyuan_15_nproc_per_node: int = 1
    hunyuan_15_enable_sr: bool = False
    hunyuan_15_use_sage_attn: bool = False
    hunyuan_15_enable_cache: bool = False

    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    max_active_jobs: int = Field(default=1, ge=1, le=8)
    default_preset: str = "standard"

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def resolve_path(self, raw_path: str | None) -> Path | None:
        if not raw_path:
            return None
        path = Path(raw_path).expanduser()
        if path.is_absolute():
            return path
        return BACKEND_ROOT / path

    @property
    def resolved_output_dir(self) -> Path:
        return self.resolve_path(self.output_dir) or BACKEND_ROOT / "data" / "outputs"

    @property
    def resolved_thumbnail_dir(self) -> Path:
        return self.resolve_path(self.thumbnail_dir) or BACKEND_ROOT / "data" / "thumbnails"

    @property
    def resolved_log_dir(self) -> Path:
        return self.resolve_path(self.log_dir) or BACKEND_ROOT / "data" / "logs"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url.startswith("sqlite:///./"):
            return "sqlite:///" + str(BACKEND_ROOT / self.database_url.removeprefix("sqlite:///./"))
        return self.database_url

    def ensure_runtime_dirs(self) -> None:
        for directory in [
            BACKEND_ROOT / "data",
            self.resolved_output_dir,
            self.resolved_thumbnail_dir,
            self.resolved_log_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings

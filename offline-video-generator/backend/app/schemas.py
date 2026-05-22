from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import JobStatus


RuntimeName = Literal["mock", "hunyuan_original", "hunyuan_15"]


class GenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    negative_prompt: str = ""
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    width: int = Field(default=1280, gt=0, le=4096)
    height: int = Field(default=720, gt=0, le=4096)
    video_length: int = Field(default=129, ge=1, le=257)
    fps: int = Field(default=24, ge=1, le=60)
    steps: int = Field(default=50, ge=1, le=120)
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    cfg_scale: float = Field(default=6.0, ge=0.0, le=30.0)
    flow_shift: float = Field(default=7.0, ge=0.0, le=20.0)
    use_cpu_offload: bool = True
    use_fp8: bool = False
    rewrite_prompt: bool = False
    preset: str = "standard"
    runtime: RuntimeName = "mock"

    @field_validator("prompt")
    @classmethod
    def prompt_must_have_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Prompt must be non-empty.")
        return cleaned

    @field_validator("aspect_ratio")
    @classmethod
    def aspect_ratio_must_be_supported(cls, value: str) -> str:
        allowed = {"16:9", "9:16", "1:1", "4:3", "3:4", "21:9"}
        if value not in allowed:
            raise ValueError(f"Aspect ratio must be one of {sorted(allowed)}.")
        return value


class JobRead(BaseModel):
    id: int
    status: JobStatus
    prompt: str
    negative_prompt: str
    rewritten_prompt: str | None = None
    seed: int
    runtime: str
    model_version: str | None = None
    settings: dict[str, Any]
    progress: float
    current_stage: str
    output_asset_id: int | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobVariationRequest(BaseModel):
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    prompt: str | None = Field(default=None, max_length=4000)


class AssetPatch(BaseModel):
    favorite: bool | None = None
    tags: list[str] | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    file_path: str
    thumbnail_path: str | None = None
    preview_path: str | None = None
    metadata_path: str | None = None
    duration_seconds: float | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    favorite: bool
    tags: list[str]
    created_at: datetime


class PresetRead(BaseModel):
    id: int
    name: str
    description: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PresetWrite(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    description: str = ""
    settings: dict[str, Any]


class SystemStatus(BaseModel):
    status: str
    runtime: str
    model_loaded: bool
    queue_depth: int
    active_job_id: int | None
    offline_mode: bool = True


class GpuStatus(BaseModel):
    available: bool
    provider: str = "torch"
    devices: list[dict[str, Any]] = []
    error: str | None = None

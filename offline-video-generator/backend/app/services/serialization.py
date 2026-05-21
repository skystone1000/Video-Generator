import json
from typing import Any

from ..models import Asset, Job, Preset
from ..schemas import AssetRead, JobRead, PresetRead


def parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def job_to_read(job: Job) -> JobRead:
    return JobRead(
        id=job.id,
        status=job.status,
        prompt=job.prompt,
        negative_prompt=job.negative_prompt,
        rewritten_prompt=job.rewritten_prompt,
        seed=job.seed,
        runtime=job.runtime,
        model_version=job.model_version,
        settings=parse_json_object(job.settings_json),
        progress=job.progress,
        current_stage=job.current_stage,
        output_asset_id=job.output_asset_id,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def asset_to_read(asset: Asset) -> AssetRead:
    return AssetRead(
        id=asset.id,
        job_id=asset.job_id,
        file_path=asset.file_path,
        thumbnail_path=asset.thumbnail_path,
        preview_path=asset.preview_path,
        metadata_path=asset.metadata_path,
        duration_seconds=asset.duration_seconds,
        fps=asset.fps,
        width=asset.width,
        height=asset.height,
        favorite=asset.favorite,
        tags=parse_json_list(asset.tags_json),
        created_at=asset.created_at,
    )


def preset_to_read(preset: Preset) -> PresetRead:
    return PresetRead(
        id=preset.id,
        name=preset.name,
        description=preset.description,
        settings=parse_json_object(preset.settings_json),
        created_at=preset.created_at,
        updated_at=preset.updated_at,
    )

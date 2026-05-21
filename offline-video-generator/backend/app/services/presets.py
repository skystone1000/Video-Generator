import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Preset


DEFAULT_PRESETS = [
    {
        "name": "draft",
        "description": "Fast local draft settings for queue and UI checks.",
        "settings": {
            "runtime": "mock",
            "aspect_ratio": "16:9",
            "resolution": "480p",
            "width": 854,
            "height": 480,
            "video_length": 48,
            "fps": 24,
            "steps": 12,
            "cfg_scale": 5.0,
            "flow_shift": 7.0,
            "use_cpu_offload": True,
            "use_fp8": False,
            "rewrite_prompt": False,
            "preset": "draft",
        },
    },
    {
        "name": "standard",
        "description": "Balanced 720p creator default.",
        "settings": {
            "runtime": "mock",
            "aspect_ratio": "16:9",
            "resolution": "720p",
            "width": 1280,
            "height": 720,
            "video_length": 129,
            "fps": 24,
            "steps": 50,
            "cfg_scale": 6.0,
            "flow_shift": 7.0,
            "use_cpu_offload": True,
            "use_fp8": False,
            "rewrite_prompt": False,
            "preset": "standard",
        },
    },
    {
        "name": "vertical-short",
        "description": "Vertical social-video format.",
        "settings": {
            "runtime": "mock",
            "aspect_ratio": "9:16",
            "resolution": "720p",
            "width": 720,
            "height": 1280,
            "video_length": 129,
            "fps": 24,
            "steps": 40,
            "cfg_scale": 6.0,
            "flow_shift": 7.0,
            "use_cpu_offload": True,
            "use_fp8": False,
            "rewrite_prompt": False,
            "preset": "vertical-short",
        },
    },
]


def seed_default_presets(session: Session) -> None:
    for item in DEFAULT_PRESETS:
        existing = session.scalar(select(Preset).where(Preset.name == item["name"]))
        if existing:
            continue
        session.add(
            Preset(
                name=item["name"],
                description=item["description"],
                settings_json=json.dumps(item["settings"]),
            )
        )
    session.commit()

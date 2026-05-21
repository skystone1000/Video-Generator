import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_session
from ..models import Preset
from ..schemas import PresetRead, PresetWrite
from ..services.serialization import preset_to_read

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=list[PresetRead])
def list_presets(session: Session = Depends(get_session)) -> list[PresetRead]:
    presets = session.scalars(select(Preset).order_by(Preset.name.asc())).all()
    return [preset_to_read(preset) for preset in presets]


@router.post("", response_model=PresetRead, status_code=201)
def create_preset(payload: PresetWrite, session: Session = Depends(get_session)) -> PresetRead:
    existing = session.scalar(select(Preset).where(Preset.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Preset name already exists.")
    preset = Preset(
        name=payload.name,
        description=payload.description,
        settings_json=json.dumps(payload.settings),
    )
    session.add(preset)
    session.commit()
    session.refresh(preset)
    return preset_to_read(preset)


@router.put("/{preset_id}", response_model=PresetRead)
def update_preset(preset_id: int, payload: PresetWrite, session: Session = Depends(get_session)) -> PresetRead:
    preset = session.get(Preset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found.")
    preset.name = payload.name
    preset.description = payload.description
    preset.settings_json = json.dumps(payload.settings)
    session.commit()
    session.refresh(preset)
    return preset_to_read(preset)


@router.delete("/{preset_id}", status_code=204)
def delete_preset(preset_id: int, session: Session = Depends(get_session)) -> None:
    preset = session.get(Preset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found.")
    session.delete(preset)
    session.commit()

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_session
from ..models import Asset
from ..schemas import AssetPatch, AssetRead
from ..services.serialization import asset_to_read

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def list_assets(session: Session = Depends(get_session)) -> list[AssetRead]:
    assets = session.scalars(select(Asset).order_by(Asset.created_at.desc(), Asset.id.desc()).limit(200)).all()
    return [asset_to_read(asset) for asset in assets]


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, session: Session = Depends(get_session)) -> AssetRead:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return asset_to_read(asset)


@router.get("/{asset_id}/video")
def get_video(asset_id: int, session: Session = Depends(get_session)) -> FileResponse:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    path = Path(asset.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk.")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@router.get("/{asset_id}/thumbnail")
def get_thumbnail(asset_id: int, session: Session = Depends(get_session)) -> FileResponse:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    if not asset.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail is not available.")
    path = Path(asset.thumbnail_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found on disk.")
    return FileResponse(path, media_type="image/jpeg", filename=path.name)


@router.patch("/{asset_id}", response_model=AssetRead)
def patch_asset(asset_id: int, patch: AssetPatch, session: Session = Depends(get_session)) -> AssetRead:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    if patch.favorite is not None:
        asset.favorite = patch.favorite
    if patch.tags is not None:
        asset.tags_json = json.dumps(patch.tags)
    session.commit()
    session.refresh(asset)
    return asset_to_read(asset)


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, session: Session = Depends(get_session)) -> None:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    session.delete(asset)
    session.commit()

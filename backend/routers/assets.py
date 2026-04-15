from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/", response_model=List[schemas.AssetResponse])
def list_assets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Asset).offset(skip).limit(limit).all()


@router.get("/{asset_id}", response_model=schemas.AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    return asset


@router.post("/", response_model=schemas.AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(payload: schemas.AssetCreate, db: Session = Depends(get_db)):
    if db.query(models.Asset).filter(models.Asset.hostname == payload.hostname).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset '{payload.hostname}' already exists.",
        )
    asset = models.Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    db.add(models.AuditLog(
        action="asset_created",
        detail=f"Created asset {asset.hostname} ({asset.ip_address})",
    ))
    db.commit()
    return asset


@router.put("/{asset_id}", response_model=schemas.AssetResponse)
def update_asset(asset_id: int, payload: schemas.AssetUpdate, db: Session = Depends(get_db)):
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    patch = payload.model_dump(exclude_unset=True)
    for field, value in patch.items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    db.add(models.AuditLog(
        action="asset_updated",
        detail=f"Updated {asset.hostname}: {', '.join(patch.keys())}",
    ))
    db.commit()
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    db.add(models.AuditLog(
        action="asset_deleted",
        detail=f"Deleted asset {asset.hostname}",
    ))
    db.flush()
    db.delete(asset)
    db.commit()

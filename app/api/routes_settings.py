from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    return {
        "default_printer_id": SettingsService.get_value(db, "default_printer_id"),
        "ui_refresh_seconds": SettingsService.get_value(db, "ui_refresh_seconds", "3"),
        "camera_proxy_enabled": SettingsService.get_value(db, "camera_proxy_enabled", "0"),
    }


@router.post("")
def set_settings(payload: dict, db: Session = Depends(get_db)):
    for key, value in payload.items():
        SettingsService.set_value(db, key, str(value) if value is not None else None)
    db.commit()
    return {"ok": True}

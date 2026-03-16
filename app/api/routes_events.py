from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/{printer_id}")
def recent_events(printer_id: int, db: Session = Depends(get_db)):
    events = EventService.recent(db, printer_id)
    return [
        {
            "id": item.id,
            "event_type": item.event_type,
            "severity": item.severity,
            "message": item.message,
            "created_at": item.created_at,
        }
        for item in events
    ]

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.utils import utc_now_iso
from app.models.db_models import PrinterEvent


class EventService:
    @staticmethod
    def log(db: Session, printer_id: int, event_type: str, severity: str = "info", message: str | None = None, payload: dict | None = None) -> PrinterEvent:
        event = PrinterEvent(
            printer_id=printer_id,
            event_type=event_type,
            severity=severity,
            message=message,
            payload_json=json.dumps(payload) if payload else None,
            created_at=utc_now_iso(),
        )
        db.add(event)
        db.flush()
        return event

    @staticmethod
    def recent(db: Session, printer_id: int, limit: int = 20) -> list[PrinterEvent]:
        stmt = (
            select(PrinterEvent)
            .where(PrinterEvent.printer_id == printer_id)
            .order_by(PrinterEvent.id.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

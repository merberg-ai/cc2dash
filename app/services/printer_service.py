from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import MQTT_DEFAULT_USERNAME
from app.core.camera import CameraHelper
from app.core.utils import utc_now_iso
from app.models.db_models import Printer, PrinterState


class PrinterService:
    @staticmethod
    def list_printers(db: Session) -> list[Printer]:
        stmt = select(Printer).order_by(Printer.id.asc())
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_printer(db: Session, printer_id: int) -> Printer | None:
        return db.get(Printer, printer_id)

    @staticmethod
    def create_printer(
        db: Session,
        name: str,
        ip_address: str,
        access_code: str | None = None,
        camera_url: str | None = None,
    ) -> Printer:
        now = utc_now_iso()
        printer = Printer(
            name=name,
            ip_address=ip_address,
            access_code=access_code,
            mqtt_username=MQTT_DEFAULT_USERNAME,
            mqtt_password=access_code,
            camera_url=camera_url or CameraHelper.default_camera_url(ip_address),
            created_at=now,
            updated_at=now,
        )
        db.add(printer)
        db.flush()

        state = PrinterState(
            printer_id=printer.id,
            is_online=False,
            updated_at=now,
        )
        db.add(state)
        db.flush()
        return printer

    @staticmethod
    def update_printer(db: Session, printer: Printer, **updates) -> Printer:
        for key, value in updates.items():
            if value is not None and hasattr(printer, key):
                setattr(printer, key, value)
        printer.updated_at = utc_now_iso()
        if updates.get("access_code") is not None:
            printer.mqtt_password = updates["access_code"]
        if updates.get("ip_address") and not updates.get("camera_url"):
            printer.camera_url = CameraHelper.default_camera_url(updates["ip_address"])
        db.add(printer)
        db.flush()
        return printer

    @staticmethod
    def apply_discovery_metadata(db: Session, printer: Printer, discovery: dict | None) -> Printer:
        if not discovery:
            return printer
        changed = False
        for field, source_key in (
            ("serial_number", "serial_number"),
            ("model", "model"),
            ("token_status", "token_status"),
            ("lan_status", "lan_status"),
        ):
            value = discovery.get(source_key)
            if value is not None and getattr(printer, field) != value:
                setattr(printer, field, value)
                changed = True
        host_name = discovery.get("host_name")
        if host_name and not printer.name:
            printer.name = host_name
            changed = True
        if changed:
            printer.updated_at = utc_now_iso()
            db.add(printer)
            db.flush()
        return printer

    @staticmethod
    def delete_printer(db: Session, printer: Printer) -> None:
        db.delete(printer)
        db.flush()

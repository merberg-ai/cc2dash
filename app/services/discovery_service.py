from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.discovery import scan_for_printers
from app.core.utils import utc_now_iso
from app.models.db_models import DiscoveredPrinter


class DiscoveryService:
    @staticmethod
    def scan(db: Session) -> list[DiscoveredPrinter]:
        db.execute(delete(DiscoveredPrinter))
        results = scan_for_printers()
        saved: list[DiscoveredPrinter] = []
        for item in results:
            row = DiscoveredPrinter(
                ip_address=item.get("ip_address", ""),
                serial_number=item.get("serial_number"),
                model=item.get("model"),
                host_name=item.get("host_name"),
                token_status=item.get("token_status"),
                lan_status=item.get("lan_status"),
                discovered_at=utc_now_iso(),
            )
            db.add(row)
            saved.append(row)
        db.flush()
        return saved

    @staticmethod
    def list_results(db: Session) -> list[DiscoveredPrinter]:
        stmt = select(DiscoveredPrinter).order_by(DiscoveredPrinter.id.desc())
        return list(db.scalars(stmt).all())

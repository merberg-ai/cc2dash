from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.discovery_service import DiscoveryService

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


@router.post("/scan")
def scan(db: Session = Depends(get_db)):
    results = DiscoveryService.scan(db)
    db.commit()
    return {"ok": True, "count": len(results)}


@router.get("/results")
def results(db: Session = Depends(get_db)):
    items = DiscoveryService.list_results(db)
    return [
        {
            "id": item.id,
            "ip_address": item.ip_address,
            "serial_number": item.serial_number,
            "model": item.model,
            "host_name": item.host_name,
            "token_status": item.token_status,
            "lan_status": item.lan_status,
            "discovered_at": item.discovered_at,
        }
        for item in items
    ]

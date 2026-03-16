from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.printer_service import PrinterService
from app.services.status_service import StatusService

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("/{printer_id}")
def get_status(printer_id: int, db: Session = Depends(get_db)):
    printer = PrinterService.get_printer(db, printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    return StatusService.get_status(db, printer)

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.mqtt_client import probe_mqtt_connection
from app.core.printer_manager import printer_manager
from app.dependencies import get_db
from app.models.api_models import PrinterCreateRequest, PrinterResponse, PrinterUpdateRequest
from app.services.event_service import EventService
from app.services.printer_service import PrinterService

router = APIRouter(prefix="/api/printers", tags=["printers"])


@router.get("", response_model=list[PrinterResponse])
def list_printers(db: Session = Depends(get_db)):
    printers = PrinterService.list_printers(db)
    response: list[PrinterResponse] = []
    for printer in printers:
        live = printer_manager.get_live_state(printer.id)
        response.append(
            PrinterResponse(
                id=printer.id,
                name=printer.name,
                ip_address=printer.ip_address,
                serial_number=printer.serial_number,
                model=printer.model,
                is_enabled=printer.is_enabled,
                is_online=bool(live.is_online) if live else bool(printer.state.is_online if printer.state else False),
            )
        )
    return response


@router.post("", response_model=PrinterResponse)
def create_printer(payload: PrinterCreateRequest, db: Session = Depends(get_db)):
    printer = PrinterService.create_printer(
        db,
        name=payload.name,
        ip_address=payload.ip_address,
        access_code=payload.access_code,
        camera_url=payload.camera_url,
    )
    probe = probe_mqtt_connection(printer.ip_address, access_code=printer.access_code)
    if probe.get("ok"):
        PrinterService.apply_discovery_metadata(db, printer, probe.get("details"))
        EventService.log(db, printer.id, "printer_added", message=f"Added printer {printer.name}")
    else:
        EventService.log(db, printer.id, "printer_added", severity="warning", message=f"Added printer {printer.name}; initial probe failed: {probe.get('message')}")
    db.commit()
    db.refresh(printer)
    if printer.is_enabled:
        printer_manager.start_printer(printer)
    return PrinterResponse(
        id=printer.id,
        name=printer.name,
        ip_address=printer.ip_address,
        serial_number=printer.serial_number,
        model=printer.model,
        is_enabled=printer.is_enabled,
        is_online=False,
    )


@router.put("/{printer_id}", response_model=PrinterResponse)
def update_printer(printer_id: int, payload: PrinterUpdateRequest, db: Session = Depends(get_db)):
    printer = PrinterService.get_printer(db, printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    printer = PrinterService.update_printer(db, printer, **payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(printer)
    if printer.is_enabled:
        printer_manager.restart_printer(printer)
    else:
        printer_manager.stop_printer(printer.id)
    live = printer_manager.get_live_state(printer.id)
    return PrinterResponse(
        id=printer.id,
        name=printer.name,
        ip_address=printer.ip_address,
        serial_number=printer.serial_number,
        model=printer.model,
        is_enabled=printer.is_enabled,
        is_online=bool(live.is_online) if live else False,
    )


@router.delete("/{printer_id}")
def delete_printer(printer_id: int, db: Session = Depends(get_db)):
    printer = PrinterService.get_printer(db, printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    printer_manager.stop_printer(printer_id)
    PrinterService.delete_printer(db, printer)
    db.commit()
    return {"ok": True}


@router.post("/{printer_id}/test")
def test_printer(printer_id: int, db: Session = Depends(get_db)):
    printer = PrinterService.get_printer(db, printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    result = probe_mqtt_connection(
        printer.ip_address,
        access_code=printer.access_code,
        serial_number=printer.serial_number,
        token_status=printer.token_status,
    )
    if result.get("ok"):
        PrinterService.apply_discovery_metadata(db, printer, result.get("details"))
        db.commit()
        db.refresh(printer)
    return result

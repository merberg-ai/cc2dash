from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.event_service import EventService
from app.services.printer_service import PrinterService
from app.services.settings_service import SettingsService
from app.services.status_service import StatusService
from app.settings import TEMPLATES_DIR

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    printers = PrinterService.list_printers(db)
    if not printers:
        return RedirectResponse(url="/setup", status_code=302)

    default_printer_id = SettingsService.get_value(db, "default_printer_id")
    target = printers[0]
    if default_printer_id:
        for printer in printers:
            if str(printer.id) == str(default_printer_id):
                target = printer
                break
    return RedirectResponse(url=f"/printer/{target.id}", status_code=302)


@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, db: Session = Depends(get_db)):
    printers = PrinterService.list_printers(db)
    return templates.TemplateResponse(
        request,
        "setup.html",
        {
            "printers": printers,
            "page_title": "Setup",
        },
    )


@router.get("/printer/{printer_id}", response_class=HTMLResponse)
def printer_page(printer_id: int, request: Request, db: Session = Depends(get_db)):
    printer = PrinterService.get_printer(db, printer_id)
    if not printer:
        return RedirectResponse(url="/setup", status_code=302)
    status = StatusService.get_status(db, printer)
    events = EventService.recent(db, printer.id, limit=10)
    return templates.TemplateResponse(
        request,
        "printer.html",
        {
            "printer": printer,
            "status": status,
            "events": events,
            "page_title": printer.name,
        },
    )

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes_discovery import router as discovery_router
from app.api.routes_events import router as events_router
from app.api.routes_printers import router as printers_router
from app.api.routes_settings import router as settings_router
from app.api.routes_status import router as status_router
from app.api.routes_ui import router as ui_router
from app.core.printer_manager import printer_manager
from app.db import SessionLocal, init_db
from app.models.db_models import Printer
from app.models.state_models import LivePrinterState, TemperatureState, TimingState
from app.settings import APP_TITLE, STATIC_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        printers = db.query(Printer).filter(Printer.is_enabled == True).all()  # noqa: E712
        for printer in printers:
            stored = printer.state
            state = LivePrinterState(
                printer_id=printer.id,
                is_online=bool(stored.is_online) if stored else False,
                status=stored.status if stored else None,
                sub_status=stored.sub_status if stored else None,
                current_file=stored.current_file if stored else None,
                progress=stored.progress if stored else None,
                layer_current=stored.layer_current if stored else None,
                layer_total=stored.layer_total if stored else None,
                fan_speed=stored.fan_speed if stored else None,
                z_offset=stored.z_offset if stored else None,
                last_message_at=stored.last_message_at if stored else None,
                camera_url=printer.camera_url,
                temperatures=TemperatureState(
                    nozzle=stored.nozzle_temp if stored else None,
                    nozzle_target=stored.nozzle_target if stored else None,
                    bed=stored.bed_temp if stored else None,
                    bed_target=stored.bed_target if stored else None,
                    chamber=stored.chamber_temp if stored else None,
                ),
                timing=TimingState(
                    elapsed_seconds=stored.elapsed_seconds if stored else None,
                    remaining_seconds=stored.remaining_seconds if stored else None,
                ),
            )
            printer_manager.hydrate_state(printer.id, state)
            printer_manager.start_printer(printer)
    finally:
        db.close()
    yield
    for printer_id in list(printer_manager.clients.keys()):
        printer_manager.stop_printer(printer_id)


app = FastAPI(title=APP_TITLE, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(ui_router)
app.include_router(printers_router)
app.include_router(status_router)
app.include_router(discovery_router)
app.include_router(events_router)
app.include_router(settings_router)

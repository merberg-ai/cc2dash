from sqlalchemy.orm import Session

from app.core.printer_manager import printer_manager
from app.models.api_models import StatusResponse
from app.models.db_models import Printer, PrinterState


class StatusService:
    @staticmethod
    def get_status(db: Session, printer: Printer) -> StatusResponse:
        live = printer_manager.get_live_state(printer.id)
        stored = db.get(PrinterState, printer.id)

        return StatusResponse(
            printer_id=printer.id,
            is_online=live.is_online if live else bool(stored.is_online if stored else False),
            status=live.status if live and live.status is not None else (stored.status if stored else None),
            sub_status=live.sub_status if live and live.sub_status is not None else (stored.sub_status if stored else None),
            current_file=live.current_file if live and live.current_file is not None else (stored.current_file if stored else None),
            progress=live.progress if live and live.progress is not None else (stored.progress if stored else None),
            layer_current=live.layer_current if live and live.layer_current is not None else (stored.layer_current if stored else None),
            layer_total=live.layer_total if live and live.layer_total is not None else (stored.layer_total if stored else None),
            nozzle_temp=live.temperatures.nozzle if live else (stored.nozzle_temp if stored else None),
            nozzle_target=live.temperatures.nozzle_target if live else (stored.nozzle_target if stored else None),
            bed_temp=live.temperatures.bed if live else (stored.bed_temp if stored else None),
            bed_target=live.temperatures.bed_target if live else (stored.bed_target if stored else None),
            elapsed_seconds=live.timing.elapsed_seconds if live else (stored.elapsed_seconds if stored else None),
            remaining_seconds=live.timing.remaining_seconds if live else (stored.remaining_seconds if stored else None),
            camera_url=live.camera_url if live and live.camera_url else printer.camera_url,
            last_message_at=live.last_message_at if live else (stored.last_message_at if stored else None),
        )

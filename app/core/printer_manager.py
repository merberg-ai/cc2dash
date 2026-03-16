from __future__ import annotations

from app.core.mqtt_client import PrinterMqttClient
from app.core.printer_state import live_state_store
from app.models.db_models import Printer
from app.models.state_models import LivePrinterState


class PrinterManager:
    def __init__(self) -> None:
        self.clients: dict[int, PrinterMqttClient] = {}

    def hydrate_state(self, printer_id: int, state: LivePrinterState) -> None:
        live_state_store.upsert(state)

    def start_printer(self, printer: Printer) -> None:
        self.stop_printer(printer.id)
        client = PrinterMqttClient(
            printer_id=printer.id,
            ip_address=printer.ip_address,
            serial_number=printer.serial_number,
            access_code=printer.access_code,
            token_status=printer.token_status,
            camera_url=printer.camera_url,
        )
        self.clients[printer.id] = client
        state = live_state_store.get(printer.id) or LivePrinterState(printer_id=printer.id)
        state.camera_url = printer.camera_url
        live_state_store.upsert(state)
        client.connect()

    def stop_printer(self, printer_id: int) -> None:
        client = self.clients.pop(printer_id, None)
        if client:
            client.disconnect()
        state = live_state_store.get(printer_id)
        if state:
            state.is_online = False
            live_state_store.upsert(state)

    def restart_printer(self, printer: Printer) -> None:
        self.start_printer(printer)

    def get_live_state(self, printer_id: int) -> LivePrinterState | None:
        return live_state_store.get(printer_id)

    def get_client(self, printer_id: int) -> PrinterMqttClient | None:
        return self.clients.get(printer_id)


printer_manager = PrinterManager()

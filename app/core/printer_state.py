from __future__ import annotations

from threading import RLock

from app.models.state_models import LivePrinterState


class LiveStateStore:
    def __init__(self) -> None:
        self._state: dict[int, LivePrinterState] = {}
        self._lock = RLock()

    def get(self, printer_id: int) -> LivePrinterState | None:
        with self._lock:
            return self._state.get(printer_id)

    def upsert(self, state: LivePrinterState) -> None:
        with self._lock:
            self._state[state.printer_id] = state

    def remove(self, printer_id: int) -> None:
        with self._lock:
            self._state.pop(printer_id, None)

    def all(self) -> dict[int, LivePrinterState]:
        with self._lock:
            return dict(self._state)


live_state_store = LiveStateStore()

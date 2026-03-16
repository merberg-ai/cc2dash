from dataclasses import dataclass, field


@dataclass
class TemperatureState:
    nozzle: float | None = None
    nozzle_target: float | None = None
    bed: float | None = None
    bed_target: float | None = None
    chamber: float | None = None


@dataclass
class TimingState:
    elapsed_seconds: int | None = None
    remaining_seconds: int | None = None


@dataclass
class LivePrinterState:
    printer_id: int
    is_online: bool = False
    status: str | None = None
    sub_status: str | None = None
    current_file: str | None = None
    progress: float | None = None
    layer_current: int | None = None
    layer_total: int | None = None
    fan_speed: float | None = None
    z_offset: float | None = None
    last_message_at: str | None = None
    camera_url: str | None = None
    temperatures: TemperatureState = field(default_factory=TemperatureState)
    timing: TimingState = field(default_factory=TimingState)

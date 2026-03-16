from pydantic import BaseModel, Field


class PrinterCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    ip_address: str = Field(min_length=1, max_length=255)
    access_code: str | None = Field(default=None, max_length=64)
    camera_url: str | None = Field(default=None, max_length=500)


class PrinterUpdateRequest(BaseModel):
    name: str | None = None
    ip_address: str | None = None
    access_code: str | None = None
    camera_url: str | None = None
    is_enabled: bool | None = None


class PrinterResponse(BaseModel):
    id: int
    name: str
    ip_address: str
    serial_number: str | None = None
    model: str | None = None
    is_enabled: bool
    is_online: bool = False


class StatusResponse(BaseModel):
    printer_id: int
    is_online: bool
    status: str | None = None
    sub_status: str | None = None
    current_file: str | None = None
    progress: float | None = None
    layer_current: int | None = None
    layer_total: int | None = None
    nozzle_temp: float | None = None
    nozzle_target: float | None = None
    bed_temp: float | None = None
    bed_target: float | None = None
    elapsed_seconds: int | None = None
    remaining_seconds: int | None = None
    camera_url: str | None = None
    last_message_at: str | None = None


class EventResponse(BaseModel):
    id: int
    event_type: str
    severity: str
    message: str | None = None
    created_at: str

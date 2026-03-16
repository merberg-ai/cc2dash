from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Printer(Base):
    __tablename__ = "printers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ip_address: Mapped[str] = mapped_column(String, nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    access_code: Mapped[str | None] = mapped_column(String, nullable=True)
    mqtt_username: Mapped[str] = mapped_column(String, nullable=False, default="elegoo")
    mqtt_password: Mapped[str | None] = mapped_column(String, nullable=True)
    token_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lan_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    camera_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_connect_ok_at: Mapped[str | None] = mapped_column(String, nullable=True)
    last_connect_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    state: Mapped["PrinterState | None"] = relationship(back_populates="printer", cascade="all, delete-orphan", uselist=False)
    events: Mapped[list["PrinterEvent"]] = relationship(back_populates="printer", cascade="all, delete-orphan")


class PrinterState(Base):
    __tablename__ = "printer_state"

    printer_id: Mapped[int] = mapped_column(ForeignKey("printers.id", ondelete="CASCADE"), primary_key=True)
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    sub_status: Mapped[str | None] = mapped_column(String, nullable=True)
    current_file: Mapped[str | None] = mapped_column(String, nullable=True)
    progress: Mapped[float | None] = mapped_column(Float, nullable=True)
    layer_current: Mapped[int | None] = mapped_column(Integer, nullable=True)
    layer_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nozzle_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    nozzle_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    bed_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    bed_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    chamber_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    print_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    fan_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    elapsed_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remaining_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    z_offset: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_status_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    printer: Mapped["Printer"] = relationship(back_populates="state")


class PrinterEvent(Base):
    __tablename__ = "printer_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    printer_id: Mapped[int] = mapped_column(ForeignKey("printers.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, default="info")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    printer: Mapped["Printer"] = relationship(back_populates="events")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)


class DiscoveredPrinter(Base):
    __tablename__ = "discovered_printers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String, nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    host_name: Mapped[str | None] = mapped_column(String, nullable=True)
    token_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lan_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discovered_at: Mapped[str] = mapped_column(String, nullable=False)

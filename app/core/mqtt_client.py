from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass
from queue import Queue, Empty
from typing import Any

import paho.mqtt.client as mqtt

from app.constants import (
    COMMAND_TIMEOUT_SECONDS,
    EVENT_TYPE_CONNECT_ERROR,
    EVENT_TYPE_CONNECTED,
    EVENT_TYPE_DISCONNECTED,
    EVENT_TYPE_STATUS_CHANGED,
    FULL_STATUS_REFRESH_SECONDS,
    HEARTBEAT_INTERVAL_SECONDS,
    MQTT_DEFAULT_PASSWORD,
    MQTT_DEFAULT_USERNAME,
    MQTT_KEEPALIVE,
    MQTT_PORT,
    REGISTER_TIMEOUT_SECONDS,
)
from app.core.discovery import probe_printer
from app.core.mqtt_protocol import (
    METHOD_GET_ATTRIBUTES,
    METHOD_GET_STATUS,
    METHOD_ON_PRINTER_ATTRIBUTES,
    METHOD_ON_PRINTER_STATUS,
    build_api_request_topic,
    build_api_response_topic,
    build_command_payload,
    build_ping_payload,
    build_register_response_topic,
    build_register_topic,
    build_registration_payload,
    build_status_topic,
    extract_status_result,
    generate_client_id,
    generate_request_id,
    machine_status_name,
    merge_status_payload,
    normalize_attributes_payload,
    sub_status_name,
)
from app.core.utils import utc_now_iso
from app.db import session_scope
from app.models.db_models import Printer, PrinterState
from app.models.state_models import LivePrinterState, TemperatureState, TimingState
from app.services.event_service import EventService


@dataclass
class PrinterSessionStatus:
    printer_id: int
    connected: bool = False
    registered: bool = False
    last_error: str | None = None
    last_seen: str | None = None


class PrinterMqttClient:
    def __init__(self, printer_id: int, ip_address: str, serial_number: str | None = None, access_code: str | None = None, token_status: int | None = None, camera_url: str | None = None) -> None:
        self.printer_id = printer_id
        self.ip_address = ip_address
        self.serial_number = serial_number
        self.access_code = access_code
        self.token_status = token_status
        self.camera_url = camera_url

        self.client_id = generate_client_id()
        self.request_id = generate_request_id()
        self.status = PrinterSessionStatus(printer_id=printer_id)

        self._command_id = 0
        self._mqtt: mqtt.Client | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._registered_event = threading.Event()
        self._message_queue: Queue[dict[str, Any]] = Queue()
        self._last_ping_at = 0.0
        self._last_full_refresh_at = 0.0
        self._status_cache: dict[str, Any] = {}
        self._last_status_name: str | None = None
        self._last_sub_status_name: str | None = None

    def connect(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=f"cc2dash-printer-{self.printer_id}", daemon=True)
        self._thread.start()

    def disconnect(self) -> None:
        self._stop_event.set()
        mqtt_client = self._mqtt
        if mqtt_client:
            try:
                mqtt_client.loop_stop()
            except Exception:
                pass
            try:
                mqtt_client.disconnect()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.status.connected = False
        self.status.registered = False
        self.status.last_seen = utc_now_iso()
        self._mark_offline("Disconnected")

    def connection_summary(self) -> dict[str, Any]:
        return {
            "printer_id": self.printer_id,
            "connected": self.status.connected,
            "registered": self.status.registered,
            "last_error": self.status.last_error,
            "last_seen": self.status.last_seen,
            "ip_address": self.ip_address,
            "serial_number": self.serial_number,
            "client_id": self.client_id,
        }

    def _run(self) -> None:
        if not self.serial_number or self.token_status is None:
            discovered = probe_printer(self.ip_address)
            if discovered:
                self.serial_number = discovered.get("serial_number")
                self.token_status = discovered.get("token_status")
                self._persist_printer_metadata(discovered)
            else:
                self._handle_error("Discovery probe failed")
                return

        password = self.access_code if self.token_status == 1 and self.access_code else MQTT_DEFAULT_PASSWORD
        self._mqtt = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.client_id,
            protocol=mqtt.MQTTv311,
            clean_session=True,
        )
        self._mqtt.username_pw_set(MQTT_DEFAULT_USERNAME, password)
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_disconnect = self._on_disconnect
        self._mqtt.on_message = self._on_message
        self._mqtt.on_connect_fail = self._on_connect_fail

        try:
            self._mqtt.connect(self.ip_address, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
        except (OSError, socket.error) as exc:
            self._handle_error(f"MQTT connect failed: {exc}")
            return

        self._mqtt.loop_start()

        if not self._registered_event.wait(timeout=REGISTER_TIMEOUT_SECONDS):
            self._handle_error("Registration timed out")
            self._cleanup_loop()
            return

        while not self._stop_event.is_set():
            now = time.time()
            if now - self._last_ping_at >= HEARTBEAT_INTERVAL_SECONDS:
                self._publish_ping()
                self._last_ping_at = now
            if now - self._last_full_refresh_at >= FULL_STATUS_REFRESH_SECONDS:
                self._request_status_refresh()
                self._last_full_refresh_at = now
            self._drain_message_queue()
            time.sleep(0.25)

        self._cleanup_loop()

    def _cleanup_loop(self) -> None:
        mqtt_client = self._mqtt
        if mqtt_client:
            try:
                mqtt_client.loop_stop()
            except Exception:
                pass
            try:
                mqtt_client.disconnect()
            except Exception:
                pass

    def _next_command_id(self) -> int:
        self._command_id += 1
        return self._command_id

    def _on_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any, reason_code: mqtt.ReasonCode, _properties: Any = None) -> None:
        if reason_code != 0:
            self._handle_error(f"MQTT connect rejected: {reason_code}")
            return
        self.status.connected = True
        self.status.last_seen = utc_now_iso()
        if not self.serial_number:
            self._handle_error("Missing serial number after connect")
            return
        client.subscribe(build_register_response_topic(self.serial_number, self.request_id))
        client.publish(
            build_register_topic(self.serial_number),
            build_registration_payload(self.client_id, self.request_id),
            qos=0,
            retain=False,
        )
        self._connected_event.set()

    def _on_connect_fail(self, _client: mqtt.Client, _userdata: Any) -> None:
        self._handle_error("MQTT connect failed")

    def _on_disconnect(self, _client: mqtt.Client, _userdata: Any, _flags: Any, reason_code: mqtt.ReasonCode, _properties: Any = None) -> None:
        self.status.connected = False
        self.status.registered = False
        self.status.last_seen = utc_now_iso()
        if not self._stop_event.is_set():
            self._mark_offline(f"Disconnected: {reason_code}")

    def _on_message(self, client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode(errors="ignore") or "{}")
        except json.JSONDecodeError:
            return

        self.status.last_seen = utc_now_iso()
        topic = msg.topic
        if self.serial_number and topic == build_register_response_topic(self.serial_number, self.request_id):
            error_value = payload.get("error")
            if error_value == "ok":
                self.status.registered = True
                self.status.last_error = None
                client.subscribe(build_status_topic(self.serial_number))
                client.subscribe(build_api_response_topic(self.serial_number, self.client_id))
                self._registered_event.set()
                self._mark_online()
                self._request_attributes()
                self._request_status_refresh()
            else:
                self._handle_error(f"Registration failed: {error_value}")
                self._registered_event.set()
            return

        self._message_queue.put(payload)

    def _drain_message_queue(self) -> None:
        while True:
            try:
                payload = self._message_queue.get_nowait()
            except Empty:
                break
            self._handle_payload(payload)

    def _handle_payload(self, payload: dict[str, Any]) -> None:
        if payload.get("type") == "PONG":
            return

        method = payload.get("method")
        if method == METHOD_GET_ATTRIBUTES or method == METHOD_ON_PRINTER_ATTRIBUTES:
            self._handle_attributes(payload)
            return
        if method == METHOD_GET_STATUS or method == METHOD_ON_PRINTER_STATUS:
            self._handle_status(payload)
            return

    def _handle_attributes(self, payload: dict[str, Any]) -> None:
        attrs = normalize_attributes_payload(payload)
        self._persist_printer_metadata(
            {
                "serial_number": attrs.get("serial_number"),
                "model": attrs.get("model"),
                "host_name": attrs.get("hostname"),
                "ip_address": attrs.get("ip_address"),
            }
        )

    def _handle_status(self, payload: dict[str, Any]) -> None:
        result = extract_status_result(payload)
        self._status_cache = merge_status_payload(self._status_cache, result)
        machine_status = self._status_cache.get("machine_status") or {}
        print_status = self._status_cache.get("print_status") or {}
        extruder = self._status_cache.get("extruder") or {}
        heater_bed = self._status_cache.get("heater_bed") or {}
        chamber = self._status_cache.get("ztemperature_sensor") or self._status_cache.get("chamber") or {}
        fans = self._status_cache.get("fans") or {}
        gcode_move = self._status_cache.get("gcode_move_inf") or self._status_cache.get("gcode_move") or {}

        status_code = machine_status.get("status")
        sub_status_code = machine_status.get("sub_status")
        status_name = machine_status_name(status_code)
        sub_status_value = sub_status_name(sub_status_code)

        state = LivePrinterState(
            printer_id=self.printer_id,
            is_online=True,
            status=status_name,
            sub_status=sub_status_value,
            current_file=print_status.get("filename"),
            progress=float(print_status.get("progress") or machine_status.get("progress") or 0),
            layer_current=print_status.get("current_layer"),
            layer_total=print_status.get("total_layer"),
            fan_speed=self._fan_percent(fans.get("fan")),
            z_offset=self._safe_float(gcode_move.get("z")),
            last_message_at=utc_now_iso(),
            camera_url=self.camera_url,
            temperatures=TemperatureState(
                nozzle=self._safe_float(extruder.get("temperature")),
                nozzle_target=self._safe_float(extruder.get("target")),
                bed=self._safe_float(heater_bed.get("temperature")),
                bed_target=self._safe_float(heater_bed.get("target")),
                chamber=self._safe_float(chamber.get("temperature")),
            ),
            timing=TimingState(
                elapsed_seconds=self._safe_int(print_status.get("print_duration")),
                remaining_seconds=self._safe_int(print_status.get("remaining_time_sec")),
            ),
        )

        self.status.last_seen = state.last_message_at
        self._persist_state(state, self._status_cache)

        if status_name != self._last_status_name or sub_status_value != self._last_sub_status_name:
            self._last_status_name = status_name
            self._last_sub_status_name = sub_status_value
            with session_scope() as db:
                EventService.log(
                    db,
                    self.printer_id,
                    EVENT_TYPE_STATUS_CHANGED,
                    message=f"Status: {status_name or 'unknown'} / {sub_status_value or 'none'}",
                    payload={"status": status_name, "sub_status": sub_status_value},
                )

    def _request_attributes(self) -> None:
        self._publish_command(METHOD_GET_ATTRIBUTES)

    def _request_status_refresh(self) -> None:
        self._publish_command(METHOD_GET_STATUS)

    def _publish_ping(self) -> None:
        if not self._mqtt or not self.serial_number or not self.status.registered:
            return
        self._mqtt.publish(build_api_request_topic(self.serial_number, self.client_id), build_ping_payload(), qos=0, retain=False)

    def _publish_command(self, method: int, params: dict[str, Any] | None = None) -> None:
        if not self._mqtt or not self.serial_number or not self.status.registered:
            return
        payload = build_command_payload(self._next_command_id(), method, params)
        self._mqtt.publish(build_api_request_topic(self.serial_number, self.client_id), payload, qos=0, retain=False)

    def _mark_online(self) -> None:
        self.status.connected = True
        self.status.registered = True
        self.status.last_error = None
        self.status.last_seen = utc_now_iso()
        with session_scope() as db:
            printer = db.get(Printer, self.printer_id)
            if printer:
                printer.last_connect_ok_at = utc_now_iso()
                printer.last_connect_error = None
                state = db.get(PrinterState, self.printer_id)
                if state:
                    state.is_online = True
                    state.updated_at = utc_now_iso()
                EventService.log(db, self.printer_id, EVENT_TYPE_CONNECTED, message="Printer connected")

    def _mark_offline(self, message: str) -> None:
        with session_scope() as db:
            printer = db.get(Printer, self.printer_id)
            if printer:
                printer.last_connect_error = message
                state = db.get(PrinterState, self.printer_id)
                if state:
                    state.is_online = False
                    state.updated_at = utc_now_iso()
                EventService.log(db, self.printer_id, EVENT_TYPE_DISCONNECTED, severity="warning", message=message)

    def _handle_error(self, message: str) -> None:
        self.status.connected = False
        self.status.registered = False
        self.status.last_error = message
        self.status.last_seen = utc_now_iso()
        with session_scope() as db:
            printer = db.get(Printer, self.printer_id)
            if printer:
                printer.last_connect_error = message
                EventService.log(db, self.printer_id, EVENT_TYPE_CONNECT_ERROR, severity="error", message=message)
                state = db.get(PrinterState, self.printer_id)
                if state:
                    state.is_online = False
                    state.updated_at = utc_now_iso()

    def _persist_printer_metadata(self, discovered: dict[str, Any]) -> None:
        with session_scope() as db:
            printer = db.get(Printer, self.printer_id)
            if not printer:
                return
            changed = False
            serial_number = discovered.get("serial_number") or discovered.get("sn")
            model = discovered.get("model") or discovered.get("machine_model")
            host_name = discovered.get("host_name") or discovered.get("hostname")
            ip_address = discovered.get("ip_address") or discovered.get("ip")
            token_status = discovered.get("token_status")
            lan_status = discovered.get("lan_status")
            if serial_number and printer.serial_number != serial_number:
                printer.serial_number = serial_number
                self.serial_number = serial_number
                changed = True
            if model and printer.model != model:
                printer.model = model
                changed = True
            if host_name and printer.name != host_name:
                printer.name = host_name
                changed = True
            if ip_address and printer.ip_address != ip_address:
                printer.ip_address = ip_address
                self.ip_address = ip_address
                changed = True
            if token_status is not None and printer.token_status != token_status:
                printer.token_status = token_status
                self.token_status = token_status
                changed = True
            if lan_status is not None and printer.lan_status != lan_status:
                printer.lan_status = lan_status
                changed = True
            if changed:
                printer.updated_at = utc_now_iso()

    def _persist_state(self, live_state: LivePrinterState, raw_status: dict[str, Any]) -> None:
        from app.core.printer_state import live_state_store

        live_state_store.upsert(live_state)
        with session_scope() as db:
            state = db.get(PrinterState, self.printer_id)
            if not state:
                return
            state.is_online = live_state.is_online
            state.status = live_state.status
            state.sub_status = live_state.sub_status
            state.current_file = live_state.current_file
            state.progress = live_state.progress
            state.layer_current = live_state.layer_current
            state.layer_total = live_state.layer_total
            state.nozzle_temp = live_state.temperatures.nozzle
            state.nozzle_target = live_state.temperatures.nozzle_target
            state.bed_temp = live_state.temperatures.bed
            state.bed_target = live_state.temperatures.bed_target
            state.chamber_temp = live_state.temperatures.chamber
            state.fan_speed = live_state.fan_speed
            state.z_offset = live_state.z_offset
            state.elapsed_seconds = live_state.timing.elapsed_seconds
            state.remaining_seconds = live_state.timing.remaining_seconds
            state.raw_status_json = json.dumps(raw_status)
            state.last_message_at = live_state.last_message_at
            state.updated_at = utc_now_iso()

    @staticmethod
    def _fan_percent(fan_payload: dict[str, Any] | None) -> float | None:
        if not fan_payload:
            return None
        speed = fan_payload.get("speed")
        if speed is None:
            return None
        try:
            return round(float(speed) / 255.0 * 100.0, 1)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return None if value is None else int(value)
        except (TypeError, ValueError):
            return None


def probe_mqtt_connection(ip_address: str, access_code: str | None = None, serial_number: str | None = None, token_status: int | None = None, timeout: float = REGISTER_TIMEOUT_SECONDS) -> dict[str, Any]:
    discovery = None
    if not serial_number or token_status is None:
        discovery = probe_printer(ip_address, timeout=timeout)
        if not discovery:
            return {"ok": False, "message": "Discovery probe failed", "details": None}
        serial_number = discovery.get("serial_number")
        token_status = discovery.get("token_status")

    client_id = generate_client_id()
    request_id = generate_request_id()
    connected = threading.Event()
    registered = threading.Event()
    result: dict[str, Any] = {"ok": False, "message": "Timed out", "details": discovery}

    def on_connect(client: mqtt.Client, _userdata: Any, _flags: Any, reason_code: mqtt.ReasonCode, _properties: Any = None) -> None:
        if reason_code != 0:
            result["message"] = f"MQTT connect rejected: {reason_code}"
            registered.set()
            return
        connected.set()
        client.subscribe(build_register_response_topic(serial_number, request_id))
        client.publish(build_register_topic(serial_number), build_registration_payload(client_id, request_id), qos=0, retain=False)

    def on_message(client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode(errors="ignore") or "{}")
        except json.JSONDecodeError:
            return
        error_value = payload.get("error")
        if error_value == "ok":
            result["ok"] = True
            result["message"] = "Connected and registered successfully"
            result["details"] = {**(discovery or {}), "serial_number": serial_number, "token_status": token_status, "client_id": client_id}
        else:
            result["message"] = f"Registration failed: {error_value}"
        registered.set()
        client.disconnect()

    password = access_code if token_status == 1 and access_code else MQTT_DEFAULT_PASSWORD
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv311, clean_session=True)
    mqtt_client.username_pw_set(MQTT_DEFAULT_USERNAME, password)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    try:
        mqtt_client.connect(ip_address, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
        mqtt_client.loop_start()
        registered.wait(timeout=timeout)
    except Exception as exc:
        result["message"] = f"MQTT test failed: {exc}"
    finally:
        try:
            mqtt_client.loop_stop()
        except Exception:
            pass
        try:
            mqtt_client.disconnect()
        except Exception:
            pass

    return result

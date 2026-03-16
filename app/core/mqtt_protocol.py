from __future__ import annotations

import copy
import json
import random
import time
from typing import Any

STATUS_NAMES = {
    0: "initializing",
    1: "idle",
    2: "printing",
    3: "filament_operating",
    4: "filament_operating_2",
    5: "auto_leveling",
    6: "pid_calibrating",
    7: "resonance_testing",
    8: "self_checking",
    9: "updating",
    10: "homing",
    11: "file_transferring",
    12: "video_composing",
    13: "extruder_operating",
    14: "emergency_stop",
    15: "power_loss_recovery",
}

SUBSTATUS_NAMES = {
    0: "none",
    1041: "idle_in_print",
    1045: "extruder_preheating",
    1096: "extruder_preheating_2",
    1405: "bed_preheating",
    1906: "bed_preheating_2",
    2075: "printing",
    2077: "printing_completed",
    2401: "resuming",
    2402: "resuming_completed",
    2501: "pausing",
    2502: "paused",
    2505: "paused_2",
    2503: "stopping",
    2504: "stopped",
    2801: "homing",
    2802: "homing_completed",
    2901: "auto_leveling",
    2902: "auto_leveling_completed",
    3000: "uploading_file",
    3001: "uploading_file_completed",
    5934: "resonance_test",
    5935: "resonance_test_completed",
    5936: "resonance_test_failed",
}

METHOD_GET_ATTRIBUTES = 1001
METHOD_GET_STATUS = 1002
METHOD_ON_PRINTER_STATUS = 6000
METHOD_ON_PRINTER_ATTRIBUTES = 6008


def now_millis() -> int:
    return int(time.time() * 1000)


def generate_client_id() -> str:
    timestamp_hex = format(now_millis(), "x")[-5:]
    random_hex = format(random.randint(0, 0xFFF), "x")
    return f"0cli{timestamp_hex}{random_hex}"[:10]


def generate_request_id() -> str:
    uuid_part = "".join(format(random.randint(0, 15), "x") for _ in range(16))
    return f"{uuid_part}{format(now_millis(), 'x')}"


def build_register_topic(serial_number: str) -> str:
    return f"elegoo/{serial_number}/api_register"


def build_register_response_topic(serial_number: str, request_id: str) -> str:
    return f"elegoo/{serial_number}/{request_id}/register_response"


def build_status_topic(serial_number: str) -> str:
    return f"elegoo/{serial_number}/api_status"


def build_api_request_topic(serial_number: str, client_id: str) -> str:
    return f"elegoo/{serial_number}/{client_id}/api_request"


def build_api_response_topic(serial_number: str, client_id: str) -> str:
    return f"elegoo/{serial_number}/{client_id}/api_response"


def build_registration_payload(client_id: str, request_id: str) -> str:
    return json.dumps({"client_id": client_id, "request_id": request_id})


def build_ping_payload() -> str:
    return json.dumps({"type": "PING"})


def build_command_payload(command_id: int, method: int, params: dict[str, Any] | None = None) -> str:
    return json.dumps({"id": command_id, "method": method, "params": params or {}})


def merge_status_payload(base: dict[str, Any] | None, delta: dict[str, Any] | None) -> dict[str, Any]:
    if not base:
        return copy.deepcopy(delta or {})
    if not delta:
        return copy.deepcopy(base)

    merged = copy.deepcopy(base)
    for key, value in delta.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_status_payload(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def machine_status_name(status_code: int | None) -> str | None:
    if status_code is None:
        return None
    return STATUS_NAMES.get(status_code, f"status_{status_code}")


def sub_status_name(sub_status_code: int | None) -> str | None:
    if sub_status_code is None:
        return None
    return SUBSTATUS_NAMES.get(sub_status_code, f"sub_{sub_status_code}")


def normalize_attributes_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result") or {}
    return {
        "hostname": result.get("hostname") or result.get("host_name"),
        "model": result.get("machine_model"),
        "serial_number": result.get("sn"),
        "ip_address": result.get("ip"),
        "camera_connected": result.get("camera_connected"),
        "network_type": result.get("network_type"),
        "software_version": (result.get("software_version") or {}).get("ota_version"),
        "raw": result,
    }


def extract_status_result(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("method") in (METHOD_GET_STATUS, METHOD_ON_PRINTER_STATUS):
        return payload.get("result") or {}
    return {}

from __future__ import annotations

import json
import socket
from typing import Any

from app.constants import DISCOVERY_PORT, DISCOVERY_TIMEOUT_SECONDS


def _normalize_discovery_payload(payload: dict[str, Any], ip_address: str) -> dict[str, Any]:
    result = payload.get("result") or {}
    return {
        "ip_address": ip_address,
        "serial_number": result.get("sn"),
        "model": result.get("machine_model"),
        "host_name": result.get("host_name"),
        "token_status": result.get("token_status"),
        "lan_status": result.get("lan_status"),
        "raw": payload,
    }


def probe_printer(ip_address: str, timeout: float = DISCOVERY_TIMEOUT_SECONDS) -> dict[str, Any] | None:
    message = json.dumps({"id": 0, "method": 7000}).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(message, (ip_address, DISCOVERY_PORT))
        data, addr = sock.recvfrom(4096)
        payload = json.loads(data.decode(errors="ignore"))
        return _normalize_discovery_payload(payload, addr[0])
    except Exception:
        return None
    finally:
        sock.close()


def scan_for_printers(timeout: float = DISCOVERY_TIMEOUT_SECONDS) -> list[dict[str, Any]]:
    message = json.dumps({"id": 0, "method": 7000}).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    try:
        sock.sendto(message, ("255.255.255.255", DISCOVERY_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                break
            payload = json.loads(data.decode(errors="ignore"))
            item = _normalize_discovery_payload(payload, addr[0])
            key = item["serial_number"] or item["ip_address"]
            if key in seen:
                continue
            seen.add(key)
            results.append(item)
    finally:
        sock.close()
    return results

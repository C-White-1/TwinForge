"""Serialize and write the evidenced native OpenPLC project envelope."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path


def native_project_documents(
    *,
    project_name: str,
    task_name: str,
    interval: str,
    priority: int,
    native_program_name: str,
    ladder: str,
    compile_only: bool,
) -> dict[Path, str]:
    """Build the static project, device, pin-map, and program documents."""

    return {
        Path("project.json"): _json_text(
            _project_document(
                project_name,
                task_name,
                interval,
                priority,
                native_program_name,
            )
        ),
        Path("devices/configuration.json"): _json_text(
            _device_document(compile_only=compile_only)
        ),
        Path("devices/pin-mapping.json"): "[]\n",
        Path(f"pous/programs/{native_program_name}.ld"): ladder,
    }


def write_native_project_documents(
    destination: Path,
    documents: Mapping[Path, str],
) -> tuple[Path, ...]:
    """Write native documents deterministically and create required POU folders."""

    written: list[Path] = []
    for relative, text in documents.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    for relative in ("pous/function-blocks", "pous/functions"):
        (destination / relative).mkdir(parents=True, exist_ok=True)
    return tuple(written)


def _project_document(
    project_name: str,
    task_name: str,
    interval: str,
    priority: int,
    native_program_name: str,
) -> dict[str, object]:
    """Return the runtime-verified OpenPLC scheduling envelope."""

    return {
        "meta": {"name": project_name, "type": "plc-project"},
        "data": {
            "dataTypes": [],
            "pous": [],
            "configuration": {
                "resource": {
                    "tasks": [
                        {
                            "name": task_name,
                            "triggering": "Cyclic",
                            "interval": interval,
                            "priority": priority,
                        }
                    ],
                    "instances": [
                        {
                            "name": "instance0",
                            "task": task_name,
                            "program": native_program_name,
                        }
                    ],
                    "globalVariables": [],
                }
            },
            "deletedPous": [],
        },
    }


def _device_document(*, compile_only: bool) -> dict[str, object]:
    """Return the runtime-verified OpenPLC Runtime v3 device configuration."""

    return {
        "deviceBoard": "OpenPLC Runtime v3",
        "communicationPort": "",
        "runtimeIpAddress": "",
        "compileOnly": compile_only,
        "communicationConfiguration": {
            "modbusRTU": {
                "rtuInterface": "Serial",
                "rtuBaudRate": "115200",
                "rtuSlaveId": None,
                "rtuRS485ENPin": None,
            },
            "modbusTCP": {
                "tcpInterface": "Ethernet",
                "tcpMacAddress": "DE:AD:BE:EF:DE:AD",
                "tcpStaticHostConfiguration": {
                    "ipAddress": "",
                    "dns": "",
                    "gateway": "",
                    "subnet": "",
                },
            },
            "communicationPreferences": {
                "enabledRTU": False,
                "enabledTCP": False,
                "enabledDHCP": True,
            },
        },
    }


def _json_text(value: object) -> str:
    """Serialize a native JSON document with the established formatting."""

    return json.dumps(value, indent=2) + "\n"

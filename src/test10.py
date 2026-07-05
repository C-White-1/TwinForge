from pycomm3 import CIPDriver, LogixDriver
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import re


# -----------------------------
# Data Model
# -----------------------------

@dataclass
class Module:
    slot: int
    name: Optional[str] = None
    vendor: Optional[str] = None
    product_code: Optional[int] = None
    product_type: Optional[str] = None
    revision: Optional[dict] = None
    serial: Optional[str] = None
    identity: Optional[dict] = None
    io: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tag:
    name: str
    data_type: Optional[str]
    alias: Optional[str] = None


@dataclass
class DigitalTwin:
    controller: Dict[str, Any]
    modules: Dict[int, Module] = field(default_factory=dict)
    tags: Dict[str, Tag] = field(default_factory=dict)


# -----------------------------
# CIP Identity Read
# -----------------------------

def read_identity(plc, slot: int):
    """Read Identity Object via backplane routing."""
    route = f"1,{slot}"

    resp = plc.generic_message(
        service=0x0E,          # Get Attribute Single
        class_code=0x01,       # Identity Object
        instance=1,
        attribute=1,
        route_path=route
    )

    return resp.value if resp else None

# -----------------------------
# Scan slots via echo
# -----------------------------

def scan_slots_via_echo(plc, max_slots=20):
    modules = {}

    for slot in range(max_slots):
        try:
            resp = plc.generic_message(
                service=0x01,
                class_code=0x01,
                instance=1,
                attribute=1,
                route_path=f"1,{slot}"
            )

            if not resp or not resp.value:
                continue

            identity = resp.value

            # CRITICAL FIX: always wrap in Module
            modules[slot] = Module(
                slot=slot,
                name=identity.get("product_name"),
                vendor=identity.get("vendor"),
                product_code=identity.get("product_code"),
                product_type=identity.get("product_type"),
                revision=identity.get("revision"),
                serial=identity.get("serial"),
                identity=identity
            )

        except Exception:
            continue

    return modules

# -----------------------------
# Backplane Scan (REAL SOURCE OF TRUTH)
# -----------------------------

def scan_backplane(ip: str, max_slots: int = 20) -> Dict[int, Module]:
    modules = {}

    with CIPDriver(ip) as plc:
        for slot in range(max_slots):
            try:
                identity = read_identity(plc, slot)

                if not identity:
                    continue

                modules[slot] = Module(
                    slot=slot,
                    name=identity.get("product_name"),
                    vendor=identity.get("vendor"),
                    product_code=identity.get("product_code"),
                    product_type=identity.get("product_type"),
                    revision=identity.get("revision"),
                    serial=identity.get("serial"),
                    identity=identity
                )

            except Exception:
                continue

    return modules


# -----------------------------
# Tag Normalisation
# -----------------------------

def normalize_tags(raw_tags):
    tags = {}

    for t in raw_tags:

        # Case 1: string tags (most likely your current case)
        if isinstance(t, str):
            name = t
            tags[name] = Tag(name=name, data_type=None)
            continue

        # Case 2: dict tags
        if isinstance(t, dict):
            name = t.get("tag_name")
            if not name:
                continue

            tags[name] = Tag(
                name=name,
                data_type=t.get("data_type_name"),
                alias=t.get("alias")
            )

    return tags


# -----------------------------
# Tag → Module correlation (heuristic but explicit)
# -----------------------------

LOCAL_TAG_RE = re.compile(r"Local:(\d+):")

def correlate(tags: Dict[str, Tag], modules: Dict[int, Module]):
    mapping = []

    for name in tags:
        m = LOCAL_TAG_RE.search(name)
        if not m:
            continue

        slot = int(m.group(1))

        if slot in modules:
            mapping.append({
                "tag": name,
                "slot": slot,
                "module": modules[slot].name
            })

    return mapping


# -----------------------------
# IO Assembly probe (best effort only)
# -----------------------------

def read_io_assemblies(plc, slot: int):
    route = f"1,{slot}"

    assemblies = {
        "input": (0x04, 100),
        "output": (0x04, 101),
        "config": (0x04, 102),
    }

    result = {}

    for name, (cls, inst) in assemblies.items():
        try:
            resp = plc.generic_message(
                service=0x0E,
                class_code=cls,
                instance=inst,
                attribute=3,
                route_path=route
            )

            result[name] = resp.value if resp else None

        except Exception:
            result[name] = None

    return result


# -----------------------------
# Digital Twin Builder
# -----------------------------

def build_digital_twin(ip: str, raw_tags: List[dict]):
    twin = DigitalTwin(controller={"ip": ip})

    with CIPDriver(ip) as plc:

        # 1. chassis scan
        modules = scan_slots_via_echo(plc)
        twin.modules = modules
        
        print(type(modules), list(modules.items())[:2])

        # 2. IO enrichment
        for slot, module in modules.items():
            module.io = read_io_assemblies(plc, slot)

        # 3. tags (Logix side should NOT use CIPDriver)
        # NOTE: this is intentionally separate stack
        with LogixDriver(ip) as lpx:
            raw_tags = lpx.get_tag_list()

    twin.tags = normalize_tags(raw_tags)

    correlations = correlate(twin.tags, twin.modules)

    return twin, correlations


# -----------------------------
# Example usage
# -----------------------------

if __name__ == "__main__":
    ip = "125.215.255.49"

    with LogixDriver(ip) as plc:
        raw_tags = plc.get_tag_list()

    twin, links = build_digital_twin(ip, raw_tags)

    print("Modules:", twin.modules.keys())
    print("Tag Links:", links)

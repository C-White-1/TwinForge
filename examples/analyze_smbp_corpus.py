"""Research inventory of a directory of Machine Expert - Basic ``.smbp`` files.

Reads every ``*.smbp`` under the source directory without rewriting it and
writes a JSON inventory (hashes, versions, CPUs, element and IL counts). This
is a research aid behind docs/architecture/machine-expert-basic-smbp-format.md,
not a production capture implementation.

Example:
    python examples/analyze_smbp_corpus.py reference/machine-expert/smbp         reference/machine-expert/smbp_inventory.json
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

def leaf_fields(element):
    return {c.tag: (c.text or "").strip() for c in element if len(c) == 0}


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("source", type=Path, help="Directory containing .smbp files")
    parser.add_argument("output", type=Path, help="JSON inventory destination")
    args = parser.parse_args()
    files = sorted(args.source.rglob("*.smbp"))
    per_file = []
    element_types = Counter()
    connections = defaultdict(Counter)
    cell_fields = Counter()
    rung_fields = Counter()
    il_opcodes = Counter()
    blocks_span = defaultdict(Counter)
    for path in files:
        raw = path.read_bytes()
        root = ET.fromstring(raw)
        entry = {
            "file": path.relative_to(args.source).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "utf8_bom": raw.startswith(b"\xef\xbb\xbf"),
            "root": root.tag,
            "project_version": root.findtext("ProjectVersion"),
        }
        if root.tag != "ProjectDescriptor":
            entry["children"] = [c.tag for c in root]
            per_file.append(entry)
            continue
        cpu = root.find("HardwareConfiguration/Plc/Cpu")
        entry["management_level"] = root.findtext("ManagementLevel")
        entry["cpu"] = cpu.findtext("Reference") if cpu is not None else None
        entry["extensions"] = [
            e.findtext("Reference") for e in root.iterfind("HardwareConfiguration/Plc/Extensions/*")
        ]
        pous = root.findall("SoftwareConfiguration/Pous/ProgramOrganizationUnits")
        entry["pous"] = [p.findtext("Name") for p in pous]
        rungs = list(root.iter("RungEntity"))
        entry["rungs"] = len(rungs)
        entry["rungs_ladder_selected"] = sum(r.findtext("IsLadderSelected") == "true" for r in rungs)
        entry["rungs_without_cells"] = sum(r.find("LadderElements/LadderEntity") is None for r in rungs)
        for rung in rungs:
            for child in rung:
                rung_fields[child.tag] += 1
            cells = {}
            for cell in rung.iterfind("LadderElements/LadderEntity"):
                fields = leaf_fields(cell)
                for tag in fields:
                    cell_fields[tag] += 1
                kind = fields.get("ElementType")
                element_types[kind] += 1
                connections[kind][fields.get("ChosenConnection")] += 1
                cells[(int(fields["Row"]), int(fields["Column"]))] = kind
            # Width of a cell = distance to the next occupied column in its row.
            for (row, col), kind in cells.items():
                nxt = min((c for r, c in cells if r == row and c > col), default=None)
                if nxt is not None:
                    blocks_span[kind][nxt - col] += 1
            for line in rung.iter("InstructionLineEntity"):
                text = (line.findtext("InstructionLine") or "").strip()
                if text:
                    il_opcodes[text.split()[0]] += 1
        per_file.append(entry)

    inventory = {
        "files": per_file,
        "element_types": dict(element_types.most_common()),
        "chosen_connection_by_element_type": {k: dict(v.most_common()) for k, v in connections.items()},
        "cell_column_span_by_element_type": {k: dict(sorted(v.items())) for k, v in blocks_span.items()},
        "cell_fields": dict(cell_fields.most_common()),
        "rung_fields": dict(rung_fields.most_common()),
        "il_first_tokens": dict(il_opcodes.most_common()),
    }
    args.output.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print(f"{len(files)} files -> {args.output}")


if __name__ == "__main__":
    main()

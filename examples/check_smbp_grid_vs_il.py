"""Check a ladder-grid interpretation of ``.smbp`` rungs against their IL.

Research aid behind docs/architecture/machine-expert-basic-smbp-format.md. For every rung that has both grid cells and IL, the grid
is evaluated as a power-flow network and the IL is interpreted; every output
(coil, operation, function-block input pin) is compared by truth table over
the shared atoms.

Grid hypothesis under test:
- Node (row, k) is the vertical edge between columns k-1 and k; (row, 0) is
  the left rail for every row.
- A cell at (row, col) spans node (row, col) -> (row, col + width).
  Width is 2 for Timer, Counter, Drum, Comparison and Operation, 4 for
  WriteVarBasic, else 1.
- ``Down`` on (r, c) joins node (r, c + width) to node (r + 1, c + width);
  ``Up`` is the mirror. Joined nodes are OR-ed (wired OR).
- A cell without ``Left`` does not read its left node.
- Each function-block pin sits on a fixed row offset for its block type
  (PIN_ROWS). Input pin p of a block at (r, c) reads node (r + row(p), c);
  output pin p drives node (r + row(p), c + width) when the cell starting
  there has ``Left``. The IL lists only wired pins, so IL order does not
  give the row. The block's own ``Right`` is not used: it is missing on
  some blocks whose output is wired.

Usage: python examples/check_smbp_grid_vs_il.py SOURCE_DIR [-v] [--vertical-on-left]
``--vertical-on-left`` runs a deliberately wrong hypothesis (vertical links
at the cell's left node) to show the check can fail.
"""

import argparse
from collections import Counter, defaultdict
import itertools
import json
from pathlib import Path
import random
import re
import xml.etree.ElementTree as ET

# Operation is 2 wide in the output position (07_compare_operate.smbp: c9-c10).
WIDTH = {"Timer": 2, "Counter": 2, "Drum": 2, "Comparison": 2, "Operation": 2, "WriteVarBasic": 4}
OUTPUTS = {"Coil": "ST", "NegativeCoil": "STN", "SetCoil": "S", "ResetCoil": "R"}
# Row offset of each pin within its block, inputs and outputs separately.
# Evidence: Timer and WriteVarBasic from the downloaded samples, Drum from
# ss56/drum-test.smbp, Counter from the user-made 06_counter.smbp (all four
# inputs and three outputs visible in the editor).
PIN_ROWS = {
    "Timer": ({"IN": 0}, {"Q": 0}),
    "Drum": ({"R": 0, "U": 1}, {"F": 0}),
    "WriteVarBasic": ({"Execute": 0}, {"Done": 0}),
    "Counter": ({"R": 0, "S": 1, "CU": 2, "CD": 3}, {"E": 0, "D": 1, "F": 2}),
}
BLOCKS = set(PIN_ROWS)
# Set from --vertical-on-left (negative control).
VERTICAL_ON_LEFT = False


class Unsupported(Exception):
    pass


def norm(expr):
    # IL pads parentheses with spaces; the grid expression does not.
    text = re.sub(r"\s+", " ", expr.strip().strip("[]").strip())
    return re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", text))


# ---------------------------------------------------------------- IL


OP_RE = re.compile(r"^(LD|AND|OR|XOR)(N|R|F)?(\(N?)?$")
WRITES = ("ST", "STN", "S", "R")


def parse_il(lines):
    """Return (program, atoms, outputs, block pins, block outputs)."""
    program, atoms, written = [], set(), set()
    pins, outs = defaultdict(list), defaultdict(list)
    block, after_out = None, False
    for line in (raw.strip() for raw in lines):
        if not line or line == "MULTIFB":
            continue
        if line.startswith("[") or line.startswith("OPER"):
            program.append(("OP", norm(line[4:] if line.startswith("OPER") else line)))
            continue
        if line == ")":
            program.append((")", None))
            continue
        parts = line.split(None, 1)
        op, arg = parts[0], (parts[1].strip() if len(parts) > 1 else "")
        if op == "BLK":
            block, after_out = arg, False
            continue
        if op == "OUT_BLK":
            after_out = True
            continue
        if op == "END_BLK":
            block = None
            continue
        if block and not arg and not after_out and op not in ("MPS", "MRD", "MPP", "N"):
            pins[block].append(op)
            program.append(("PIN", (block, op)))
            continue
        if re.fullmatch(r"RISING\d+", op):
            atoms.add(op)
            program.append(("AND", (op, False)))
            continue
        if op in ("MPS", "MRD", "MPP", "N"):
            program.append((op, None))
            continue
        if op in WRITES:
            written.add(arg)
            program.append((op, arg))
            continue
        if op.startswith("AND(N"):
            op, arg = "AND(", "N " + arg
        m = OP_RE.match(op)
        if not m:
            raise Unsupported("il:" + op)
        base, mod, paren = m.groups()
        neg = mod == "N" or (paren or "").endswith("N")
        if arg.startswith("N "):
            neg, arg = True, arg[2:]
        if arg in ("1", "0"):
            atom = arg
        elif arg.startswith("["):
            atom = "[" + norm(arg) + "]"
        elif block and after_out and not arg.startswith("%"):
            outs[block].append(arg)
            atom = f"out:{block}.{arg}"
        else:
            atom = {"R": "R:", "F": "F:"}.get(mod, "") + arg
        if atom not in ("1", "0") and atom not in written:
            atoms.add(atom)
        program.append((base + ("(" if paren else ""), (atom, neg)))
    # A target written and later read back in the same rung is an internal
    # temporary (seen with MULTIFB, e.g. %MW2009:X0), not a rung output.
    internal, seen_written = set(), set()
    for op, a in program:
        if op in WRITES:
            seen_written.add(a)
        elif op not in ("OP", "PIN", ")") and a and a[0] in seen_written:
            internal.add(a[0])
    outputs = {(op, arg) for op, arg in program if op in WRITES and arg not in internal}
    outputs |= {("OP", arg) for op, arg in program if op == "OP"}
    outputs |= {("PIN",) + arg for op, arg in program if op == "PIN"}
    return program, atoms, outputs, internal, pins, outs


def run_il(program, env):
    acc, mem = False, {}
    paren, mstack, results = [], [], {}

    def val(a):
        atom, neg = a
        if atom in ("1", "0"):
            v = atom == "1"
        else:
            v = mem[atom] if atom in mem else env[atom]
        return not v if neg else v

    for op, arg in program:
        if op == "LD":
            acc = val(arg)
        elif op == "AND":
            acc = acc and val(arg)
        elif op == "OR":
            acc = acc or val(arg)
        elif op == "XOR":
            acc = acc != val(arg)
        elif op.endswith("("):
            paren.append((acc, op[:-1]))
            acc = val(arg)
        elif op == ")":
            prev, kind = paren.pop()
            acc = {"AND": prev and acc, "OR": prev or acc, "XOR": prev != acc}[kind]
        elif op == "N":
            acc = not acc
        elif op == "MPS":
            mstack.append(acc)
        elif op == "MRD":
            acc = mstack[-1]
        elif op == "MPP":
            acc = mstack.pop()
        elif op == "OP":
            results[("OP", arg)] = results.get(("OP", arg), False) or acc
        elif op == "PIN":
            results[("PIN",) + arg] = acc
        else:  # ST STN S R: compare the energising condition
            mem[arg] = acc if op == "ST" else (not acc if op == "STN" else mem.get(arg, False))
            results[(op, arg)] = results.get((op, arg), False) or acc
    return results


# ---------------------------------------------------------------- grid


def width(c):
    return WIDTH.get(c["ElementType"], 1)


def conns(c):
    return {s.strip() for s in c.get("ChosenConnection", "").split(",")}


def cell_atom(c):
    t, d = c["ElementType"], c.get("Descriptor", "")
    if t in ("NormalContact", "NegatedContact", "Xor"):
        return d
    if t == "RisingEdge":
        return "R:" + d
    if t == "FallingEdge":
        return "F:" + d
    if t == "RisingEdgeBlock":
        return "RISING" + d
    if t == "Comparison" and ":=" not in c.get("ComparisonExpression", ""):
        return "[" + norm(c["ComparisonExpression"]) + "]"
    return None


def output_key(c):
    t = c["ElementType"]
    if t in OUTPUTS:
        return (OUTPUTS[t], c.get("Descriptor", ""))
    if t == "Operation":
        return ("OP", norm(c.get("OperationExpression", "")))
    if t == "Comparison" and ":=" in c.get("ComparisonExpression", ""):
        return ("OP", norm(c["ComparisonExpression"]))
    return None


def grid_model(cells, pins, outs):
    atoms, outputs = set(), set()
    for c in cells:
        if cell_atom(c):
            atoms.add(cell_atom(c))
        if output_key(c):
            outputs.add(output_key(c))
        if c["ElementType"] in BLOCKS:
            name = c.get("Descriptor", "")
            in_rows, out_rows = PIN_ROWS[c["ElementType"]]
            for pin in pins.get(name, []):
                if pin not in in_rows:
                    raise Unsupported(f"pin:{c['ElementType']}.{pin}")
                outputs.add(("PIN", name, pin))
            for pin in dict.fromkeys(outs.get(name, [])):
                if pin not in out_rows:
                    raise Unsupported(f"pin:{c['ElementType']}.{pin}")
                if block_output_wired(c, out_rows[pin], cells):
                    atoms.add(f"out:{name}.{pin}")
    return atoms, outputs


def block_output_wired(c, row_offset, cells):
    r, end = int(c["Row"]) + row_offset, int(c["Column"]) + width(c)
    return any(int(n["Row"]) == r and int(n["Column"]) == end and "Left" in conns(n) for n in cells)


def run_grid(cells, pins, outs, env):
    by_end = defaultdict(list)
    vertical = defaultdict(list)
    for c in cells:
        by_end[int(c["Column"]) + width(c)].append(c)
        at = int(c["Column"]) if VERTICAL_ON_LEFT else int(c["Column"]) + width(c)
        vertical[at].append(c)
    rows = max(int(c["Row"]) for c in cells) + 1
    last = max(int(c["Column"]) + width(c) for c in cells)
    node: dict[tuple[int, int], bool] = {}
    results = {}
    for k in range(last + 1):
        raw = {r: True for r in range(rows)} if k == 0 else {}
        for c in by_end.get(k, []):
            r, col = int(c["Row"]), int(c["Column"])
            inp = node.get((r, col), False) if "Left" in conns(c) else False
            out = transfer(c, inp, env, node, cells, pins, outs, results, raw)
            if out is not None:
                raw[r] = raw.get(r, False) or out
        parent = {}

        def find(x):
            while parent.setdefault(x, x) != x:
                x = parent[x]
            return x

        for r in raw:
            find(r)
        for c in vertical.get(k, []):
            r = int(c["Row"])
            if "Down" in conns(c):
                parent[find(r)] = find(r + 1)
            if "Up" in conns(c):
                parent[find(r)] = find(r - 1)
        groups = defaultdict(bool)
        for r in list(parent):
            groups[find(r)] = groups[find(r)] or raw.get(r, False)
        for r in list(parent):
            node[(r, k)] = groups[find(r)]
    return results


def transfer(c, inp, env, node, cells, pins, outs, results, raw):
    """Value the cell drives onto its right node, or None. Records outputs."""
    t = c["ElementType"]
    if t in ("Line", "Short"):
        return True if t == "Short" else inp
    if t in ("NormalContact", "RisingEdge", "FallingEdge", "RisingEdgeBlock"):
        return inp and env[cell_atom(c)]
    if t == "NegatedContact":
        return inp and not env[cell_atom(c)]
    if t == "Xor":
        return inp != env[cell_atom(c)]
    if t == "Not":
        return not inp
    if t == "Comparison":
        if ":=" in c.get("ComparisonExpression", ""):
            key = output_key(c)
            results[key] = results.get(key, False) or inp
            return inp
        return inp and env[cell_atom(c)]
    if t in OUTPUTS or t == "Operation":
        key = output_key(c)
        results[key] = results.get(key, False) or inp
        return inp if "Right" in conns(c) else None
    if t in BLOCKS:
        name, r, col = c.get("Descriptor", ""), int(c["Row"]), int(c["Column"])
        in_rows, out_rows = PIN_ROWS[t]
        for pin in pins.get(name, []):
            results[("PIN", name, pin)] = node.get((r + in_rows[pin], col), False)
        # Outputs may land on rows below the block's own row, so they are
        # written straight into this node column's raw values.
        for pin in dict.fromkeys(outs.get(name, [])):
            if block_output_wired(c, out_rows[pin], cells):
                row = r + out_rows[pin]
                raw[row] = raw.get(row, False) or env[f"out:{name}.{pin}"]
        return None
    if t in ("VerticalLine", "None"):
        return None
    raise Unsupported("cell:" + t)


# ---------------------------------------------------------------- compare


def envs(atoms):
    atoms = sorted(atoms)
    if len(atoms) <= 12:
        for bits in itertools.product((False, True), repeat=len(atoms)):
            yield dict(zip(atoms, bits))
    else:
        rnd = random.Random(0)
        for _ in range(4096):
            yield {a: rnd.random() < 0.5 for a in atoms}


def main():
    global VERTICAL_ON_LEFT
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("source", type=Path, help="Directory containing .smbp files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print every mismatch")
    parser.add_argument("--vertical-on-left", action="store_true",
                        help="Run the deliberately wrong hypothesis as a negative control")
    args = parser.parse_args()
    VERTICAL_ON_LEFT = args.vertical_on_left
    verbose = args.verbose
    outcome, reasons, features = Counter(), Counter(), Counter()
    mismatches = []
    for path in sorted(args.source.rglob("*.smbp")):
        root = ET.parse(path).getroot()
        if root.tag != "ProjectDescriptor":
            continue
        for index, rung in enumerate(root.iter("RungEntity")):
            cells = [{c.tag: (c.text or "").strip() for c in le if len(c) == 0}
                     for le in rung.iterfind("LadderElements/LadderEntity")]
            cells = [c for c in cells if c["ElementType"] != "None"]
            lines = [il.findtext("InstructionLine") or "" for il in rung.iter("InstructionLineEntity")]
            if not cells:
                outcome["il-only"] += 1
                continue
            where = f"{path.relative_to(args.source).as_posix()} rung {index}"
            try:
                program, iatoms, ikeys, internal, pins, outs = parse_il(lines)
                gatoms, gkeys = grid_model(cells, pins, outs)
            except Unsupported as exc:
                outcome["unsupported"] += 1
                reasons[str(exc)] += 1
                continue
            if gkeys != ikeys or gatoms != iatoms:
                outcome["mismatch"] += 1
                mismatches.append({"rung": where, "kind": "keys/atoms",
                                   "grid_keys": sorted(map(str, gkeys)), "il_keys": sorted(map(str, ikeys)),
                                   "grid_atoms": sorted(gatoms), "il_atoms": sorted(iatoms), "il": lines})
                continue
            bad = None
            for env in envs(gatoms):
                g, i = run_grid(cells, pins, outs, env), run_il(program, env)
                for key in gkeys:
                    if g.get(key, False) != i.get(key, False):
                        bad = {"output": str(key), "env": env, "grid": g.get(key, False), "il": i.get(key, False)}
                        break
                if bad:
                    break
            if bad:
                outcome["mismatch"] += 1
                mismatches.append({"rung": where, "kind": "truth", **bad, "il_text": lines})
                continue
            outcome["match"] += 1
            at = {(int(c["Row"]), int(c["Column"])): c for c in cells}
            for (r, col), c in at.items():
                n = at.get((r, col + width(c)))
                if n is not None and ("Right" in conns(c)) != ("Left" in conns(n)):
                    features[f"Right/Left disagree after {c['ElementType']}"] += 1
            kinds = {c["ElementType"] for c in cells}
            if any({"Up", "Down"} & conns(c) for c in cells):
                features["has vertical links"] += 1
            if kinds & BLOCKS:
                features["has function block"] += 1
            if any(int(c["Row"]) > 0 and c["ElementType"] in BLOCKS for c in cells):
                features["block below row 0"] += 1
            if any(c["ElementType"] in BLOCKS and len(pins.get(c.get("Descriptor"), [])) > 1 for c in cells):
                features["block with >1 input pin"] += 1
            if any(c["ElementType"] in BLOCKS and len(set(outs.get(c.get("Descriptor"), []))) > 1 for c in cells):
                features["block with >1 wired output"] += 1
            if any(c["ElementType"] in BLOCKS and any(
                    PIN_ROWS[c["ElementType"]][0][p] != i
                    for i, p in enumerate(pins.get(c.get("Descriptor"), []))) for c in cells):
                features["input pin row differs from IL position"] += 1
            if internal:
                features["IL internal temporary (MULTIFB)"] += 1
            if "RisingEdgeBlock" in kinds:
                features["RisingEdgeBlock"] += 1
            if len(gatoms) > 12:
                features["sampled (>12 atoms)"] += 1
    print(dict(outcome))
    print("unsupported reasons:", dict(reasons))
    print("features among matches:", dict(features))
    for m in mismatches if verbose else mismatches[:5]:
        print(json.dumps(m))


if __name__ == "__main__":
    main()

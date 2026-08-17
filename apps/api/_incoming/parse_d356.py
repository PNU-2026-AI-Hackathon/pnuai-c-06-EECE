#!/usr/bin/env python3
"""
Prefab — IPC-D-356 netlist parser (D1 prototype)

IPC-D-356 fixed-width record layout (0-indexed):
  [0:3]    record type   317=through-hole/via, 327=SMT(single-sided)
  [3:17]   net name (14)
  [20:26]  reference designator (6)
  [26]     '-' separator
  [27:31]  pin name (4)   <-- TRUNCATED TO 4 CHARS. critical limitation.
  [32:37]  drill  'D'+4
  [37]     plating P/U
  [38:41]  access 'A00'..'A03'
  [41:49]  X 'X'+sign+6   (0.0001 in)
  [49:57]  Y 'Y'+sign+6
  [57:62]  X size
  [62:67]  Y size
  [67:71]  rotation
"""
import sys, re
from collections import defaultdict, OrderedDict

REC_TYPES = {"317": "THRU/VIA", "327": "SMT"}


def parse(path):
    nets = defaultdict(list)      # net -> [(refdes, pin, rec)]
    parts = defaultdict(set)      # refdes -> {pins}
    meta = []
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.rstrip("\n")
        if not line:
            continue
        if line.startswith("P "):
            meta.append(line.strip())
            continue
        if line.startswith("999"):
            break
        rec = line[0:3]
        if rec not in REC_TYPES:
            continue

        net = line[3:17].strip()
        refdes = line[20:26].strip()
        pin = line[27:31].strip() if len(line) > 27 else ""

        m = re.search(r"X([+-]\d{6})Y([+-]\d{6})", line)
        xy = (int(m.group(1)) / 10000, int(m.group(2)) / 10000) if m else (None, None)

        if refdes.upper() == "VIA" or not refdes:
            nets[net].append(("VIA", "", rec, xy))
            continue

        nets[net].append((refdes, pin, rec, xy))
        if pin:
            parts[refdes].add(pin)
    return nets, parts, meta


def report(nets, parts, meta):
    print("=" * 74)
    print("IPC-D-356 PARSE RESULT")
    print("=" * 74)
    print("header:", "; ".join(meta))
    print()

    real = {n: c for n, c in nets.items() if n and n != "N/C"}
    print(f"nets: {len(real)} (+ N/C bucket)   parts: {len(parts)}")
    print()

    print("-" * 74)
    print("NETLIST  (VIA entries collapsed)")
    print("-" * 74)
    for net in sorted(real, key=lambda n: (-len([p for p in nets[n] if p[0] != 'VIA']), n)):
        conns = [(r, p) for r, p, _, _ in nets[net] if r != "VIA"]
        vias = sum(1 for r, _, _, _ in nets[net] if r == "VIA")
        seen, uniq = set(), []
        for c in conns:
            if c not in seen:
                seen.add(c); uniq.append(c)
        tag = f"  [+{vias} via]" if vias else ""
        print(f"{net:<18} ({len(uniq)}){tag}")
        print(f"    {', '.join(f'{r}.{p}' for r, p in uniq)}")
    print()

    print("-" * 74)
    print("PARTS  (pin names as exported)")
    print("-" * 74)
    for ref in sorted(parts):
        pins = sorted(parts[ref])
        print(f"{ref:<6} {len(pins):>2} pins : {', '.join(pins)}")
    print()

    # ---- truncation check -------------------------------------------------
    print("-" * 74)
    print("!! PIN NAME TRUNCATION CHECK")
    print("-" * 74)
    suspicious = []
    for ref, pins in parts.items():
        for p in pins:
            if len(p) == 4 and (p.endswith("_") or p[-1].isdigit() is False):
                suspicious.append(f"{ref}.{p}")
    print(f"pins at the 4-char field limit: {len([p for ps in parts.values() for p in ps if len(p)==4])}")
    print("examples of ambiguous / clipped names:")
    for s in sorted(set(suspicious))[:14]:
        print(f"    {s}")
    print()
    print("=> IPC-D-356 CANNOT give exact GPIO numbers. Topology only.")
    print("=> A BOM export + module pinout DB is REQUIRED for R1/R2/R3/R5.")


if __name__ == "__main__":
    nets, parts, meta = parse(sys.argv[1] if len(sys.argv) > 1 else "board.d356")
    report(nets, parts, meta)

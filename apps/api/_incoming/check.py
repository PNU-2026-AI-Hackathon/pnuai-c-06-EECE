#!/usr/bin/env python3
"""
Prefab — rule engine prototype (D1)

Design principle under test:
    TOPOLOGY raises the question.  DATASHEET answers it.
    -> deterministic code flags the cross-domain net (no LLM needed)
    -> LLM is only called to CLEAR the flag by reading the part's datasheet

Rules implemented here (both need ZERO datasheet access to fire):
    R11  net name claims a voltage domain that its source part contradicts
    R12  signal crosses from a higher supply domain into a lower one
         with no series element in the path
"""
import re, sys
from collections import defaultdict
from parse_d356 import parse

GND_PAT = re.compile(r"^(GND|VSS|AGND|DGND)", re.I)
SUPPLY_PIN = re.compile(r"^(VCC|VDD|VIN|VBUS|V\+|5V|3V3|3\.3V|VDDIO)", re.I)
# voltage token anywhere in a name: 5V, 3V3, 1V8, 12V
VOLT_TOK = re.compile(r"(?<![A-Z0-9])(\d{1,2})V(\d)?(?![A-Z0-9])", re.I)


def volts(name):
    m = VOLT_TOK.search(name or "")
    if not m:
        return None
    whole, frac = m.group(1), m.group(2)
    return float(f"{whole}.{frac}") if frac else float(whole)


def build(nets):
    """part -> {pin: net}, and XY per (part,pin) for pad clustering"""
    part_pins, xy = defaultdict(dict), {}
    for net, conns in nets.items():
        for ref, pin, rec, coord in conns:
            if ref == "VIA":
                continue
            key = (ref, pin, coord)
            part_pins[ref][key] = net
            xy[key] = coord
    return part_pins


def cluster_pads(part_pins, ref, tol=0.05):
    """Parts whose pins all export the same name (e.g. K1 'pad-') are split
    into physical groups by X coordinate. Geometry recovers what names lost."""
    groups = defaultdict(list)
    for (r, pin, coord), net in part_pins[ref].items():
        x = coord[0] if coord[0] is not None else 0.0
        placed = False
        for gx in list(groups):
            if abs(gx - x) < tol * 20:
                groups[gx].append((pin, net)); placed = True; break
        if not placed:
            groups[x].append((pin, net))
    return groups


def supply_domain(part_pins, ref):
    """Return (io_volts, basis, confidence)."""
    pins = part_pins[ref]
    named = {}
    for (r, pin, coord), net in pins.items():
        named.setdefault(pin, set()).add(net)

    # a part exposing an explicit 3V3 rail pin -> its IO is that rail
    for pin, nset in named.items():
        if re.match(r"^(3V3|3\.3V|VDDIO)", pin, re.I):
            for n in nset:
                v = volts(n)
                if v:
                    return v, f"{ref}.{pin} -> {n}", "high"

    # otherwise: whatever rail feeds VCC/VDD/VIN
    for pin, nset in named.items():
        if SUPPLY_PIN.match(pin):
            for n in nset:
                v = volts(n)
                if v:
                    return v, f"{ref}.{pin} -> {n}", "high"

    # unnamed pads (K1 'pad-'): use the X-cluster that also holds this part's
    # supply + ground pair
    groups = cluster_pads(part_pins, ref)
    for gx, members in groups.items():
        rails = [volts(n) for _, n in members if volts(n) and not GND_PAT.match(n)]
        has_gnd = any(GND_PAT.match(n) for _, n in members)
        if rails and has_gnd:
            return max(rails), f"{ref} pad cluster @X{gx:+.4f} (rail+GND)", "inferred"
    return None, "unknown", "none"


def main(path):
    nets, parts, meta = parse(path)
    part_pins = build(nets)

    dom = {}
    print("=" * 74)
    print("SUPPLY DOMAIN INFERENCE")
    print("=" * 74)
    for ref in sorted(part_pins):
        if re.match(r"^(R|C|L|D|FB)\d", ref):
            continue
        v, basis, conf = supply_domain(part_pins, ref)
        dom[ref] = v
        print(f"  {ref:<5} io={str(v)+'V':<6} [{conf:<8}] {basis}")
    print()

    findings = []
    signal_nets = {n: c for n, c in nets.items()
                   if n and n != "N/C" and not GND_PAT.match(n) and
                   not (volts(n) and len({r for r, _, _, _ in c if r != 'VIA'}) > 4)}

    # ---------------- R11 : net name vs source domain --------------------
    for net, conns in signal_nets.items():
        claimed = volts(net)
        if claimed is None:
            continue
        refs = sorted({r for r, _, _, _ in conns if r != "VIA"})
        for ref in refs:
            d = dom.get(ref)
            if d and abs(d - claimed) > 0.15:
                findings.append((
                    "R11", "WARN", net,
                    f"net name claims {claimed}V but {ref} runs on {d}V",
                    f"{', '.join(refs)}"))

    # ---------------- R12 : cross-domain signal, no series part ----------
    for net, conns in signal_nets.items():
        refs = sorted({r for r, _, _, _ in conns if r != "VIA"})
        actives = [r for r in refs if r in dom and dom[r]]
        if len(actives) < 2:
            continue
        hi, lo = max(actives, key=lambda r: dom[r]), min(actives, key=lambda r: dom[r])
        if dom[hi] - dom[lo] > 0.15:
            series = [r for r in refs if re.match(r"^(R|D)\d", r)]
            findings.append((
                "R12", "FAIL", net,
                f"{hi} ({dom[hi]}V) drives {lo} ({dom[lo]}V) directly"
                + (f"; passives on net: {','.join(series)} (pull-up, not series)" if series
                   else "; NO series resistor / divider / level shifter"),
                f"{', '.join(refs)}"))

    print("=" * 74)
    print("FINDINGS")
    print("=" * 74)
    if not findings:
        print("  none")
    for rule, sev, net, msg, ctx in findings:
        print(f"\n[{sev}] {rule}  net: {net}")
        print(f"       {msg}")
        print(f"       on net: {ctx}")
        print(f"       -> NEXT: read datasheet of the {sev=='FAIL' and 'driving' or 'source'} "
              f"part to get Voh. Flag clears only if Voh <= 3.6V.")
    print()
    print("=" * 74)
    print(f"{len(findings)} finding(s). Zero datasheet lookups used to get here.")
    print("=" * 74)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "board.d356")

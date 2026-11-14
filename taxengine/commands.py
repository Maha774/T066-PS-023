"""Command file processor: COMPUTE / PRINT_SHEET / PRINT_COMPARISON, in file order (BR-41)."""
from datetime import date

from .engine import compute, recommend


class RunResult:
    def __init__(self):
        self.sheets = []        # Sheet rows, in PRINT_SHEET order
        self.comparisons = []   # dict rows, in PRINT_COMPARISON order
        self.rejections = []    # (source_file, record_id, reason)


def run_commands(ds, commands_path) -> RunResult:
    out = RunResult()
    out.rejections.extend(ds.rejections)
    computed = {}  # taxpayer_id -> (filing_date, {"OLD": Sheet, "NEW": Sheet})

    with open(commands_path, encoding="utf-8-sig") as f:
        lines = f.read().splitlines()

    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        name, args = parts[0].upper(), parts[1:]
        ref = f"line {number}"

        def reject(reason):
            out.rejections.append(("commands.txt", ref, reason))

        if name == "COMPUTE":
            if len(args) != 2 or not args[0] or not args[1]:
                reject("COMPUTE needs taxpayer_id|filing_date")
            elif args[0] not in ds.taxpayers:
                reject(f"unknown taxpayer_id {args[0]}")
            else:
                try:
                    filing = date.fromisoformat(args[1])
                except ValueError:
                    reject(f"invalid filing_date '{args[1]}'")
                    continue
                # a later COMPUTE replaces the earlier result
                computed[args[0]] = (filing, {r: compute(ds, args[0], r, filing) for r in ("OLD", "NEW")})
        elif name == "PRINT_SHEET":
            if len(args) != 2 or args[1].upper() not in ("OLD", "NEW"):
                reject("PRINT_SHEET needs taxpayer_id|OLD or NEW")
            elif args[0] not in computed:
                reject(f"{args[0]} has not been computed yet")
            else:
                out.sheets.append(computed[args[0]][1][args[1].upper()])
        elif name == "PRINT_COMPARISON":
            if len(args) != 1 or not args[0]:
                reject("PRINT_COMPARISON needs taxpayer_id")
            elif args[0] not in computed:
                reject(f"{args[0]} has not been computed yet")
            else:
                filing, sheets = computed[args[0]]
                regime, saving = recommend(sheets["OLD"], sheets["NEW"])
                out.comparisons.append({
                    "taxpayer_id": args[0], "filing_date": filing.isoformat(),
                    "old_total_tax": sheets["OLD"].total_tax, "new_total_tax": sheets["NEW"].total_tax,
                    "old_net_payable": sheets["OLD"].net_payable, "new_net_payable": sheets["NEW"].net_payable,
                    "recommended_regime": regime, "saving": saving})
        else:
            reject(f"unknown command {name}")
    return out

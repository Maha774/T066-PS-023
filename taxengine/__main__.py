"""Run:  python -m taxengine [data_dir] [--out output_dir] [--quiet]"""
import argparse
from pathlib import Path

from .commands import run_commands
from .loaders import load_dataset
from .report import render_comparison, render_sheet, write_outputs


def main(argv=None):
    ap = argparse.ArgumentParser(description="PS-023 income tax computation engine")
    ap.add_argument("data_dir", nargs="?", default="sample_data")
    ap.add_argument("--commands", help="command file (default: <data_dir>/commands.txt)")
    ap.add_argument("--out", default="output")
    ap.add_argument("--quiet", action="store_true", help="only write the CSV files")
    args = ap.parse_args(argv)

    ds = load_dataset(args.data_dir)
    result = run_commands(ds, args.commands or Path(args.data_dir) / "commands.txt")
    write_outputs(result, args.out)
    if not args.quiet:
        for s in result.sheets:
            print(render_sheet(s), end="\n\n")
        for c in result.comparisons:
            print(render_comparison(c), end="\n\n")
    print(f"Done: {len(result.sheets)} sheets, {len(result.comparisons)} comparisons, "
          f"{len(result.rejections)} rejections -> {args.out}/")


if __name__ == "__main__":
    main()

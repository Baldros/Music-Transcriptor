from __future__ import annotations

import argparse
import json
from pathlib import Path

from .tg_writer import ContractValidationError, write_tg


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a TuxGuitar .tg file from a MelodyScoreContract JSON file."
    )
    parser.add_argument("input", type=Path, help="Path to the contract JSON file.")
    parser.add_argument("output", type=Path, help="Path to the output .tg file.")
    args = parser.parse_args()

    try:
        with args.input.open("r", encoding="utf-8") as fp:
            contract = json.load(fp)
        write_tg(contract, args.output)
    except ContractValidationError as exc:
        parser.exit(2, f"contract validation failed: {exc}\n")

    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


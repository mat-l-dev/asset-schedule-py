"""Command-line interface with JSON on stdout and errors on stderr."""

import argparse
from collections.abc import Sequence
from dataclasses import asdict
import json

from . import __version__
from .schedule import straight_line_schedule


def main(argv: Sequence[str] | None = None) -> int:
    """Write one JSON document; argparse exits with status 2 on invalid input."""
    parser = argparse.ArgumentParser(
        prog="asset-schedule",
        description=(
            "Calculate full-month straight-line depreciation in integer minor "
            "units. Extra minor units are allocated to the earliest periods."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--cost-minor", type=int, required=True)
    parser.add_argument("--residual-minor", type=int, required=True)
    parser.add_argument("--periods", type=int, required=True)
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--start-month", type=int, required=True)
    parser.add_argument("--compact", action="store_true", help="omit indentation")
    args = parser.parse_args(argv)

    try:
        schedule = straight_line_schedule(
            cost_minor=args.cost_minor,
            residual_minor=args.residual_minor,
            periods=args.periods,
            start_year=args.start_year,
            start_month=args.start_month,
        )
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    document = {
        "schema_version": 1,
        "method": "straight-line",
        "remainder_allocation": "earliest-periods",
        "inputs": {
            "cost_minor": args.cost_minor,
            "residual_minor": args.residual_minor,
            "periods": args.periods,
            "start_year": args.start_year,
            "start_month": args.start_month,
        },
        "total_depreciation_minor": args.cost_minor - args.residual_minor,
        "schedule": [asdict(row) for row in schedule],
    }
    print(
        json.dumps(
            document,
            indent=None if args.compact else 2,
            separators=(",", ":") if args.compact else None,
        )
    )
    return 0

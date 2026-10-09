"""Ejemplo mínimo: tres meses completos y valores monetarios enteros."""

from dataclasses import asdict
import json

from asset_schedule import straight_line_schedule

schedule = straight_line_schedule(
    cost_minor=100_000,
    residual_minor=10_000,
    periods=3,
    start_year=2026,
    start_month=11,
)

print(json.dumps([asdict(row) for row in schedule], indent=2))

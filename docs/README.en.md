# asset-schedule-py

Monthly straight-line depreciation schedules with integer arithmetic, a typed API, and a JSON command-line interface. No runtime dependencies.

[Documentación en español](../README.md)

## Scope

The library performs one generic calculation: distribute an asset's depreciable amount over an explicit number of full months. Cost, residual value, and every result use the same caller-selected monetary minor unit. For example, `100_000` may mean 1,000.00 in a two-decimal currency; no currency or decimal scale is inferred.

It does not determine useful lives, tax rates, or recognition policies. It does not calculate partial months, impairment, revaluations, estimate changes, disposals, or journal entries. Its output does not establish accounting, tax, or legal compliance.

## Local installation

Python 3.12 or later is required. The included version is `0.1.0`. These commands install this repository's code; they do not assume a PyPI release.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
```

On Windows, activate with `.venv\Scripts\Activate.ps1`. With uv:

```bash
uv venv
uv pip install .
```

Package builds use setuptools. It is not a runtime dependency.

## API

```python
from asset_schedule import straight_line_schedule

rows = straight_line_schedule(
    cost_minor=100_000,
    residual_minor=10_000,
    periods=3,
    start_year=2026,
    start_month=11,
)

assert [row.depreciation_minor for row in rows] == [30_000, 30_000, 30_000]
assert rows[-1].accumulated_depreciation_minor == 90_000
assert rows[-1].carrying_value_minor == 10_000
assert (rows[-1].year, rows[-1].month) == (2027, 1)
```

All arguments are required and keyword-only. The function returns a tuple of immutable `ScheduleRow` objects:

| Field | Meaning |
| --- | --- |
| `period` | One-based period number |
| `year`, `month` | Calendar month for this period |
| `depreciation_minor` | This period's depreciation |
| `accumulated_depreciation_minor` | Cumulative depreciation including this period |
| `carrying_value_minor` | Cost less cumulative depreciation at period end |

The first row corresponds to the supplied start month. Each row represents a full month regardless of its day count. The result stops after exactly `periods` rows and does not produce entries beyond the useful life.

### Remainder allocation

The calculation is `base, remainder = divmod(cost_minor - residual_minor, periods)`. The first `remainder` periods receive `base + 1`; the rest receive `base`. No floating-point arithmetic is used.

- A depreciable amount of 10 over 3 months produces `4, 3, 3`.
- An amount of 11 over 3 months produces `4, 4, 3`.
- One minor unit over 4 months produces `1, 0, 0, 0`.

Results are deterministic. Period amounts differ by at most one minor unit. Their total is exactly `cost_minor - residual_minor`, the final carrying value is exactly `residual_minor`, and carrying value never falls below residual value. Equal cost and residual values produce the requested months with zero depreciation.

### Validation and limits

- Every argument must have Python's built-in `int` type. `bool`, `float`, `Decimal`, strings, and `int` subclasses are rejected; values are never implicitly converted.
- Cost and residual value must be nonnegative; residual value cannot exceed cost.
- `periods` must be positive and `start_month` must be between 1 and 12.
- Both the first and last month must fall between January of year 1 and December of year 9999. The complete horizon is validated before allocating rows.
- Invalid types raise `TypeError`; invalid ranges raise `ValueError`.
- The API uses arbitrary-precision integers. The CLI emits JSON integers, subject to the interpreter's decimal conversion limit. JSON consumers must also preserve large integers; JavaScript `Number` can lose precision above `2**53 - 1`.
- The complete schedule is materialized. Time and memory are linear in the period count; the calendar supports at most 119,988 months.

## CLI

```bash
asset-schedule \
  --cost-minor 100000 \
  --residual-minor 10000 \
  --periods 3 \
  --start-year 2026 \
  --start-month 11
```

`python -m asset_schedule` is equivalent. All amounts and parameters must be supplied as integers; `1.0` and `true` are invalid.

Output is one JSON document containing `schema_version`, `method`, `remainder_allocation`, `inputs`, `total_depreciation_minor`, and `schedule`. See the [complete output example](../examples/schedule.json). `schema_version` is `1`, `method` is `straight-line`, and `remainder_allocation` is `earliest-periods`.

Additional options:

- `--compact`: single-line JSON
- `--help`: usage help
- `--version`: package version

Successful calculations write JSON to stdout and exit with code 0. Invalid input produces a stderr diagnostic, empty stdout, and exit code 2. Help and version output are text rather than JSON.

## Development and verification

After installing the package:

```bash
python -m unittest discover -s tests -v
python examples/basic.py
```

To test directly from source without installing the package or dependencies:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python examples/basic.py
```

The standard-library `unittest` suite covers rounding, year rollover, calendar boundaries, deterministic replay, large integers, rejected input, the CLI, and invariants across an exhaustive small domain of 10,710 schedules.

Build a distribution with uv:

```bash
uv build
```

No CI workflows are included. Checks run locally without using GitHub Actions minutes.

## Status and license

This is an initial functional version with a deliberately limited scope. See the [changelog](../CHANGELOG.md).

A distribution license is pending the rights holder's decision. This repository does not yet declare an open-source license.

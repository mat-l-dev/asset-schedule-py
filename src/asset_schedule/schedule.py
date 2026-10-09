"""Pure calculations for full-month, straight-line depreciation schedules."""

from dataclasses import dataclass

_LAST_MONTH_INDEX = 9999 * 12 - 1


@dataclass(frozen=True, slots=True)
class ScheduleRow:
    """One full month; cumulative values and carrying value are month-end."""

    period: int
    year: int
    month: int
    depreciation_minor: int
    accumulated_depreciation_minor: int
    carrying_value_minor: int


def _require_integer(name: str, value: int) -> None:
    # bool is a subclass of int, but is not an amount, period, or date part.
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer (bool is not accepted)")


def straight_line_schedule(
    *,
    cost_minor: int,
    residual_minor: int,
    periods: int,
    start_year: int,
    start_month: int,
) -> tuple[ScheduleRow, ...]:
    """Return an immutable schedule of exactly ``periods`` full months.

    Amounts are nonnegative, built-in integers in a caller-defined minor unit.
    All five arguments require built-in ``int`` values; no coercion is applied.
    ``residual_minor`` cannot exceed ``cost_minor``. ``periods`` is positive.

    The depreciable amount is divided by ``periods`` with ``divmod``. The
    first remainder-count periods receive one additional minor unit. This
    makes the total exact and each period's expense differ by at most one.

    The first row is the specified start month. All months must fit within
    years 1 through 9999. The result stops at the end of the useful life.
    No tax rate, currency, day proration, or legal treatment is inferred.

    Raises:
        TypeError: Any argument is not a built-in integer (including bool).
        ValueError: An amount, period count, or calendar range is invalid.
    """
    for name, value in (
        ("cost_minor", cost_minor),
        ("residual_minor", residual_minor),
        ("periods", periods),
        ("start_year", start_year),
        ("start_month", start_month),
    ):
        _require_integer(name, value)

    if cost_minor < 0:
        raise ValueError("cost_minor must be nonnegative")
    if residual_minor < 0:
        raise ValueError("residual_minor must be nonnegative")
    if residual_minor > cost_minor:
        raise ValueError("residual_minor must not exceed cost_minor")
    if periods <= 0:
        raise ValueError("periods must be greater than zero")
    if not 1 <= start_year <= 9999:
        raise ValueError("start_year must be between 1 and 9999")
    if not 1 <= start_month <= 12:
        raise ValueError("start_month must be between 1 and 12")

    first_month_index = (start_year - 1) * 12 + start_month - 1
    if first_month_index + periods - 1 > _LAST_MONTH_INDEX:
        raise ValueError("the schedule must end on or before December 9999")

    base, remainder = divmod(cost_minor - residual_minor, periods)
    accumulated = 0
    rows: list[ScheduleRow] = []
    for offset in range(periods):
        depreciation = base + (1 if offset < remainder else 0)
        accumulated += depreciation
        year_index, month_index = divmod(first_month_index + offset, 12)
        rows.append(
            ScheduleRow(
                period=offset + 1,
                year=year_index + 1,
                month=month_index + 1,
                depreciation_minor=depreciation,
                accumulated_depreciation_minor=accumulated,
                carrying_value_minor=cost_minor - accumulated,
            )
        )
    return tuple(rows)

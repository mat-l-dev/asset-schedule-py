"""Behavioral tests and bounded exhaustive checks, without external tools."""

from dataclasses import FrozenInstanceError, asdict
from decimal import Decimal
from fractions import Fraction
import unittest

from asset_schedule import ScheduleRow, straight_line_schedule


class ScheduleTests(unittest.TestCase):
    def schedule(self, **overrides):
        inputs = {
            "cost_minor": 100_000,
            "residual_minor": 10_000,
            "periods": 3,
            "start_year": 2026,
            "start_month": 11,
        }
        inputs.update(overrides)
        return straight_line_schedule(**inputs)

    def test_basic_example(self):
        self.assertEqual(
            self.schedule(),
            (
                ScheduleRow(1, 2026, 11, 30_000, 30_000, 70_000),
                ScheduleRow(2, 2026, 12, 30_000, 60_000, 40_000),
                ScheduleRow(3, 2027, 1, 30_000, 90_000, 10_000),
            ),
        )

    def test_remainder_goes_to_earliest_periods(self):
        rows = self.schedule(cost_minor=10, residual_minor=0, periods=3)
        self.assertEqual([r.depreciation_minor for r in rows], [4, 3, 3])
        rows = self.schedule(cost_minor=11, residual_minor=0, periods=3)
        self.assertEqual([r.depreciation_minor for r in rows], [4, 4, 3])

    def test_single_period(self):
        self.assertEqual(
            self.schedule(periods=1),
            (ScheduleRow(1, 2026, 11, 90_000, 90_000, 10_000),),
        )

    def test_one_remaining_minor_unit(self):
        rows = self.schedule(cost_minor=101, residual_minor=100, periods=4)
        self.assertEqual([r.depreciation_minor for r in rows], [1, 0, 0, 0])
        self.assertEqual([r.carrying_value_minor for r in rows], [100] * 4)

    def test_zero_cost(self):
        rows = self.schedule(cost_minor=0, residual_minor=0)
        self.assertEqual([r.depreciation_minor for r in rows], [0] * 3)
        self.assertEqual([r.carrying_value_minor for r in rows], [0] * 3)

    def test_cost_equal_to_residual(self):
        rows = self.schedule(cost_minor=100, residual_minor=100)
        self.assertEqual([r.depreciation_minor for r in rows], [0] * 3)
        self.assertEqual([r.accumulated_depreciation_minor for r in rows], [0] * 3)
        self.assertEqual([r.carrying_value_minor for r in rows], [100] * 3)

    def test_year_rollover(self):
        rows = self.schedule(start_month=12, periods=14)
        self.assertEqual((rows[0].year, rows[0].month), (2026, 12))
        self.assertEqual((rows[1].year, rows[1].month), (2027, 1))
        self.assertEqual((rows[-1].year, rows[-1].month), (2028, 1))

    def test_leap_year_does_not_change_full_month_expense(self):
        leap = self.schedule(start_year=2024, start_month=1)
        normal = self.schedule(start_year=2025, start_month=1)
        self.assertEqual([r.month for r in leap], [1, 2, 3])
        self.assertEqual(
            [r.depreciation_minor for r in leap],
            [r.depreciation_minor for r in normal],
        )

    def test_replay_is_equal_and_independent(self):
        first = self.schedule(cost_minor=104, residual_minor=2, periods=7)
        second = self.schedule(cost_minor=104, residual_minor=2, periods=7)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first[0], second[0])

    def test_rows_and_container_are_immutable(self):
        rows = self.schedule()
        self.assertIsInstance(rows, tuple)
        with self.assertRaises(FrozenInstanceError):
            rows[0].depreciation_minor = 0

    def test_result_stops_at_useful_life(self):
        rows = self.schedule(periods=2)
        self.assertEqual([r.period for r in rows], [1, 2])
        self.assertEqual((rows[-1].year, rows[-1].month), (2026, 12))
        self.assertEqual(rows[-1].carrying_value_minor, 10_000)
        with self.assertRaises(IndexError):
            _ = rows[2]

    def test_large_integer_amounts_are_exact(self):
        cost, residual = 10**1000 + 29, 10**800 + 1
        rows = self.schedule(cost_minor=cost, residual_minor=residual, periods=13)
        self.assertEqual(sum(r.depreciation_minor for r in rows), cost - residual)
        self.assertEqual(rows[-1].carrying_value_minor, residual)
        self.assertEqual(rows[-1].accumulated_depreciation_minor, cost - residual)

    def test_earliest_supported_month(self):
        rows = self.schedule(start_year=1, start_month=1)
        self.assertEqual((rows[0].year, rows[0].month), (1, 1))

    def test_latest_supported_month(self):
        rows = self.schedule(start_year=9999, start_month=12, periods=1)
        self.assertEqual((rows[0].year, rows[0].month), (9999, 12))

    def test_end_at_calendar_limit(self):
        rows = self.schedule(start_year=9999, start_month=11, periods=2)
        self.assertEqual((rows[-1].year, rows[-1].month), (9999, 12))

    def test_full_calendar_horizon(self):
        periods = 9999 * 12
        rows = self.schedule(
            cost_minor=periods, residual_minor=0, periods=periods,
            start_year=1, start_month=1,
        )
        self.assertEqual(len(rows), periods)
        self.assertEqual(rows[-1], ScheduleRow(periods, 9999, 12, 1, periods, 0))

    def test_invalid_numeric_ranges(self):
        cases = (
            ("cost_minor", -1, "cost_minor"),
            ("residual_minor", -1, "residual_minor"),
            ("residual_minor", 100_001, "must not exceed"),
            ("periods", 0, "periods"),
            ("periods", -1, "periods"),
            ("start_year", 0, "start_year"),
            ("start_year", -1, "start_year"),
            ("start_year", 10_000, "start_year"),
            ("start_month", 0, "start_month"),
            ("start_month", -1, "start_month"),
            ("start_month", 13, "start_month"),
        )
        for name, value, message in cases:
            with self.subTest(name=name, value=value):
                with self.assertRaisesRegex(ValueError, message):
                    self.schedule(**{name: value})

    def test_calendar_overflow_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "December 9999"):
            self.schedule(start_year=9999, start_month=12, periods=2)

    def test_huge_period_count_is_rejected_before_allocation(self):
        with self.assertRaisesRegex(ValueError, "December 9999"):
            self.schedule(periods=10**1000)

    def test_non_integer_inputs_are_rejected_for_every_argument(self):
        class IntegerSubclass(int):
            pass

        invalid = (
            True, False, 1.0, float("nan"), float("inf"), "1", None,
            Decimal("1"), Fraction(1, 1), 1 + 0j, [1], IntegerSubclass(1),
        )
        for name in ("cost_minor", "residual_minor", "periods", "start_year", "start_month"):
            for value in invalid:
                with self.subTest(name=name, value=value):
                    with self.assertRaisesRegex(TypeError, f"{name} must be an integer"):
                        self.schedule(**{name: value})

    def test_arguments_are_keyword_only(self):
        with self.assertRaises(TypeError):
            straight_line_schedule(100, 0, 3, 2026, 1)

    def test_no_argument_is_implicitly_defaulted(self):
        with self.assertRaises(TypeError):
            straight_line_schedule(cost_minor=100, residual_minor=0, periods=3)

    def test_row_serialization_fields(self):
        self.assertEqual(
            asdict(self.schedule()[0]),
            {
                "period": 1,
                "year": 2026,
                "month": 11,
                "depreciation_minor": 30_000,
                "accumulated_depreciation_minor": 30_000,
                "carrying_value_minor": 70_000,
            },
        )

    def test_invariants_over_bounded_exhaustive_domain(self):
        # 10,710 schedules, including amounts smaller than the useful life.
        for cost in range(35):
            for residual in range(cost + 1):
                for periods in range(1, 18):
                    with self.subTest(cost=cost, residual=residual, periods=periods):
                        rows = self.schedule(
                            cost_minor=cost, residual_minor=residual, periods=periods,
                        )
                        expenses = [r.depreciation_minor for r in rows]
                        self.assertEqual(len(rows), periods)
                        self.assertEqual(sum(expenses), cost - residual)
                        self.assertEqual(rows[-1].carrying_value_minor, residual)
                        self.assertLessEqual(max(expenses) - min(expenses), 1)
                        self.assertEqual(expenses, sorted(expenses, reverse=True))
                        accumulated = 0
                        carrying = cost
                        for index, row in enumerate(rows, start=1):
                            accumulated += row.depreciation_minor
                            self.assertEqual(row.period, index)
                            self.assertEqual(row.accumulated_depreciation_minor, accumulated)
                            self.assertEqual(row.carrying_value_minor, cost - accumulated)
                            self.assertGreaterEqual(row.depreciation_minor, 0)
                            self.assertGreaterEqual(row.carrying_value_minor, residual)
                            self.assertLessEqual(row.carrying_value_minor, carrying)
                            carrying = row.carrying_value_minor


if __name__ == "__main__":
    unittest.main()

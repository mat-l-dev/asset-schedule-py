"""Exercise the installed-style module entry point as a subprocess."""

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import asset_schedule
from asset_schedule import __version__

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PARENT = Path(asset_schedule.__file__).resolve().parent.parent
BASE_ARGS = [
    "--cost-minor", "100000",
    "--residual-minor", "10000",
    "--periods", "3",
    "--start-year", "2026",
    "--start-month", "11",
]


class CliTests(unittest.TestCase):
    def run_cli(self, args):
        env = os.environ.copy()
        # Exercise the same package location as the parent test process.
        env["PYTHONPATH"] = str(PACKAGE_PARENT)
        return subprocess.run(
            [sys.executable, "-m", "asset_schedule", *args],
            capture_output=True, text=True, env=env, check=False,
        )

    def test_valid_json(self):
        result = self.run_cli(BASE_ARGS)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        document = json.loads(result.stdout)
        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(document["method"], "straight-line")
        self.assertEqual(document["remainder_allocation"], "earliest-periods")
        self.assertEqual(document["total_depreciation_minor"], 90_000)
        self.assertEqual(document["inputs"]["start_month"], 11)
        self.assertEqual(len(document["schedule"]), 3)
        self.assertEqual(document["schedule"][-1]["carrying_value_minor"], 10_000)
        self.assertEqual(document["schedule"][-1]["year"], 2027)

    def test_fixture_matches_output(self):
        result = self.run_cli(BASE_ARGS)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = json.loads((ROOT / "examples" / "schedule.json").read_text())
        self.assertEqual(json.loads(result.stdout), expected)

    def test_compact_output_preserves_document(self):
        regular = self.run_cli(BASE_ARGS)
        compact = self.run_cli([*BASE_ARGS, "--compact"])
        self.assertEqual(compact.returncode, 0, compact.stderr)
        self.assertEqual(len(compact.stdout.splitlines()), 1)
        self.assertEqual(json.loads(regular.stdout), json.loads(compact.stdout))

    def test_invalid_domain_inputs(self):
        for flag, value, message in (
            ("--cost-minor", "-1", "cost_minor"),
            ("--residual-minor", "-1", "residual_minor"),
            ("--residual-minor", "100001", "must not exceed"),
            ("--periods", "0", "periods"),
            ("--start-year", "0", "start_year"),
            ("--start-month", "13", "start_month"),
        ):
            with self.subTest(flag=flag, value=value):
                args = BASE_ARGS.copy()
                args[args.index(flag) + 1] = value
                result = self.run_cli(args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_calendar_overflow(self):
        args = BASE_ARGS.copy()
        args[args.index("--start-year") + 1] = "9999"
        args[args.index("--start-month") + 1] = "12"
        result = self.run_cli(args)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("December 9999", result.stderr)

    def test_non_integer_arguments(self):
        for value in ("1.5", "1.0", "true", "False", "abc", "1e3", "NaN"):
            with self.subTest(value=value):
                args = BASE_ARGS.copy()
                args[1] = value
                result = self.run_cli(args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("invalid int value", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_missing_argument(self):
        result = self.run_cli(BASE_ARGS[:-2])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("--start-month", result.stderr)

    def test_unknown_argument(self):
        result = self.run_cli([*BASE_ARGS, "--tax-rate", "0.2"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_abbreviated_argument_is_rejected(self):
        args = BASE_ARGS.copy()
        args[0] = "--cost"
        result = self.run_cli(args)
        self.assertEqual(result.returncode, 2)

    def test_help(self):
        result = self.run_cli(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("--cost-minor", result.stdout)
        self.assertIn("earliest periods", result.stdout)

    def test_version(self):
        result = self.run_cli(["--version"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), __version__)

    def test_large_integer_json(self):
        args = BASE_ARGS.copy()
        args[1] = str(10**100 + 7)
        result = self.run_cli(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        expenses = [row["depreciation_minor"] for row in document["schedule"]]
        self.assertEqual(sum(expenses), 10**100 + 7 - 10_000)

    def test_python_example(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PACKAGE_PARENT)
        result = subprocess.run(
            [sys.executable, str(ROOT / "examples" / "basic.py")],
            capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual([r["depreciation_minor"] for r in rows], [30_000] * 3)


if __name__ == "__main__":
    unittest.main()

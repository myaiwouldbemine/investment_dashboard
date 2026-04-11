from __future__ import annotations

import unittest

import pandas as pd

from src.quality.checks import DataQualityError, run_post_checks, run_pre_checks


class QualityChecksTests(unittest.TestCase):
    def test_pre_check_rejects_invalid_dates_and_negative_amounts(self) -> None:
        frame = pd.DataFrame(
            [
                {"trade_date": "bad-date", "amount": "100", "required": "ok"},
                {"trade_date": "2026-01-01", "amount": "-5", "required": "ok"},
            ]
        )

        with self.assertRaises(DataQualityError) as ctx:
            run_pre_checks(
                frame,
                domain="bond",
                dataset="source",
                required_columns=["required", "trade_date", "amount"],
                date_columns=["trade_date"],
                amount_columns=["amount"],
            )

        message = str(ctx.exception)
        self.assertIn("unparseable date column `trade_date`", message)
        self.assertIn("negative amount column `amount`", message)

    def test_post_check_rejects_date_range_errors(self) -> None:
        frame = pd.DataFrame(
            [
                {"start_date": pd.Timestamp("2026-02-01"), "maturity_date": pd.Timestamp("2026-01-01"), "amount": 100.0},
                {"start_date": pd.Timestamp("2026-01-01"), "maturity_date": pd.Timestamp("2026-03-01"), "amount": 110.0},
            ]
        )

        with self.assertRaises(DataQualityError) as ctx:
            run_post_checks(
                frame,
                domain="deposit",
                dataset="staging",
                amount_columns=[],
                date_ranges=[("start_date", "maturity_date")],
            )

        self.assertIn("invalid date range `maturity_date < start_date`", str(ctx.exception))

    def test_post_check_rejects_amount_anomalies(self) -> None:
        frame = pd.DataFrame(
            [{"amount": value} for value in [100.0, 102.0, 101.0, 99.0, 5000.0]]
        )

        with self.assertRaises(DataQualityError) as ctx:
            run_post_checks(
                frame,
                domain="stock",
                dataset="positions",
                amount_columns=["amount"],
                date_ranges=[],
            )

        self.assertIn("amount anomaly in `amount`", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

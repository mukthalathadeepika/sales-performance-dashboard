"""
tests/test_calculations.py
Automated acceptance tests verifying PRD Section 6 reference criteria and KPIs.
"""

import sys
from pathlib import Path
import unittest

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.file_handling.loader import load_dataset
from backend.column_mapping.detector import auto_detect_columns
from backend.cleaning.quality import run_data_quality_audit, clean_and_normalize_data
from backend.analytics.kpi import calculate_kpis
from backend.chat.engine import process_query


class TestSuperStoreAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample_path = Path(ROOT_DIR) / "data" / "sample" / "SuperStore_Sales_Dataset.csv"
        cls.df, err = load_dataset(str(cls.sample_path), file_name="SuperStore_Sales_Dataset.csv")
        assert err is None, f"Failed to load dataset: {err}"
        cls.mapping = auto_detect_columns(cls.df)
        cls.clean_df, cls.exclusions = clean_and_normalize_data(cls.df, cls.mapping)
        cls.audit = run_data_quality_audit(cls.df, cls.mapping)

    def test_01_row_and_column_counts(self):
        """PRD Check: 5,901 rows."""
        self.assertEqual(len(self.df), 5901)
        self.assertEqual(len(self.clean_df), 5901)
        self.assertEqual(self.audit["total_rows"], 5901)

    def test_02_distinct_order_ids(self):
        """PRD Check: 3,003 distinct Order IDs across 5,901 rows."""
        self.assertEqual(self.clean_df["_std_order_id"].nunique(), 3003)
        self.assertEqual(self.audit["distinct_orders"], 3003)

    def test_03_raw_sales_total(self):
        """PRD Check: Raw Sales total: 1,565,804.32."""
        raw_sales = self.clean_df["_std_sales"].sum()
        self.assertAlmostEqual(raw_sales, 1565804.32, places=2)

    def test_04_raw_profit_total(self):
        """PRD Check: Raw Profit total: 175,262.1059."""
        raw_profit = self.clean_df["_std_profit"].sum()
        self.assertAlmostEqual(raw_profit, 175262.1059, places=2)

    def test_05_raw_quantity_total(self):
        """PRD Check: Raw Quantity total: 22,317."""
        raw_qty = self.clean_df["_std_quantity"].sum()
        self.assertEqual(raw_qty, 22317)

    def test_06_geography_and_categories(self):
        """PRD Check: 49 states, 4 regions, 3 categories, 17 sub-categories."""
        self.assertEqual(self.clean_df["_std_state"].nunique(), 49)
        self.assertEqual(self.clean_df["_std_region"].nunique(), 4)
        self.assertEqual(self.clean_df["_std_category"].nunique(), 3)
        self.assertEqual(self.clean_df["_std_sub_category"].nunique(), 17)

    def test_07_returns_limitation(self):
        """PRD Check: Returns is #N/A on 5,614 rows; remaining values are 1 (287 rows)."""
        # In pandas, '#N/A' in CSV is read as NaN
        na_count = int(self.df["Returns"].isna().sum())
        self.assertEqual(na_count, 5614)
        # Check normalized returns (1 values)
        self.assertEqual(self.clean_df["_std_returns"].sum(), 287)
        self.assertIsNotNone(self.audit["returns_warning"])

    def test_08_blank_and_malformed_columns(self):
        """PRD Check: Two columns are blank (ind1, ind2); first header is malformed."""
        self.assertIn("ind1", self.audit["blank_columns"])
        self.assertIn("ind2", self.audit["blank_columns"])

    def test_09_date_coverage(self):
        """PRD Check: Dates cover 2019-01-01 through 2020-12-31."""
        valid_dates = self.clean_df["_std_order_date"].dropna()
        self.assertEqual(valid_dates.min().strftime("%Y-%m-%d"), "2019-01-01")
        self.assertEqual(valid_dates.max().strftime("%Y-%m-%d"), "2020-12-31")

    def test_10_kpis_and_aov(self):
        """Verify KPI calculations: AOV = total sales / distinct orders."""
        kpis = calculate_kpis(self.clean_df)
        self.assertAlmostEqual(kpis["total_sales"], 1565804.32, places=2)
        self.assertEqual(kpis["total_orders"], 3003)
        expected_aov = 1565804.3235 / 3003
        self.assertAlmostEqual(kpis["aov"], expected_aov, places=2)
        expected_margin = (175262.1059 / 1565804.3235) * 100
        self.assertAlmostEqual(kpis["profit_margin_pct"], expected_margin, places=2)

    def test_11_chat_engine_accuracy_and_scope(self):
        """Verify chat deterministic replies and out-of-scope handling."""
        # 1. Sales question
        res_sales = process_query("What are total sales?", self.clean_df)
        self.assertIn("₹", res_sales["answer_text"])
        self.assertNotIn("$", res_sales["answer_text"])
        from backend.analytics.currency import format_inr
        self.assertIn(format_inr(1565804.32), res_sales["answer_text"])

        # 2. Out-of-scope country (India)
        res_india = process_query("What are sales in India?", self.clean_df)
        self.assertTrue(res_india["is_unsupported"])
        self.assertIn("Coverage Limitation", res_india["answer_text"])
        self.assertIn("United States", res_india["answer_text"])

        # 3. Out-of-scope category (Toys)
        res_toys = process_query("Sales for Toys", self.clean_df)
        self.assertTrue(res_toys["is_unsupported"])
        self.assertIn("Toys", res_toys["answer_text"])


if __name__ == "__main__":
    unittest.main()

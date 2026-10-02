"""
tests/test_redesign.py
Comprehensive test suite verifying the redesigned architecture, Indian Rupee (₹) formatting,
12-step data pipeline, and chatbot integration.
"""

import sys
from pathlib import Path
import unittest

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.pipeline import run_full_pipeline
from backend.analytics.currency import format_inr
from backend.chat.engine import process_query
from frontend.components.charts import (
    plot_monthly_sales_and_profit,
    plot_category_sales_vs_profit,
    plot_profit_by_subcategory,
    plot_regional_profit_margins,
    plot_top_products_bar,
    plot_customer_segment_donut
)


class TestDashboardRedesign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sample_path = Path(ROOT_DIR) / "data" / "sample" / "SuperStore_Sales_Dataset.csv"
        cls.res = run_full_pipeline(str(sample_path), file_name="SuperStore_Sales_Dataset.csv")
        assert cls.res["success"], f"Pipeline failed: {cls.res.get('error')}"
        cls.df = cls.res["clean_df"]

    def test_01_pipeline_execution(self):
        """Verify 12-step pipeline completed successfully."""
        self.assertTrue(self.res["success"])
        self.assertEqual(self.res["row_count"], 5901)
        self.assertEqual(len(self.df), 5901)
        self.assertGreaterEqual(len(self.res["pipeline_steps"]), 5)

    def test_02_inr_formatting(self):
        """Verify Indian Rupee (₹) formatting with and without FX conversion."""
        raw = format_inr(1565804.32, compact=True, convert=False)
        self.assertTrue(raw.startswith("₹"))
        self.assertIn("15.66 L", raw)
        self.assertNotIn("$", raw)

        converted = format_inr(1565804.32, compact=True, convert=True)
        self.assertTrue(converted.startswith("₹"))
        self.assertNotIn("$", converted)
        self.assertIn("Cr", converted)

        formatted_profit = format_inr(175262.11, compact=True, convert=False)
        self.assertIn("1.75 L", formatted_profit)

        formatted_negative = format_inr(-10500.50, compact=False, convert=False)
        self.assertTrue(formatted_negative.startswith("-₹"))

    def test_03_charts_generation(self):
        """Verify all 6 Plotly charts generate without errors."""
        fig1 = plot_monthly_sales_and_profit(self.df)
        self.assertIsNotNone(fig1)

        fig2 = plot_category_sales_vs_profit(self.df)
        self.assertIsNotNone(fig2)

        fig3 = plot_profit_by_subcategory(self.df)
        self.assertIsNotNone(fig3)

        fig4 = plot_regional_profit_margins(self.df)
        self.assertIsNotNone(fig4)

        fig5 = plot_top_products_bar(self.df, metric="Sales")
        self.assertIsNotNone(fig5)

        fig6 = plot_customer_segment_donut(self.df)
        self.assertIsNotNone(fig6)

    def test_04_chatbot_inr_and_questions(self):
        """Verify chatbot queries return INR currency and accurate answers."""
        # 1. Total sales question
        r1 = process_query("What is the total sales?", self.df)
        self.assertIn("₹", r1["answer_text"])
        self.assertNotIn("$", r1["answer_text"])
        self.assertIn(format_inr(1565804.32), r1["answer_text"])

        # 2. Region with highest sales
        r2 = process_query("Which region has the highest sales?", self.df)
        self.assertIn("West", r2["answer_text"])
        self.assertIn("₹", r2["answer_text"])

        # 3. Best sales month
        r3 = process_query("What was the best sales month?", self.df)
        self.assertIn("Dec 2020", r3["answer_text"])
        self.assertIn("₹", r3["answer_text"])

        # 4. Compare West and East
        r4 = process_query("Compare West and East regions.", self.df)
        self.assertIn("West", r4["answer_text"])
        self.assertIn("East", r4["answer_text"])

        # 5. Products causing losses
        r5 = process_query("Which products are causing losses?", self.df)
        self.assertIn("₹", r5["answer_text"])
        self.assertIsNotNone(r5["chart_data"])

    def test_05_shipping_analytics(self):
        """Verify shipping analytics calculates mode breakdown and average transit days."""
        from backend.analytics.shipping import get_shipping_summary
        summary = get_shipping_summary(self.df)
        self.assertIsNotNone(summary["avg_days"])
        self.assertGreater(summary["avg_days"], 0)
        self.assertFalse(summary["mode_breakdown"].empty)
        self.assertIn("Ship Mode", summary["mode_breakdown"].columns)

    def test_06_entity_period_comparison_and_trends(self):
        """Verify natural language comparisons with entities and years."""
        # 1. Compare Technology sales in 2019 and 2020
        r1 = process_query("Compare Technology sales in 2019 and 2020", self.df)
        self.assertIn("Technology", r1["answer_text"])
        self.assertIn("2019", r1["answer_text"])
        self.assertIn("2020", r1["answer_text"])
        self.assertIsNotNone(r1["chart_data"])

        # 2. Performance trend for entity
        r2 = process_query("What happened to sales in West?", self.df)
        self.assertIn("West", r2["answer_text"])
        self.assertIn("₹", r2["answer_text"])

    def test_07_coverage_limitation_and_word_boundaries(self):
        """Verify out-of-scope query handling and word-boundary state matching."""
        # Unrelated domain metric
        r1 = process_query("What is our employee attrition rate?", self.df)
        self.assertTrue(r1["is_unsupported"] or "out-of-scope" in r1["answer_text"].lower() or "coverage limitation" in r1["answer_text"].lower())

        # India should NOT match Indiana as a state entity
        r2 = process_query("What are the total sales in India?", self.df)
        self.assertTrue(r2["is_unsupported"] or "coverage limitation" in r2["answer_text"].lower() or "not contain" in r2["answer_text"].lower() or "outside" in r2["answer_text"].lower())

    def test_08_metric_precision(self):
        """Verify total sales calculation matches exact rounded sum."""
        total_sum = round(float(self.df["_std_sales"].sum()), 2)
        expected_str = format_inr(total_sum)
        r = process_query("What is the total sales?", self.df)
        self.assertIn(expected_str, r["answer_text"])


if __name__ == "__main__":
    unittest.main()

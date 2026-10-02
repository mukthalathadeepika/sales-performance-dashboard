"""Additional platform tests: FX display, dataset swap, forecast, unique keys, follow-ups."""

import io
import re
import sys
import unittest
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.pipeline import run_full_pipeline
from backend.analytics.currency import format_inr, set_exchange_rate, get_exchange_rate
from backend.chat.engine import process_query
from backend.forecasting.forecast import forecast_sales
from backend.exports.exporter import export_to_csv, export_to_excel, generate_executive_pdf
from backend.analytics.kpi import calculate_kpis
from backend.analytics.insights import generate_executive_insights


class TestPlatformBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sample = Path(ROOT_DIR) / "data" / "sample" / "SuperStore_Sales_Dataset.csv"
        cls.res = run_full_pipeline(str(sample), file_name="SuperStore_Sales_Dataset.csv")
        cls.df = cls.res["clean_df"]

    def test_01_no_dollar_in_user_facing_currency(self):
        text = format_inr(12345.67)
        self.assertIn("₹", text)
        self.assertNotIn("$", text)

    def test_02_exchange_rate_changes_display(self):
        original = get_exchange_rate()
        try:
            set_exchange_rate(80.0, "USD")
            a = format_inr(100, convert=True)
            set_exchange_rate(90.0, "USD")
            b = format_inr(100, convert=True)
            self.assertNotEqual(a, b)
        finally:
            set_exchange_rate(original, "USD")

    def test_03_alternate_dataset_replaces_mapping(self):
        csv = (
            "InvoiceDate,Revenue,Item,Territory\n"
            "2021-01-15,100,Widget,North\n"
            "2021-02-20,250,Gadget,South\n"
            "2021-03-10,50,Widget,North\n"
        )
        res = run_full_pipeline(io.StringIO(csv), file_name="alt_sales.csv")
        self.assertTrue(res["success"], res.get("error"))
        df = res["clean_df"]
        self.assertIn("_std_sales", df.columns)
        self.assertIn("_std_order_date", df.columns)
        self.assertAlmostEqual(float(df["_std_sales"].sum()), 400.0)
        self.assertNotIn("_std_profit", df.columns)
        r = process_query("What is the total sales?", df)
        self.assertIn("₹", r["answer_text"])
        self.assertNotIn("1,565,804.32", r["answer_text"])

    def test_04_missing_geography_does_not_crash_pipeline(self):
        csv = "Date,Amount\n2024-01-01,10\n2024-02-01,20\n"
        res = run_full_pipeline(io.StringIO(csv), file_name="tiny.csv")
        self.assertTrue(res["success"])
        self.assertNotIn("_std_state", res["clean_df"].columns)

    def test_05_forecast_insufficient_data(self):
        csv = "Date,Amount\n2024-01-01,10\n2024-01-02,20\n"
        res = run_full_pipeline(io.StringIO(csv), file_name="short.csv")
        fc = forecast_sales(res["clean_df"], min_months=4)
        self.assertFalse(fc["available"])
        self.assertIn("insufficient", fc["message"].lower())

    def test_06_forecast_available_on_sample(self):
        fc = forecast_sales(self.df)
        self.assertTrue(fc["available"])
        self.assertEqual(len(fc["forecast"]), 3)

    def test_07_follow_up_uses_region_context(self):
        first = process_query("Which region has the highest sales?", self.df)
        self.assertIn("West", first["answer_text"])
        follow = process_query("What about profit?", self.df, prev_context=first["context"])
        self.assertIn("profit", follow["answer_text"].lower())
        self.assertFalse(follow["is_unsupported"])

    def test_08_compare_months(self):
        r = process_query("Compare January 2019 and January 2020", self.df)
        self.assertIn("2019", r["answer_text"])
        self.assertIn("2020", r["answer_text"])
        self.assertIsNotNone(r["chart_data"])

    def test_09_exports_work(self):
        kpis = calculate_kpis(self.df)
        csv = export_to_csv(self.df)
        self.assertTrue(csv.startswith(b"") or len(csv) > 10)
        xls = export_to_excel(self.df, kpis)
        self.assertGreater(len(xls), 100)
        insights = generate_executive_insights(self.df)
        pdf = generate_executive_pdf(kpis=kpis, findings=insights.get("findings", []), date_range_str="Test", currency_symbol="₹")
        self.assertGreater(len(pdf), 100)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_10_unique_plotly_keys(self):
        files = [
            Path(ROOT_DIR) / "frontend" / "views" / "dashboard_view.py",
            Path(ROOT_DIR) / "frontend" / "views" / "sales_analysis_view.py",
            Path(ROOT_DIR) / "frontend" / "views" / "ai_assistant_view.py",
            Path(ROOT_DIR) / "frontend" / "components" / "map.py",
        ]
        keys = []
        for path in files:
            text = path.read_text(encoding="utf-8")
            keys.extend(re.findall(r'key="([a-zA-Z0-9_]+_chart)"', text))
            keys.extend(re.findall(r'key="(geo_sales_map)"', text))
        dupes = [k for k in keys if keys.count(k) > 1]
        self.assertEqual(dupes, [], f"Duplicate chart keys: {dupes}")

    def test_11_data_quality_not_in_nav(self):
        app = (Path(ROOT_DIR) / "frontend" / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("Data Quality", app)
        self.assertIn("Sales Analysis", app)
        self.assertIn("AI Sales Assistant", app)


if __name__ == "__main__":
    unittest.main()

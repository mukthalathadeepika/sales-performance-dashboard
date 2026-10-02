"""Quick import and pipeline verification."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

print("Testing imports...")
try:
    from backend.pipeline import run_full_pipeline
    print("  ✓ Pipeline")
    from backend.analytics.currency import format_inr, set_exchange_rate, get_exchange_rate
    print("  ✓ Currency")
    from backend.analytics.kpi import calculate_kpis
    print("  ✓ KPIs")
    from backend.analytics.insights import generate_executive_insights
    print("  ✓ Insights")
    from backend.chat.engine import process_query, EXAMPLE_PROMPTS
    print("  ✓ Chat Engine")
    from backend.exports.exporter import generate_executive_pdf
    print("  ✓ Exporter")
    from backend.analytics.categories import get_category_breakdown
    print("  ✓ Categories")
    from backend.analytics.geography import get_state_breakdown
    print("  ✓ Geography")
except ImportError as e:
    print(f"  ✗ Import Error: {e}")
    sys.exit(1)

print("\nTesting pipeline on sample data...")
res = run_full_pipeline("data/sample/SuperStore_Sales_Dataset.csv", file_name="SuperStore.csv")
print(f"  Success: {res['success']}")
if not res['success']:
    print(f"  Error: {res.get('error')}")
    sys.exit(1)

df = res["clean_df"]
print(f"  Shape: {df.shape}")
std_cols = [c for c in df.columns if c.startswith("_std_")]
print(f"  Std columns ({len(std_cols)}): {std_cols[:10]}")

print("\nTesting currency...")
set_exchange_rate(83.5, "USD")
print(f"  Rate: 1 {res.get('file_name', 'USD')} = ₹{get_exchange_rate()}")
print(f"  format_inr(1000): {format_inr(1000, compact=True)}")
print(f"  format_inr(150000): {format_inr(150000, compact=True)}")

print("\nTesting KPIs...")
kpis = calculate_kpis(df)
print(f"  KPIs: {list(kpis.keys())[:6]}")

print("\nTesting chat engine...")
r1 = process_query("What is the total sales?", df)
print(f"  Q: What is the total sales?")
print(f"  A: {r1['answer_text'][:100]}")

r2 = process_query("Which region has the highest sales?", df)
print(f"  Q: Which region has the highest sales?")
print(f"  A: {r2['answer_text'][:100]}")

print("\nTesting insights...")
ins = generate_executive_insights(df)
print(f"  Findings: {len(ins.get('findings', []))}")
print(f"  Bullets: {len(ins.get('summary_bullets', []))}")

print("\nTesting PDF export...")
try:
    pdf = generate_executive_pdf(kpis=kpis, findings=ins.get("findings", []),
                                  date_range_str="Test", currency_symbol="₹")
    print(f"  PDF size: {len(pdf)} bytes")
except Exception as e:
    print(f"  PDF Error: {e}")

print("\n✅ All tests passed!")

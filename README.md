# Sales Performance Dashboard

## 🚀 Live Dashboard

[Open Live Dashboard](https://muktha-sales-dashboard.streamlit.app/)

## 💻 Project Repository

[View Source Code on GitHub](https://github.com/mukthalathadeepika/sales-performance-dashboard)

This project is a Sales Performance Dashboard developed as part of my Syntecxhub internship.

### Features
- Sales and profit KPIs
- Monthly, quarterly and yearly analysis
- Product and category analysis
- Region-wise analysis
- Interactive filters
- Sales and profitability insights

Built in strict adherence to business intelligence standards and validated against the reference **SuperStore Sales Dataset** (5,901 records, 2019–2020).

---

## 🌟 Key Application Pages

The application is structured into **three focused, production-ready primary pages** accessible from the sidebar navigation:

### 1. 📊 Executive Dashboard
- **Executive KPI Cards**:
  - **Total Sales / Revenue** (formatted in Indian Rupees `₹` with compact notation `L` / `Cr`)
  - **Total Net Profit** (accurately accounting for negative profit & loss-making items)
  - **Total Orders (Distinct)** (distinct count of Order IDs across line items)
  - **Total Quantity Sold** (units)
  - **Profit Margin %** ($\text{Total Profit} / \text{Total Sales} \times 100$)
  - **Average Order Value (AOV)** ($\text{Total Sales} / \text{Distinct Orders}$)
- **Visual Analytics Suite (Plotly)**:
  - **Monthly Sales & Profit Combo Chart**: Monthly sales bars and net profit line with dual-axis visualization, cumulative trend curves, and 1-click PNG export.
  - **Category & Sub-Category Performance**: Multi-metric breakdown comparing Sales, Profit, and Quantity across product hierarchies.
  - **Regional Performance**: Grouped bar charts showing regional revenue and profit distribution.
  - **Top & Bottom Products Ranking**: Configurable ranking ($N=5, 10, 20$ for Top; $N=5, 10$ for Bottom) across Sales, Profit, and Quantity with interactive chart and tabular views.
  - **Geographic Visualizations**: Interactive US State Choropleth map, regional drill-down, and top city breakdown.
  - **Shipping & Fulfillment Analytics**: Average transit duration (Ship Date minus Order Date) and order distribution across shipping modes.
- **Executive Data Exports**: One-click downloads for filtered datasets in **CSV**, multi-sheet **Excel (.xlsx)**, and executive **PDF briefings**.

### 2. 🔎 Sales Analysis
- **Custom Multidimensional Deep-Dive**:
  - Group sales, profit, quantity, or distinct orders by Category, Sub-Category, Region, State, City, Segment, Ship Mode, or Product.
  - Interactive chart formats: Grouped Bar, Horizontal Bar, Line Chart, Pie/Donut Chart, Treemap, or Data Table.
  - Flexible time aggregations: Monthly, Quarterly, Yearly, or Daily grains.
- **Unified Period Comparison Engine**:
  - Compare any grouped dimension across **Year vs Year**, **Month vs Month**, **Quarter vs Quarter**, or **Custom Date Ranges**.
  - Detailed variance reporting displaying Baseline Value, Comparison Value, Absolute Difference, and Percentage Change ($\pm\%$).
  - One-click export of comparison tables in both **CSV** and **Excel (.xlsx)** formats.

### 3. 🤖 AI Sales Assistant
- **Deterministic Natural Language Query Engine**:
  - Pure dataset-grounded calculations using Pandas — **zero hallucinations, no paid external AI dependencies**.
  - Answers questions on revenue, profit, margins, top products, best/worst months, regional comparisons, and entity trends.
  - Direct visualization of query results with interactive Plotly charts, expandable supporting data tables formatted in INR, and context pills (dimension, metric, entity, dates).
- **Explicit Coverage Limitation Disclosures**:
  - Automatically identifies out-of-scope concepts (e.g. employee attrition, inventory levels, weather, unmapped entities like India when data covers US states).
  - Returns clear, professional coverage guidance disclosing available dataset boundaries.

---

## 🛠️ Data Pipeline & Currency Management

- **12-Step Ingestion & Normalization Pipeline** (`backend/pipeline.py`):
  - Non-destructive processing of CSV, Excel (`.xlsx`, `.xls`), and TSV files.
  - Automatic column mapping with heuristic confidence scoring.
  - Robust date parsing handling `DD-MM-YYYY` formats with `dayfirst=True` safeguards.
  - Automatic handling of duplicate rows, whitespace, and blank columns (`ind1`, `ind2`).
- **Standardized Currency Engine** (`backend/analytics/currency.py`):
  - Full Indian Rupee (`₹`) formatting across KPI cards, charts, tooltips, tables, exports, and chat responses.
  - Configurable source currency and exchange rates (default `83.5 INR/USD`).
  - No inconsistent dollar (`$`) symbols in the user interface.
- **Dataset & Filter Management**:
  - **Reset All Filters**: Restores the full currently loaded dataset without losing data.
  - **Clear Current Dataset**: Wipes the active dataset and returns the application to a clean empty state.
  - **1-Click Sample Loader**: Instant reload of the built-in SuperStore dataset from the sidebar or empty state.

---

## 📐 Reference Dataset Validation

Tested and verified against `data/sample/SuperStore_Sales_Dataset.csv`:

| Reference Metric | PRD Specification | Application Value | Status |
| :--- | :--- | :--- | :--- |
| **Total Rows** | 5,901 rows | 5,901 rows | ✅ Verified |
| **Distinct Orders** | 3,003 distinct Order IDs | 3,003 distinct Order IDs | ✅ Verified |
| **Raw Sales Total** | 1,565,804.32 | 1,565,804.32 | ✅ Verified |
| **Raw Profit Total** | 175,262.1059 | 175,262.11 | ✅ Verified |
| **Raw Quantity Total** | 22,317 units | 22,317 units | ✅ Verified |
| **Geographic Scope** | 49 states, 4 regions | 49 states, 4 regions | ✅ Verified |
| **Categories** | 3 categories, 17 sub-categories | 3 categories, 17 sub-categories | ✅ Verified |
| **Date Range** | 2019-01-01 to 2020-12-31 | 2019-01-01 to 2020-12-31 | ✅ Verified |
| **Shipping Duration** | Tracked shipping days | Average 3.9 days | ✅ Verified |

---

## 📂 Repository Architecture

```text
sales-performance-dashboard/
|-- frontend/                     # Streamlit presentation layer
|   |-- app.py                    # Main application controller & navigation
|   |-- views/                    # Primary application views
|   |   |-- dashboard_view.py     # 📊 Executive Dashboard view
|   |   |-- sales_analysis_view.py# 🔎 Multidimensional & Period Comparison view
|   |   `-- ai_assistant_view.py  # 🤖 Natural language AI assistant view
|   |-- components/               # Reusable visual components
|   |   |-- kpi_card.py           # Standardized KPI cards
|   |   |-- charts.py             # Plotly chart generators
|   |   `-- map.py                # Geographic maps
|   `-- styles/
|       `-- main.css              # Dark Navy BI theme styling
|-- backend/                      # Analytical, data processing & chat services
|   |-- pipeline.py               # 12-step data ingestion & normalization pipeline
|   |-- analytics/                # Calculations (KPIs, currency, shipping, insights)
|   |-- chat/                     # Deterministic query engine & coverage guardrails
|   |-- cleaning/                 # Data quality checks, deduplication & normalization
|   |-- column_mapping/           # Semantic column detector & confidence scoring
|   |-- forecasting/              # Moving-average sales forecasting
|   |-- file_handling/            # CSV, Excel, TSV reader
|   `-- exports/                  # CSV, Excel (.xlsx), and PDF generators
|-- data/sample/                  # Reference sample data (SuperStore_Sales_Dataset.csv)
|-- tests/                        # Automated test suite (30 unit & platform tests)
|   |-- test_calculations.py      # Core KPI and metric calculation tests
|   |-- test_platform.py          # Platform, key uniqueness, and export tests
|   |-- test_redesign.py          # Chatbot, currency, shipping, and NLP tests
|   `-- test_quick.py             # Quick pipeline sanity check
|-- .streamlit/
|   `-- config.toml               # Streamlit theme & server configuration
|-- app.py                        # Root launcher entry point
|-- requirements.txt              # Project dependencies
`-- README.md                     # Comprehensive project documentation
```

---

## 🚀 Local Installation & Execution

### 1. Prerequisites
- Python 3.9, 3.10, or 3.11 installed.

### 2. Clone Repository
```bash
git clone https://github.com/<your-username>/sales-performance-dashboard.git
cd sales-performance-dashboard
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Automated Test Suite
Run all 30 automated test cases:
```bash
python -m pytest
```

### 5. Launch the Application
Run via the root launcher:
```bash
streamlit run app.py
```
Or directly via the frontend module:
```bash
streamlit run frontend/app.py
```
Open your browser at `http://localhost:8501`.

---

## 🌐 Deployment to Streamlit Community Cloud

1. **Commit & Push to GitHub**:
   ```bash
   git add .
   git commit -m "feat: complete production-ready sales performance dashboard"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**:
   - Visit [share.streamlit.io](https://share.streamlit.io) and sign in.
   - Click **"New app"**.
   - Select your repository and `main` branch.
   - Set **Main file path** to `app.py` (or `frontend/app.py`).
   - Click **"Deploy!"**.

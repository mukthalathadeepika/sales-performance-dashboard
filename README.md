# Sales Performance Dashboard MVP

A business analytics web application built with **Python**, **Streamlit**, **Pandas**, and **Plotly** to inspect, visualize, compare, and query sales data.

Built in strict adherence to the [Product Requirements Document (PRD)](./Sales_Performance_Dashboard_PRD.pdf) and verified against the reference **SuperStore Sales Dataset** (5,901 records, 2019–2020).

---

## 🌟 Key Features

### 1. Home / Landing Page
- Introduces the platform in a few clear lines.
- Four interactive option cards matching PRD Section 2.1:
  - **Explore the Dashboard**: Inspect interactive charts, KPI cards, and dynamic filters.
  - **Build an Analysis**: Custom query builder to choose measure, dimension, ranking, and chart format.
  - **Automatic Overview**: Executive narrative briefing, key performance drivers, and PDF report export.
  - **Ask in Chat**: Plain-language sales questions answered deterministically and visualized on screen.
- Quick preview button to load the reference dataset with 1 click.

### 2. Executive Performance Dashboard
- **Core KPI Cards**:
  - **Total Sales / Revenue**
  - **Total Net Profit** (includes negative profits / loss-making lines)
  - **Total Orders (Distinct)** (distinct count of Order IDs across lines)
  - **Total Quantity Sold**
  - **Total Unique Customers**
  - **Average Order Value (AOV)**: $\text{Total Sales} / \text{Distinct Orders}$
  - **Profit Margin %**: $\text{Total Profit} / \text{Total Sales} \times 100$
  - **Sales Target Achievement %** with interactive target setter
- **Interactive Multi-Level Filters**:
  - Order Date range slider / picker
  - Region, Category, Sub-Category (cascaded), Customer Segment, and State filters
  - Currency display selector (`$`, `€`, `£`, `₹`, `¥`, or unadorned numeric values)
  - **Reset All Filters** one-click button restoring full dataset
- **Visual Analytics Suite (Plotly)**:
  - **Monthly Sales & Profit Combo Chart** (Bar + Line with dual y-axis) & Cumulative Sales curve
  - **Top & Bottom Products Ranking** (selectable $N=5, 10, 15, 20$; Sales, Profit, Quantity) with Chart/Table switch
  - **Category & Sub-Category Treemap** (sized by Sales, colored by Margin %) & Profitability Matrix
  - **Geographic US State Map** & Hierarchical Drill-Down (Region → State → City)
  - **Customer Segment Distribution Donut Chart**
  - **Fulfillment Transit Duration** (Ship Date minus Order Date) by Ship Mode
  - **Returns Analysis** with visible coverage limitation notice
  - **Data Exports**: Download filtered data as CSV or multi-sheet Excel workbook

### 3. Guided Analysis Builder
- Searchable query builder allowing users to choose:
  - **Measure**: Sales, Profit, Quantity, Distinct Orders
  - **Dimension Grouping**: Category, Sub-Category, Region, State, City, Segment, Ship Mode, Product
  - **Ranking / Limit**: Top 5, Top 10, Top 20, Bottom 5, Bottom 10, All Items
  - **Visual Format**: Bar Chart, Line Chart, Donut Chart, Treemap, or Data Table
- Direct export of the customized data slice.

### 4. Automatic Overview & Executive Insights
- Deterministic, data-grounded executive narrative (no hallucinated AI assumptions).
- Highlights top-performing categories, margin leaders, and loss-making items.
- Transaction Anomaly detection flagging top 0.5% high-value orders and significant losses.
- **Executive PDF Report Export**: One-click download of a professional briefing PDF generated via ReportLab with customer-name masking options.

### 5. Natural Language Sales Chat Assistant
- Natural language query processor using pure deterministic Pandas calculations (no paid external AI API required).
- Supported query types:
  - Total sales, profit, distinct orders, AOV, profit margin
  - Best / top / highest category, sub-category, product, region, state
  - Year-over-year comparisons (e.g. 2019 vs 2020)
  - Customer segment distribution
- Explicit coverage disclosures (out-of-scope locations like India or categories like Toys are clearly identified without fabricating data).
- Renders requested charts directly on the main canvas accompanied by data tables and context tags.

### 6. Data Quality Audit & Semantic Mapping
- Non-destructive data ingestion supporting CSV, Excel (.xlsx), and TSV files.
- Automated column mapping with confidence scoring and manual override dropdowns.
- Detailed quality health check:
  - Total input rows and distinct order IDs
  - Exact duplicate row detection vs repeated order IDs
  - Missing value counts and placeholder (`#N/A`, `null`, `none`) audit
  - Automatic date format handling (`DD-MM-YYYY`, `dayfirst=True`)
  - Detection of unused / blank columns (`ind1`, `ind2`)

---

## 📐 PRD Reference Dataset Validation

Tested against `data/sample/SuperStore_Sales_Dataset.csv`:

| Reference Item | PRD Specification | Application Value | Status |
| :--- | :--- | :--- | :--- |
| **Total Rows** | 5,901 rows | 5,901 rows | ✅ Verified |
| **Distinct Orders** | 3,003 distinct Order IDs | 3,003 distinct Order IDs | ✅ Verified |
| **Raw Sales Total** | 1,565,804.32 | 1,565,804.32 | ✅ Verified |
| **Raw Profit Total** | 175,262.1059 | 175,262.11 | ✅ Verified |
| **Raw Quantity Total** | 22,317 units | 22,317 units | ✅ Verified |
| **Geographic Scope** | 49 states, 4 regions | 49 states, 4 regions | ✅ Verified |
| **Categories** | 3 categories, 17 sub-categories | 3 categories, 17 sub-categories | ✅ Verified |
| **Date Range** | 2019-01-01 to 2020-12-31 | 2019-01-01 to 2020-12-31 | ✅ Verified |
| **Returns Limitation** | 5,614 `#N/A` rows, 287 tracked returns | 5,614 missing, 287 tracked | ✅ Verified & Disclosed |
| **Malformed / Blank Cols** | `ind1`, `ind2` blank; BOM on header | Flagged & handled safely | ✅ Verified |

---

## 📂 Repository Layout

```text
sales-performance-dashboard/
|-- frontend/                 # Streamlit pages and visual components
|   |-- app.py                # Primary entry point selected for deployment
|   |-- pages/                # Modular view pages
|   |   |-- home.py
|   |   |-- dashboard.py
|   |   |-- guided_analysis.py
|   |   |-- automatic_overview.py
|   |   |-- chat_view.py
|   |   `-- data_quality.py
|   |-- components/           # Reusable UI modules
|   |   |-- kpi_card.py
|   |   |-- filters.py
|   |   `-- charts.py
|   `-- styles/
|       `-- main.css          # Executive typography and card styling
|-- backend/                  # Analytical & data processing services
|   |-- file_handling/        # Robust CSV, Excel, TSV reader
|   |-- cleaning/             # Data quality audit & normalization
|   |-- column_mapping/       # Heuristic semantic column detector
|   |-- analytics/            # KPIs, trends, geography, drill-down, insights
|   |-- chat/                 # Deterministic query engine
|   `-- exports/              # PDF and Excel generators
|-- data/sample/              # Safe sample dataset (SuperStore CSV)
|-- tests/                    # Acceptance & calculation unit tests
|   `-- test_calculations.py
|-- .streamlit/
|   `-- config.toml           # Theme and deployment parameters
|-- app.py                    # Root entry point launcher
|-- requirements.txt          # Python dependencies
|-- README.md                 # Complete documentation
`-- .gitignore                # Excludes secrets, caches, private uploads
```

---

## 🚀 Local Installation & Execution

### 1. Prerequisites
- Python 3.9+ installed.

### 2. Clone Repository
```bash
git clone https://github.com/<your-username>/sales-performance-dashboard.git
cd sales-performance-dashboard
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Acceptance Tests
```bash
python -m unittest tests/test_calculations.py
```

### 5. Launch the Application
Run via the root launcher:
```bash
streamlit run app.py
```
Or via the frontend entry point:
```bash
streamlit run frontend/app.py
```
Open your browser at `http://localhost:8501`.

---

## 🌐 Deployment to Streamlit Community Cloud

Deploy in under 3 minutes:

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "feat: complete sales performance dashboard MVP"
   git branch -M main
   git remote add origin https://github.com/<your-username>/sales-performance-dashboard.git
   git push -u origin main
   ```

2. **Connect to Streamlit Community Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
   - Click **"New app"**.
   - Select your repository: `<your-username>/sales-performance-dashboard`.
   - Select Branch: `main`.
   - Set **Main file path**: `frontend/app.py` (or `app.py`).
   - Click **"Deploy!"**.

3. Your live dashboard will be accessible via a public shareable URL.

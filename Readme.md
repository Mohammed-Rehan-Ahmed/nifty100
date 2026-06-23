# Nifty 100 Financial Intelligence Platform

> Production-grade financial analytics system covering 101 Nifty 100 companies
> across 12 modules, 50+ KPIs, and a 6-sprint build timeline.

---

## Quick Start

\```powershell
# 1. Enter project directory
cd nifty100

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create package markers
New-Item -ItemType File -Force src\__init__.py
New-Item -ItemType File -Force src\etl\__init__.py
New-Item -ItemType File -Force tests\__init__.py
New-Item -ItemType File -Force tests\etl\__init__.py

# 5. Initialise schema + run ETL
python db/init_db.py
python src/etl/loader.py

# 6. Verify Sprint 1 gates
python src/etl/sprint1_verify.py

# 7. Compute all KPIs
python src/analytics/ratios.py
python src/analytics/cagr.py
python src/analytics/cashflow_kpis.py
python src/analytics/merge_ratios.py

# 8. Launch dashboard
streamlit run src/dashboard/app.py
\```

---

## Project Structure

\```
nifty100/
│
├── data/
│   ├── raw/                         ← 7 core Excel files (READ ONLY)
│   │   ├── companies.xlsx
│   │   ├── profitandloss.xlsx
│   │   ├── balancesheet.xlsx
│   │   ├── cashflow.xlsx
│   │   ├── analysis.xlsx
│   │   ├── documents.xlsx
│   │   └── prosandcons.xlsx
│   │
│   ├── supporting/                  ← 5 supplementary Excel files
│   │   ├── financial_ratios.xlsx
│   │   ├── market_cap.xlsx
│   │   ├── peer_groups.xlsx
│   │   ├── sectors.xlsx
│   │   └── stock_prices.xlsx
│   │
│   └── nifty100.db                  ← SQLite database (12 tables)
│
├── src/
│   ├── etl/
│   │   ├── loader.py                ← Excel → SQLite pipeline
│   │   ├── normaliser.py            ← Year + ticker normalisation
│   │   ├── validator.py             ← 16 DQ rules
│   │   ├── dq_review.py             ← Post-load audit queries
│   │   └── sprint1_verify.py        ← Sprint 1 exit criteria checker
│   │
│   ├── analytics/
│   │   ├── ratios.py                ← 50+ KPI computation
│   │   ├── cagr.py                  ← 3/5/10yr CAGR engine
│   │   ├── cashflow_kpis.py         ← Capital allocation + CF intelligence
│   │   ├── merge_ratios.py          ← Final ratio table assembly
│   │   ├── sector_roce.py           ← Sector benchmarks + ROCE anomalies
│   │   ├── valuation.py             ← P/E, P/B, EV/EBITDA, FCF yield
│   │   ├── peer.py                  ← Peer percentile ranks + badges
│   │   ├── radar_charts.py          ← Radar PNG per company
│   │   └── screener/
│   │       ├── __init__.py
│   │       ├── engine.py            ← 6 preset screeners + composite score
│   │       ├── ranking.py           ← Sector-relative ranks + outlier flags
│   │       └── sprint3_verify.py    ← Sprint 3 exit criteria checker
│   │
│   ├── dashboard/
│   │   ├── app.py                   ← Streamlit entry point
│   │   ├── pages/
│   │   │   ├── 01_home.py
│   │   │   ├── 02_company.py
│   │   │   ├── 03_screener.py
│   │   │   ├── 04_peer.py
│   │   │   ├── 05_trends.py
│   │   │   ├── 06_sector.py
│   │   │   ├── 07_capital.py
│   │   │   ├── 08_documents.py
│   │   │   ├── 09_valuation.py
│   │   │   └── 10_cashflow_intel.py
│   │   └── utils/
│   │       ├── db.py                ← Cached SQLite query helpers
│   │       └── charts.py            ← Plotly/matplotlib chart builders
│   │
│   ├── reports/
│   │   ├── tearsheet.py             ← 2-page company PDF (101 companies)
│   │   └── sector_report.py         ← Sector PDF (11 sectors)
│   │
│   └── api/
│       └── main.py                  ← FastAPI server (16 endpoints)
│
├── db/
│   ├── schema.sql                   ← 12-table SQLite schema with FK constraints
│   └── init_db.py                   ← Schema initialisation script
│
├── tests/
│   ├── etl/
│   │   ├── test_normalise.py        ← 20 normaliser unit tests
│   │   ├── test_validator.py        ← 32 DQ rule tests
│   │   └── test_screener.py         ← 7 screener logic tests
│   ├── kpi/
│   │   ├── test_ratios.py
│   │   ├── test_cagr.py
│   │   ├── test_cashflow.py
│   │   ├── test_leverage.py
│   │   ├── test_peer.py
│   │   ├── test_radar.py
│   │   ├── test_sprint2_verify.py
│   │   └── test_kpi_full.py
│   └── dq/
│       └── test_dq_rules.py         ← 34 DQ integration tests
│
├── config/
│   ├── screener_config.yaml         ← 6 preset screener thresholds
│   ├── logging_config.yaml          ← Log levels + handlers
│   └── .env.template                ← Environment variable template
│
├── reports/
│   ├── tearsheets/                  ← 101 company PDFs
│   ├── sector/                      ← 11 sector PDFs
│   ├── portfolio/                   ← Portfolio summary PDF
│   └── radar_charts/                ← 101 radar PNGs
│
├── output/
│   ├── load_audit.csv               ← Per-table ETL load statistics
│   └── validation_failures.csv      ← All DQ rule violations
│
├── notebooks/
│   └── exploratory_queries.sql      ← 10 audit SQL queries
│
├── docs/
│   ├── sprint1_retro.md
│   ├── sprint2_retro.md
│   └── sprint3_retro.md
│
├── logs/
│   └── app.log
│
├── .env                             ← DB_PATH, PORT, LOG_LEVEL
├── requirements.txt
├── Makefile
└── README.md
\```

---

## Database Schema — 12 Tables

| Table | Rows (approx) | Primary Key | Description |
|---|---|---|---|
| `companies` | 101 | `id` (NSE ticker) | Master company reference |
| `profitandloss` | ~1,200 | `(company_id, year)` | Annual P&L statements |
| `balancesheet` | ~1,220 | `(company_id, year)` | Annual balance sheets |
| `cashflow` | ~1,152 | `(company_id, year)` | Annual cash flow statements |
| `analysis` | ~20 | `company_id` | Pre-computed growth text metrics |
| `documents` | ~1,585 | `(company_id, Year)` | BSE annual report URLs |
| `prosandcons` | ~16 | `id` | Qualitative investment insights |
| `sectors` | 101 | `company_id` | GICS-style sector mapping |
| `market_cap` | ~552 | `(company_id, year)` | Simulated valuation multiples |
| `stock_prices` | ~5,520 | `(company_id, date)` | Simulated monthly OHLCV |
| `financial_ratios` | ~1,065 | `(company_id, year)` | 50+ computed KPIs |
| `peer_groups` | 56 | `(company_id, peer_group_name)` | 11 defined peer groups |

> All monetary values in **₹ Crore** unless stated otherwise.
> `market_cap` and `stock_prices` datasets are **SIMULATED** — labelled in dashboard tooltips.

---

## ETL Pipeline — Data Flow

\```
data/raw/*.xlsx              data/supporting/*.xlsx
        │                              │
        ▼                              ▼
    loader.py  ────────────────────────────────────────┐
        │                                              │
        ├── normaliser.py                              │
        │     ├── normalize_year()   Mar-23 → 2023-03  │
        │     └── normalize_ticker() tcs    → TCS      │
        │                                              │
        ├── validator.py                               │
        │     └── 16 DQ rules → validation_failures.csv│
        │                                              │
        └── SQLite writer                              │
              DELETE + append (schema preserved)       │
                     │                                 │
                     ▼                                 │
              data/nifty100.db ◄──────────────────────┘
                     │
           output/load_audit.csv
           output/validation_failures.csv
\```

---

## Data Quality Rules — 16 Rules

### CRITICAL — Row rejected or load halted

| Rule ID | Table | Check | Action |
|---|---|---|---|
| DQ-01 | `companies` | `id` must be unique | Halt load |
| DQ-02 | `profitandloss` | `(company_id, year)` unique | Reject duplicates |
| DQ-03 | `balancesheet` | `(company_id, year)` unique | Reject duplicates |
| DQ-04 | `cashflow` | `(company_id, year)` unique | Reject duplicates |
| DQ-05 | All child tables | `company_id` exists in `companies.id` | Reject orphans |
| DQ-06 | `stock_prices` | `date` matches `YYYY-MM-DD` | Reject bad dates |
| DQ-07 | Time-series tables | `year` matches `YYYY-MM` after normalisation | Reject bad years |
| DQ-08 | All tables | Ticker is 2–12 uppercase alphanumeric chars | Reject bad tickers |

### WARNING — Flagged, not rejected

| Rule ID | Table | Check |
|---|---|---|
| DQ-09 | `profitandloss` | `sales - expenses == operating_profit` within ±1% |
| DQ-10 | `profitandloss` | `opm_percentage` matches computed OPM within ±1pp |
| DQ-11 | `balancesheet` | `total_assets == total_liabilities` within ±1% |
| DQ-12 | `profitandloss` | `sales > 0` |
| DQ-13 | `analysis` | Text fields are regex-parseable for CAGR extraction |
| DQ-14 | `profitandloss` | `eps > 0` when `net_profit > 0` |
| DQ-15 | `profitandloss` | `dividend_payout <= 200%` |
| DQ-16 | Time-series tables | Each company has >= 5 years of data |

---

## KPI Reference — 50+ Computed Metrics

| Category | KPIs |
|---|---|
| Profitability | NPM, OPM, EBIT Margin, ROE, ROCE, ROA |
| Leverage | D/E, ICR, Net Debt, Net Debt/EBITDA |
| Efficiency | Asset Turnover, Fixed Asset Turnover, Working Capital Days |
| Growth | Revenue CAGR 3/5/10yr, PAT CAGR 3/5/10yr, EPS CAGR 5yr |
| Cash Flow | FCF, CFO/PAT, CapEx Intensity, FCF Conversion, FCF Yield |
| Valuation | P/E, P/B, EV/EBITDA, Dividend Yield, Book Value Per Share |
| Composite | Financial Health Score (0–100), Capital Allocation Pattern (8 types) |

---

## Screener Presets — 6 Templates

| Preset | Key Filters | Rank By |
|---|---|---|
| Quality Compounder | ROE>15%, D/E<1, FCF>0, Rev CAGR>10% | Composite Score |
| Value Pick | P/E<20, P/B<3, D/E<2, Div Yield>1% | FCF Yield |
| Growth Accelerator | PAT CAGR>20%, Rev CAGR>15%, D/E<2 | PAT CAGR 5yr |
| Dividend Champion | Div Yield>2%, Payout<80%, FCF>0 | Dividend Yield |
| Debt Free Blue Chip | D/E=0, ROE>12%, Revenue>5000Cr | ROE |
| Turnaround Watch | Rev CAGR 3yr>10%, FCF latest>0 | Rev CAGR 3yr |

---

## Dashboard — 10 Screens

| Page | URL Path | Key Features |
|---|---|---|
| Home | `/` | Market KPIs, sector donut, top-10 ROE |
| Company Profile | `/company` | KPI tiles, P&L charts, ROE/ROCE trend |
| Screener | `/screener` | 10 sliders, 6 presets, CSV export |
| Peer Comparison | `/peers` | Radar chart, percentile table |
| Trend Analysis | `/trends` | Multi-metric overlay, YoY % change |
| Sector Analysis | `/sectors` | Bubble chart, median KPI bars |
| Capital Allocation | `/capital` | Treemap, pattern filter |
| Annual Reports | `/documents` | BSE PDF links per year |
| Valuation | `/valuation` | P/B vs ROE scatter, FCF yield, flags |
| CF Intelligence | `/cashflow_intel` | Pattern distribution, distress alerts |

---

## Makefile Targets

| Command | Action |
|---|---|
| `make init` | Create venv + install all dependencies |
| `make load` | Init schema → run full ETL pipeline |
| `make ratios` | Compute all 50+ KPIs across 5 scripts |
| `make test` | Run full pytest suite → HTML report |
| `make report` | Run DQ review + Sprint 1 verify |
| `make dashboard` | Start Streamlit on `localhost:8501` |
| `make api` | Start FastAPI on `localhost:8000` |
| `make clean` | Delete `__pycache__` + `.pyc` files |

---

## Sprint Roadmap

| Sprint | Days | Focus | Status |
|---|---|---|---|
| Sprint 1 | 01–07 | Data Foundation + ETL | ✅ Complete |
| Sprint 2 | 08–14 | Ratio Engine (50+ KPIs) | ✅ Complete |
| Sprint 3 | 15–21 | Screener, Peers, Dashboard | ✅ Complete |
| Sprint 4 | 22–28 | Valuation + CF Intelligence | ✅ Complete |
| Sprint 5 | 29–35 | PDF Reports + NLP Module | 🔄 In Progress |
| Sprint 6 | 36–45 | FastAPI + ML Clustering + QA | ⏳ Pending |

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.8+ |
| Data Processing | pandas, numpy | >=2.0, >=1.24 |
| Excel I/O | openpyxl | >=3.1 |
| Database | SQLite | 3.x |
| Dashboard | Streamlit | >=1.30 |
| Charts | Plotly, matplotlib | >=5.18, >=3.7 |
| API | FastAPI + Uvicorn | >=0.110, >=0.27 |
| PDF Reports | ReportLab | >=4.1 |
| NLP | NLTK | >=3.8 |
| ML | scikit-learn | >=1.3 |
| Testing | pytest + pytest-html | >=7.4 |
| Config | python-dotenv, PyYAML | >=1.0, >=6.0 |
| Code Quality | black, ruff | >=24.0, >=0.4 |

---

## Environment Variables

\```env
DB_PATH=data/nifty100.db
PORT=8000
LOG_LEVEL=INFO
SIMULATED_DATA_FLAG=True
\```

Copy `config/.env.template` to `.env` and update paths as needed.

---

## Test Coverage

\```
tests/
├── etl/         ← 59 tests  (normaliser, validator, screener)
├── kpi/         ← 56 tests  (ratios, CAGR, cashflow, leverage, peer, radar)
└── dq/          ← 34 tests  (all 16 DQ rules pass + fail cases)

Total: 149 tests | Target: 0 failures before Sprint 6 sign-off
\```

Run full suite:
\```powershell
pytest tests/ --html=reports/pytest_report.html -v
\```

---

## AI Disclosure

This project was developed with significant AI assistance (Claude by Anthropic)
for code generation, ETL logic, KPI formula implementation, and documentation.
All financial formulas, DQ rules, and analytical outputs have been reviewed and
validated against source financial data by the project team.

---

*Nifty 100 Financial Intelligence Platform*
*Version 1.0 | June 2026 | Data Analytics Division*
*Confidential — Internal Use Only*
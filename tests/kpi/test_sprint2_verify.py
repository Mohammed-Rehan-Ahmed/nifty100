import sqlite3, os, pandas as pd
from dotenv import load_dotenv
load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")

def conn(): return sqlite3.connect(DB_PATH)

def test_financial_ratios_row_count():
    n = conn().execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    assert n >= 1100, f"Only {n} rows"

def test_roe_column_exists():
    df = pd.read_sql("SELECT return_on_equity_pct FROM financial_ratios LIMIT 1", conn())
    assert "return_on_equity_pct" in df.columns

def test_cagr_table_exists():
    n = conn().execute("SELECT COUNT(*) FROM cagr_metrics").fetchone()[0]
    assert n >= 90

def test_capital_allocation_exists():
    n = conn().execute("SELECT COUNT(*) FROM capital_allocation").fetchone()[0]
    assert n >= 1000

def test_sector_benchmarks_exists():
    n = conn().execute("SELECT COUNT(*) FROM sector_benchmarks").fetchone()[0]
    assert n >= 5

def test_no_null_company_id():
    n = conn().execute(
        "SELECT COUNT(*) FROM financial_ratios WHERE company_id IS NULL"
    ).fetchone()[0]
    assert n == 0

def test_de_non_negative():
    n = conn().execute(
        "SELECT COUNT(*) FROM financial_ratios WHERE debt_to_equity < 0"
    ).fetchone()[0]
    assert n == 0

def test_roce_notes_generated():
    assert os.path.exists("data/sector_roce_notes.csv")
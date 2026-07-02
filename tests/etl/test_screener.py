import sys, sqlite3, os
sys.path.insert(0, "src/analytics")
import pandas as pd
from screener.engine import apply_filters, compute_composite_score
from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")

def sample():
    return pd.DataFrame([
        {"company_id":"TCS","return_on_equity_pct":30,"debt_to_equity":0,
         "free_cash_flow_cr":1000,"revenue_cagr_5yr":12,"pat_cagr_5yr":15,
         "pe_ratio":25,"pb_ratio":8,"dividend_yield_pct":1.5,
         "return_on_capital_pct":25,"net_profit_margin_pct":20,
         "cfo_pat_ratio":1.1,"broad_sector":"IT","sales":50000,
         "dividend_payout_ratio_pct":45,"interest_coverage":None},
        {"company_id":"SBIN","return_on_equity_pct":10,"debt_to_equity":8,
         "free_cash_flow_cr":-500,"revenue_cagr_5yr":5,"pat_cagr_5yr":8,
         "pe_ratio":10,"pb_ratio":1,"dividend_yield_pct":3.0,
         "return_on_capital_pct":8,"net_profit_margin_pct":12,
         "cfo_pat_ratio":0.8,"broad_sector":"Financials","sales":100000,
         "dividend_payout_ratio_pct":20,"interest_coverage":1.2},
    ])

def test_min_roe_filter():
    df = apply_filters(sample(), {"min_roe": 15})
    assert len(df) == 1
    assert df.iloc[0]["company_id"] == "TCS"

def test_max_de_filter():
    df = apply_filters(sample(), {"max_de": 1})
    assert len(df) == 1

def test_min_fcf_filter():
    df = apply_filters(sample(), {"min_fcf": 0})
    assert len(df) == 1

def test_sector_filter():
    df = apply_filters(sample(), {"sector": "IT"})
    assert len(df) == 1

def test_no_filter():
    df = apply_filters(sample(), {})
    assert len(df) == 2

def test_composite_score_range():
    df = compute_composite_score(sample())
    assert df["composite_score"].between(0, 100).all()

def test_composite_score_ordering():
    df = compute_composite_score(sample())
    df = df.sort_values("composite_score", ascending=False)
    assert df.iloc[0]["company_id"] == "TCS"
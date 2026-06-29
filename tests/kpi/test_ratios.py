import sys, math
sys.path.insert(0, "src/analytics")
import pandas as pd, numpy as np
from ratios import compute_profitability, compute_leverage, safe_div

def make_row(**kwargs):
    defaults = dict(net_profit=100, sales=500, operating_profit=80,
                    depreciation=10, equity_capital=200, reserves=300,
                    borrowings=100, total_assets=600, investments=0,
                    other_income=5, interest=20, fixed_assets=150,
                    other_asset=200, other_liabilities=50,
                    operating_activity=90, investing_activity=-40,
                    financing_activity=-30, eps=10, dividend_payout=30,
                    face_value=1, broad_sector="IT",profit_before_tax=85)
    defaults.update(kwargs)
    return pd.DataFrame([defaults])

def test_npm():
    df = compute_profitability(make_row())
    assert round(df["net_profit_margin_pct"].iloc[0], 1) == 20.0

def test_roe_positive():
    df = compute_profitability(make_row())
    assert round(df["return_on_equity_pct"].iloc[0], 1) == 20.0

def test_roe_neg_equity():
    df = compute_profitability(make_row(equity_capital=-500, reserves=0))
    assert pd.isna(df["return_on_equity_pct"].iloc[0])

def test_de_debtfree():
    df = compute_profitability(make_row())
    df = compute_leverage(df, {"Financials"})
    row = make_row(borrowings=0)
    row = compute_profitability(row)
    row = compute_leverage(row, {"Financials"})
    assert row["debt_to_equity"].iloc[0] == 0

def test_icr_debtfree():
    df = compute_profitability(make_row(interest=0))
    df = compute_leverage(df, {"Financials"})
    assert pd.isna(df["interest_coverage"].iloc[0])
    assert df["icr_display"].iloc[0] == "Debt Free"

def test_safe_div_zero():
    n = pd.Series([10])
    d = pd.Series([0])
    assert pd.isna(safe_div(n, d)[0])

def test_roce():
    df = compute_profitability(make_row())
    ebit = 85 + 20  # profit_before_tax + interest
    cap  = 200 + 300 + 100
    expected = round(ebit / cap * 100, 4)
    assert round(df["return_on_capital_pct"].iloc[0], 4) == expected
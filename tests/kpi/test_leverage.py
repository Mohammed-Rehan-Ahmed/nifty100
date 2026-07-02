import sys
sys.path.insert(0, "src/analytics")
import pandas as pd, numpy as np
from ratios import compute_profitability, compute_leverage

def base():
    return pd.DataFrame([{
        "net_profit":100,"sales":500,"operating_profit":80,"profit_before_tax":85,
        "depreciation":10,"equity_capital":200,"reserves":300,
        "borrowings":200,"total_assets":700,"investments":50,
        "other_income":5,"interest":20,"fixed_assets":150,
        "other_asset":200,"other_liabilities":50,"broad_sector":"IT"
    }])

def prep(df):
    df = compute_profitability(df)
    return compute_leverage(df, {"Financials"})

def test_de_ratio():
    df = prep(base())
    assert round(df["debt_to_equity"].iloc[0], 2) == round(200/500, 2)

def test_de_debtfree():
    b = base(); b["borrowings"] = 0
    df = prep(b)
    assert df["debt_to_equity"].iloc[0] == 0

def test_de_high_flag_nonfinancial():
    b = base(); b["borrowings"] = 3000
    df = prep(b)
    assert df["de_flag"].iloc[0] == "HIGH_DE"

def test_de_high_flag_financial():
    b = base(); b["borrowings"] = 3000; b["broad_sector"] = "Financials"
    df = prep(b)
    assert df["de_flag"].iloc[0] == ""

def test_icr():
    df = prep(base())
    expected = round((80 + 5) / 20, 2)
    assert round(df["interest_coverage"].iloc[0], 2) == expected

def test_net_debt():
    df = prep(base())
    assert df["net_debt_cr"].iloc[0] == 200 - 50

def test_asset_turnover():
    from ratios import compute_efficiency
    df = compute_profitability(base())
    df = compute_efficiency(df)
    assert round(df["asset_turnover"].iloc[0], 4) == round(500/700, 4)
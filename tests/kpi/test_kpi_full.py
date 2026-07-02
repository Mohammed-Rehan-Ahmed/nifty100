import sys, os
sys.path.insert(0, "src/analytics")
import pandas as pd, numpy as np
from ratios import compute_profitability, compute_leverage, compute_efficiency, safe_div
from cagr import compute_cagr
from cashflow_kpis import classify_pattern, cfo_quality, capex_category

# ── Profitability ──────────────────────────────────────────────────────────────
def base():
    return pd.DataFrame([{
        "net_profit":100,"sales":500,"operating_profit":80,"depreciation":10,
        "equity_capital":200,"reserves":300,"borrowings":100,"total_assets":600,
        "investments":50,"other_income":5,"interest":20,"fixed_assets":150,
        "other_asset":200,"other_liabilities":50,"broad_sector":"IT","profit_before_tax":85
    }])

def test_npm():
    df = compute_profitability(base())
    assert round(df["net_profit_margin_pct"].iloc[0],1) == 20.0

def test_opm():
    df = compute_profitability(base())
    assert round(df["operating_profit_margin_pct"].iloc[0],1) == 16.0

def test_roe_positive():
    df = compute_profitability(base())
    assert round(df["return_on_equity_pct"].iloc[0],1) == 20.0

def test_roe_neg_equity():
    b = base(); b["equity_capital"]=-500; b["reserves"]=0
    df = compute_profitability(b)
    assert pd.isna(df["return_on_equity_pct"].iloc[0])

def test_roce():
    df = compute_profitability(base())
    ebit = 85+20
    ce   = 200+300+100
    assert round(df["return_on_capital_pct"].iloc[0],2) == round(ebit/ce*100,2)

def test_roa():
    df = compute_profitability(base())
    assert round(df["return_on_assets_pct"].iloc[0],2) == round(100/600*100,2)

# ── Leverage ───────────────────────────────────────────────────────────────────
def prep(df):
    df = compute_profitability(df)
    return compute_leverage(df, {"Financials"})

def test_de_ratio():
    df = prep(base())
    assert round(df["debt_to_equity"].iloc[0],4) == round(100/500,4)

def test_de_debtfree():
    b = base(); b["borrowings"]=0
    df = prep(b)
    assert df["debt_to_equity"].iloc[0] == 0

def test_de_high_flag():
    b = base(); b["borrowings"]=3000
    df = prep(b)
    assert df["de_flag"].iloc[0] == "HIGH_DE"

def test_de_flag_exempt_financial():
    b = base(); b["borrowings"]=3000; b["broad_sector"]="Financials"
    df = prep(b)
    assert df["de_flag"].iloc[0] == ""

def test_icr():
    df = prep(base())
    assert round(df["interest_coverage"].iloc[0],2) == round(85/20,2)

def test_icr_debtfree():
    b = base(); b["interest"]=0
    df = prep(b)
    assert pd.isna(df["interest_coverage"].iloc[0])
    assert df["icr_display"].iloc[0] == "Debt Free"

def test_net_debt():
    df = prep(base())
    assert df["net_debt_cr"].iloc[0] == 100-50

# ── Efficiency ─────────────────────────────────────────────────────────────────
def test_asset_turnover():
    df = compute_profitability(base())
    df = compute_efficiency(df)
    assert round(df["asset_turnover"].iloc[0],4) == round(500/600,4)

def test_safe_div_zero():
    assert pd.isna(safe_div(pd.Series([10]), pd.Series([0]))[0])

# ── CAGR ───────────────────────────────────────────────────────────────────────
def test_cagr_normal():
    v, f = compute_cagr(100, 161.05, 5)
    assert f=="OK" and abs(v-10.0)<0.1

def test_cagr_turnaround():
    v, f = compute_cagr(-100, 200, 5)
    assert f=="TURNAROUND"

def test_cagr_zero_base():
    v, f = compute_cagr(0, 100, 5)
    assert f=="ZERO_BASE"

def test_cagr_decline_to_loss():
    v, f = compute_cagr(100, -50, 5)
    assert f=="DECLINE_TO_LOSS"

# ── Cash Flow ──────────────────────────────────────────────────────────────────
def test_pattern_reinvestor():
    assert classify_pattern(100,-50,-30) == "Reinvestor"

def test_pattern_distress():
    assert classify_pattern(-50,-10,100) == "Distress"
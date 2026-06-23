import sys
sys.path.insert(0, "src/etl")
import pytest
import pandas as pd
from validator import (
    dq01_company_pk_unique, dq02_pl_pk_unique, dq03_bs_pk_unique,
    dq04_cf_pk_unique, dq05_fk_integrity, dq06_stock_price_date_format,
    dq07_year_format, dq08_ticker_format, dq09_opm_crosscheck,
    dq10_opm_pct_crosscheck, dq11_bs_balance, dq12_positive_sales,
    dq14_eps_sign, dq15_dividend_payout_cap, dq16_coverage_check,
    run_all_validations
)

# ── Minimal fixtures ───────────────────────────────────────────────────────────
def co():
    return pd.DataFrame([{"id":"TCS"},{"id":"INFY"}])

def pl():
    return pd.DataFrame([
        {"company_id":"TCS", "year":"2023-03","sales":100,"expenses":75,
         "operating_profit":25,"opm_percentage":25.0,
         "net_profit":20,"eps":10,"dividend_payout":30},
        {"company_id":"INFY","year":"2023-03","sales":80,"expenses":60,
         "operating_profit":20,"opm_percentage":25.0,
         "net_profit":15,"eps":8,"dividend_payout":40},
    ])

def bs():
    return pd.DataFrame([
        {"company_id":"TCS", "year":"2023-03","total_assets":500,"total_liabilities":500},
        {"company_id":"INFY","year":"2023-03","total_assets":300,"total_liabilities":300},
    ])

def cf():
    return pd.DataFrame([
        {"company_id":"TCS", "year":"2023-03"},
        {"company_id":"INFY","year":"2023-03"},
    ])

def sp():
    return pd.DataFrame([
        {"company_id":"TCS", "date":"2023-01-01"},
        {"company_id":"INFY","date":"2023-06-01"},
    ])

def dfs():
    return {"companies":co(),"profitandloss":pl(),
            "balancesheet":bs(),"cashflow":cf(),"stock_prices":sp()}

def f(): return []


# ── DQ-01 ──────────────────────────────────────────────────────────────────────
def test_dq01_pass():
    failures=f(); dq01_company_pk_unique(dfs(),failures)
    assert not failures

def test_dq01_fail():
    d=dfs(); d["companies"]=pd.DataFrame([{"id":"TCS"},{"id":"TCS"}])
    failures=f(); dq01_company_pk_unique(d,failures)
    assert any(x["rule_id"]=="DQ-01" and x["severity"]=="CRITICAL" for x in failures)


# ── DQ-02 ──────────────────────────────────────────────────────────────────────
def test_dq02_pass():
    failures=f(); dq02_pl_pk_unique(dfs(),failures)
    assert not failures

def test_dq02_fail():
    d=dfs(); d["profitandloss"]=pd.concat([pl(),pl()]).reset_index(drop=True)
    failures=f(); dq02_pl_pk_unique(d,failures)
    assert any(x["rule_id"]=="DQ-02" for x in failures)


# ── DQ-03 ──────────────────────────────────────────────────────────────────────
def test_dq03_pass():
    failures=f(); dq03_bs_pk_unique(dfs(),failures)
    assert not failures

def test_dq03_fail():
    d=dfs(); d["balancesheet"]=pd.concat([bs(),bs()]).reset_index(drop=True)
    failures=f(); dq03_bs_pk_unique(d,failures)
    assert any(x["rule_id"]=="DQ-03" for x in failures)


# ── DQ-04 ──────────────────────────────────────────────────────────────────────
def test_dq04_pass():
    failures=f(); dq04_cf_pk_unique(dfs(),failures)
    assert not failures

def test_dq04_fail():
    d=dfs(); d["cashflow"]=pd.concat([cf(),cf()]).reset_index(drop=True)
    failures=f(); dq04_cf_pk_unique(d,failures)
    assert any(x["rule_id"]=="DQ-04" for x in failures)


# ── DQ-05 ──────────────────────────────────────────────────────────────────────
def test_dq05_pass():
    failures=f(); dq05_fk_integrity(dfs(),failures)
    assert not failures

def test_dq05_fail():
    d=dfs()
    d["profitandloss"]=pd.DataFrame([
        {"company_id":"GHOST","year":"2023-03","sales":100,"expenses":75,
         "operating_profit":25,"opm_percentage":25,"net_profit":20,
         "eps":10,"dividend_payout":30}
    ])
    failures=f(); dq05_fk_integrity(d,failures)
    assert any(x["rule_id"]=="DQ-05" and x["severity"]=="CRITICAL" for x in failures)


# ── DQ-06 ──────────────────────────────────────────────────────────────────────
def test_dq06_pass():
    failures=f(); dq06_stock_price_date_format(dfs(),failures)
    assert not failures

def test_dq06_pass_timestamp():
    d=dfs(); d["stock_prices"]=pd.DataFrame([{"company_id":"TCS","date":"2023-01-01 00:00:00"}])
    failures=f(); dq06_stock_price_date_format(d,failures)
    assert not failures

def test_dq06_fail():
    d=dfs(); d["stock_prices"]=pd.DataFrame([{"company_id":"TCS","date":"01-01-2023"}])
    failures=f(); dq06_stock_price_date_format(d,failures)
    assert any(x["rule_id"]=="DQ-06" and x["severity"]=="CRITICAL" for x in failures)


# ── DQ-07 ──────────────────────────────────────────────────────────────────────
def test_dq07_pass():
    failures=f(); dq07_year_format(dfs(),failures)
    assert not failures

def test_dq07_fail():
    d=dfs(); d["profitandloss"]=pl().copy()
    d["profitandloss"]["year"]="BAD"
    failures=f(); dq07_year_format(d,failures)
    assert any(x["rule_id"]=="DQ-07" and x["severity"]=="CRITICAL" for x in failures)


# ── DQ-08 ──────────────────────────────────────────────────────────────────────
def test_dq08_pass():
    failures=f(); dq08_ticker_format(dfs(),failures)
    assert not failures

def test_dq08_fail():
    d=dfs(); d["companies"]=pd.DataFrame([{"id":"X"}])
    failures=f(); dq08_ticker_format(d,failures)
    assert any(x["rule_id"]=="DQ-08" and x["severity"]=="CRITICAL" for x in failures)


# ── DQ-09 ──────────────────────────────────────────────────────────────────────
def test_dq09_pass():
    failures=f(); dq09_opm_crosscheck(dfs(),failures)
    assert not failures

def test_dq09_fail():
    d=dfs(); d["profitandloss"]=pl().copy()
    d["profitandloss"].loc[0,"operating_profit"]=99
    failures=f(); dq09_opm_crosscheck(d,failures)
    assert any(x["rule_id"]=="DQ-09" for x in failures)


# ── DQ-10 ──────────────────────────────────────────────────────────────────────
def test_dq10_pass():
    failures=f(); dq10_opm_pct_crosscheck(dfs(),failures)
    assert not failures

def test_dq10_fail():
    d=dfs(); d["profitandloss"]=pl().copy()
    d["profitandloss"].loc[0,"opm_percentage"]=99
    failures=f(); dq10_opm_pct_crosscheck(d,failures)
    assert any(x["rule_id"]=="DQ-10" for x in failures)


# ── DQ-11 ──────────────────────────────────────────────────────────────────────
def test_dq11_pass():
    failures=f(); dq11_bs_balance(dfs(),failures)
    assert not failures

def test_dq11_fail():
    d=dfs(); d["balancesheet"]=bs().copy()
    d["balancesheet"].loc[0,"total_liabilities"]=600
    failures=f(); dq11_bs_balance(d,failures)
    assert any(x["rule_id"]=="DQ-11" and x["severity"]=="WARNING" for x in failures)


# ── DQ-12 ──────────────────────────────────────────────────────────────────────
def test_dq12_pass():
    failures=f(); dq12_positive_sales(dfs(),failures)
    assert not failures

def test_dq12_fail():
    d=dfs(); d["profitandloss"]=pl().copy()
    d["profitandloss"].loc[0,"sales"]=0
    failures=f(); dq12_positive_sales(d,failures)
    assert any(x["rule_id"]=="DQ-12" for x in failures)


# ── DQ-14 ──────────────────────────────────────────────────────────────────────
def test_dq14_pass():
    failures=f(); dq14_eps_sign(dfs(),failures)
    assert not failures

def test_dq14_fail():
    d=dfs(); d["profitandloss"]=pl().copy()
    d["profitandloss"].loc[0,"eps"]=-5
    failures=f(); dq14_eps_sign(d,failures)
    assert any(x["rule_id"]=="DQ-14" for x in failures)


# ── DQ-15 ──────────────────────────────────────────────────────────────────────
def test_dq15_pass():
    failures=f(); dq15_dividend_payout_cap(dfs(),failures)
    assert not failures

def test_dq15_fail():
    d=dfs(); d["profitandloss"]=pl().copy()
    d["profitandloss"].loc[0,"dividend_payout"]=250
    failures=f(); dq15_dividend_payout_cap(d,failures)
    assert any(x["rule_id"]=="DQ-15" for x in failures)


# ── DQ-16 ──────────────────────────────────────────────────────────────────────
def test_dq16_fail_low_coverage():
    failures=f(); dq16_coverage_check(dfs(),failures)
    assert any(x["rule_id"]=="DQ-16" for x in failures)

def test_dq16_pass_sufficient():
    d=dfs()
    d["companies"]=pd.DataFrame([{"id":"TCS"}])
    d["profitandloss"]=pd.DataFrame([
        {"company_id":"TCS","year":f"201{i}-03","sales":100,"expenses":75,
         "operating_profit":25,"opm_percentage":25,"net_profit":20,
         "eps":10,"dividend_payout":30}
        for i in range(6)
    ])
    d["balancesheet"]=pd.DataFrame([
        {"company_id":"TCS","year":f"201{i}-03",
         "total_assets":500,"total_liabilities":500}
        for i in range(6)
    ])
    d["cashflow"]=pd.DataFrame([
        {"company_id":"TCS","year":f"201{i}-03"} for i in range(6)
    ])
    failures=f(); dq16_coverage_check(d,failures)
    assert not any(x["rule_id"]=="DQ-16" and x["company_id"]=="TCS" for x in failures)


# ── Runner ─────────────────────────────────────────────────────────────────────
def test_run_all_returns_list():
    assert isinstance(run_all_validations(dfs()), list)

def test_run_all_schema():
    for r in run_all_validations(dfs()):
        for k in ("rule_id","severity","table","field","issue"):
            assert k in r
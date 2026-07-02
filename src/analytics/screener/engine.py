import os, sqlite3, logging
import pandas as pd
import numpy as np
import yaml
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
logger = logging.getLogger(__name__)


def load_config():
    with open("config/screener_config.yaml") as f:
        return yaml.safe_load(f)


def load_universe(conn):
    df = pd.read_sql("""
        SELECT r.*, s.broad_sector, s.sub_sector,
               c.company_name, m.pe_ratio, m.pb_ratio,
               m.dividend_yield_pct, m.market_cap_crore
        FROM financial_ratios r
        LEFT JOIN sectors s ON r.company_id = s.company_id
        LEFT JOIN companies c ON r.company_id = c.id
        LEFT JOIN market_cap m ON r.company_id = m.company_id
            AND m.year = r.year
    """, conn)
    # Keep latest year per company
    df = df.sort_values("year").groupby("company_id").last().reset_index()
    return df


def apply_filters(df, filters: dict) -> pd.DataFrame:
    mask = pd.Series([True] * len(df), index=df.index)

    ops = {
        "min_roe":              ("return_on_equity_pct",      ">="),
        "max_de":               ("debt_to_equity",             "<="),
        "min_fcf":              ("free_cash_flow_cr",          ">="),
        "min_revenue_cagr_5yr": ("revenue_cagr_5yr",          ">="),
        "min_revenue_cagr_3yr": ("revenue_cagr_3yr",          ">="),
        "min_pat_cagr_5yr":     ("pat_cagr_5yr",              ">="),
        "max_pe":               ("pe_ratio",                   "<="),
        "max_pb":               ("pb_ratio",                   "<="),
        "min_dividend_yield":   ("dividend_yield_pct",        ">="),
        "max_dividend_payout":  ("dividend_payout_ratio_pct", "<="),
        "min_revenue":          ("sales",                      ">="),
        "min_fcf_latest":       ("free_cash_flow_cr",          ">="),
        "min_roce":             ("return_on_capital_pct",      ">="),
        "min_npm":              ("net_profit_margin_pct",      ">="),
        "max_de_strict":        ("debt_to_equity",             "=="),
    }

    for key, val in filters.items():
        if key == "sector":
            mask &= df["broad_sector"].str.lower() == str(val).lower()
            continue
        if key not in ops:
            continue
        col, op = ops[key]
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        if op == ">=": mask &= series >= val
        elif op == "<=": mask &= series <= val
        elif op == "==": mask &= series == val

    return df[mask].copy()


def compute_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    cfg = load_config()["thresholds"]["composite_score"]

    def winsorise(s):
        lo, hi = s.quantile(0.10), s.quantile(0.90)
        return s.clip(lo, hi)

    def scale(s):
        s = winsorise(s.fillna(s.median()))
        rng = s.max() - s.min()
        return ((s - s.min()) / rng * 100) if rng > 0 else pd.Series(50, index=s.index)

    scores = pd.DataFrame(index=df.index)

    # Profitability 35%
    roe   = scale(pd.to_numeric(df.get("return_on_equity_pct",  0), errors="coerce"))
    roce  = scale(pd.to_numeric(df.get("return_on_capital_pct", 0), errors="coerce"))
    npm   = scale(pd.to_numeric(df.get("net_profit_margin_pct", 0), errors="coerce"))
    scores["profitability"] = roe*0.15 + roce*0.10 + npm*0.10

    # Cash Quality 30%
    fcf_cagr = scale(pd.to_numeric(df.get("revenue_cagr_5yr", 0), errors="coerce"))
    cfo_pat  = scale(pd.to_numeric(df.get("cfo_pat_ratio",    0), errors="coerce"))
    fcf_flag = pd.to_numeric(df.get("free_cash_flow_cr", 0), errors="coerce").apply(
        lambda x: 100 if x > 0 else 0)
    scores["cash_quality"] = fcf_cagr*0.15 + cfo_pat*0.10 + fcf_flag*0.05

    # Growth 20%
    rev_cagr = scale(pd.to_numeric(df.get("revenue_cagr_5yr", 0), errors="coerce"))
    pat_cagr = scale(pd.to_numeric(df.get("pat_cagr_5yr",     0), errors="coerce"))
    scores["growth"] = rev_cagr*0.10 + pat_cagr*0.10

    # Leverage 15%
    de = pd.to_numeric(df.get("debt_to_equity", 0), errors="coerce").fillna(0)
    de_score = de.apply(lambda x: 100 if x==0 else 85 if x<=0.5 else
                        70 if x<=1 else 50 if x<=2 else 0)
    icr = pd.to_numeric(df.get("interest_coverage", 0), errors="coerce").fillna(0)
    icr_score = icr.apply(lambda x: 100 if x>=10 else 75 if x>=5 else
                          50 if x>=3 else 0)
    scores["leverage"] = de_score*0.10 + icr_score*0.05

    w = cfg
    df["composite_score"] = (
        scores["profitability"] * w["profitability_weight"] +
        scores["cash_quality"]  * w["cash_quality_weight"]  +
        scores["growth"]        * w["growth_weight"]         +
        scores["leverage"]      * w["leverage_weight"]
    ).round(2)
    return df


def run_preset(name: str, filters: dict, rank_by: str, conn) -> pd.DataFrame:
    universe = load_universe(conn)
    result   = apply_filters(universe, filters)
    result   = compute_composite_score(result)
    result   = result.sort_values(rank_by, ascending=False)
    logger.info("Preset '%s': %d companies", name, len(result))
    return result


def run_all_presets():
    conn = sqlite3.connect(DB_PATH)
    cfg  = load_config()["presets"]

    writer = pd.ExcelWriter("data/screener_output.xlsx", engine="openpyxl")

    DISPLAY_COLS = [
        "company_id","company_name","broad_sector",
        "return_on_equity_pct","return_on_capital_pct","net_profit_margin_pct",
        "debt_to_equity","free_cash_flow_cr","revenue_cagr_5yr","pat_cagr_5yr",
        "pe_ratio","pb_ratio","dividend_yield_pct","composite_score"
    ]

    for preset_name, preset_cfg in cfg.items():
        filters  = {k: v for k, v in preset_cfg.items() if k != "rank_by"}
        rank_by  = preset_cfg.get("rank_by", "composite_score")
        if rank_by not in ["composite_score","return_on_equity_pct",
                           "revenue_cagr_5yr","pat_cagr_5yr",
                           "dividend_yield_pct","fcf_yield_pct"]:
            rank_by = "composite_score"

        result = run_preset(preset_name, filters, rank_by, conn)
        cols   = [c for c in DISPLAY_COLS if c in result.columns]
        result[cols].to_excel(writer, sheet_name=preset_name[:31], index=False)
        print(f"  {preset_name:25s}: {len(result):3d} companies")

    writer.close()
    conn.close()
    print("\nSaved → data/screener_output.xlsx")


if __name__ == "__main__":
    run_all_presets()
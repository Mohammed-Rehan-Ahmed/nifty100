import os, sqlite3, logging
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
logger = logging.getLogger(__name__)


def run_merge():
    conn = sqlite3.connect(DB_PATH)

    ratios = pd.read_sql("SELECT * FROM financial_ratios", conn)
    cagr   = pd.read_sql("SELECT * FROM cagr_metrics", conn)
    alloc  = pd.read_sql("SELECT company_id, year, pattern_label, free_cash_flow_cr, capex_cr, cfo_pat_ratio, capex_intensity_pct, fcf_conversion_pct FROM capital_allocation", conn)
    mc     = pd.read_sql("SELECT company_id, year, pe_ratio, pb_ratio, ev_ebitda, dividend_yield_pct, market_cap_crore FROM market_cap", conn)
    mc["year"] = mc["year"].astype(str)

    # Merge ratios + cashflow allocation
    df = ratios.merge(alloc, on=["company_id","year"], how="left", suffixes=("","_ca"))

    # Drop duplicate cashflow cols already in ratios
    for col in ["free_cash_flow_cr","capex_cr","cfo_pat_ratio","capex_intensity_pct","fcf_conversion_pct"]:
        if f"{col}_ca" in df.columns:
            df.drop(columns=[f"{col}_ca"], inplace=True)

    # Merge CAGR (latest year only — one row per company)
    cagr_cols = ["company_id"] + [c for c in cagr.columns if "cagr" in c]
    df = df.merge(cagr[cagr_cols], on="company_id", how="left")

    # Merge market cap valuation
    df = df.merge(mc, on=["company_id","year"], how="left")

    # FCF Yield
    df["fcf_yield_pct"] = np.where(
        df["market_cap_crore"].isna() | (df["market_cap_crore"] <= 0), np.nan,
        df["free_cash_flow_cr"] / df["market_cap_crore"] * 100
    )

    # Write final table
    df.to_sql("financial_ratios", conn, if_exists="replace", index=False)
    df.to_csv("data/financial_ratios_final.csv", index=False)

    logger.info("financial_ratios final: %d rows, %d cols", len(df), len(df.columns))
    print(f"Rows: {len(df)} | Columns: {len(df.columns)}")
    print(df[["company_id","year","return_on_equity_pct","debt_to_equity",
              "free_cash_flow_cr","revenue_cagr_5yr"]].head(10).to_string())

    conn.close()


def validate_sample():
    """Spot-check 5 companies vs companies.xlsx pre-computed values."""
    conn = sqlite3.connect(DB_PATH)
    co   = pd.read_sql("SELECT id, roe_percentage, roce_percentage FROM companies", conn)
    latest = pd.read_sql("""
        SELECT company_id, year, return_on_equity_pct, return_on_capital_pct
        FROM financial_ratios
        WHERE year = (SELECT MAX(year) FROM financial_ratios WHERE company_id = financial_ratios.company_id)
    """, conn)

    merged = latest.merge(co, left_on="company_id", right_on="id")

    EDGE_CASES = []
    print("\n===== ROE SPOT CHECK =====")
    for _, row in merged.head(10).iterrows():
        diff = abs((row["return_on_equity_pct"] or 0) - (row["roe_percentage"] or 0))
        status = "✓" if diff <= 5 else "⚠"
        print(f"  {status} {row['company_id']:15s} computed={round(row['return_on_equity_pct'] or 0,2):7.2f}%  source={row['roe_percentage']}%  diff={round(diff,2)}")
        if diff > 5:
            EDGE_CASES.append({"company_id": row["company_id"],
                               "metric": "ROE",
                               "computed": row["return_on_equity_pct"],
                               "source": row["roe_percentage"],
                               "diff": diff,
                               "note": "Version diff or year mismatch"})

    pd.DataFrame(EDGE_CASES).to_csv("data/ratio_edge_cases.csv", index=False)
    print(f"\nEdge cases logged: {len(EDGE_CASES)} → data/ratio_edge_cases.csv")
    conn.close()


if __name__ == "__main__":
    run_merge()
    validate_sample()
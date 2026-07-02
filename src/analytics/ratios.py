import os, sqlite3, logging
import pandas as pd
import numpy as np
from dotenv import load_dotenv


load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FINANCIAL_SECTORS = {"Financials"}


def get_data(conn):
    pl = pd.read_sql("SELECT * FROM profitandloss", conn)
    bs = pd.read_sql("SELECT * FROM balancesheet", conn)
    cf = pd.read_sql("SELECT * FROM cashflow", conn)
    se = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    return pl, bs, cf, se


def safe_div(num, den):
    """Divide series, return None where den is 0 or None."""
    return np.where((den == 0) | den.isna() | num.isna(), np.nan, num / den)


def compute_profitability(df):
    """NPM, OPM, EBIT Margin, ROE, ROCE, ROA."""
    # NPM
    df["net_profit_margin_pct"] = safe_div(df["net_profit"], df["sales"]) * 100

    # OPM
    df["operating_profit_margin_pct"] = safe_div(df["operating_profit"], df["sales"]) * 100

    # EBIT = operating_profit - depreciation
    df["ebit"] = df["profit_before_tax"] + df["interest"].fillna(0)
    df["ebit_margin_pct"] = safe_div(df["ebit"], df["sales"]) * 100

    # Equity
    df["total_equity"] = df["equity_capital"].fillna(0) + df["reserves"].fillna(0)

    # ROE — None if equity <= 0
    df["return_on_equity_pct"] = np.where(
        df["total_equity"] <= 0, np.nan,
        safe_div(df["net_profit"], df["total_equity"]) * 100
    )

    # ROCE = EBIT / (equity + borrowings)
    df["capital_employed"] = df["total_equity"] + df["borrowings"].fillna(0)
    df["return_on_capital_pct"] = np.where(
        df["capital_employed"] <= 0, np.nan,
        safe_div(df["ebit"], df["capital_employed"]) * 100
    )

    # ROA
    df["return_on_assets_pct"] = np.where(
        df["total_assets"] <= 0, np.nan,
        safe_div(df["net_profit"], df["total_assets"]) * 100
    )
    return df


def compute_leverage(df, financial_sectors):
    """D/E, ICR, Net Debt, Net Debt/EBITDA."""
    df["debt_to_equity"] = np.where(
        df["total_equity"] <= 0, np.nan,
        np.where(df["borrowings"].fillna(0) == 0, 0,
                 safe_div(df["borrowings"].fillna(0), df["total_equity"]))
    )
    # Flag high D/E for non-financials
    df["de_flag"] = np.where(
        (~df["broad_sector"].isin(financial_sectors)) & (df["debt_to_equity"] > 5),
        "HIGH_DE", ""
    )

    # ICR = (operating_profit + other_income) / interest
    df["interest_coverage"] = np.where(
        df["interest"].fillna(0) == 0, np.nan,
        safe_div(df["operating_profit"] + df["other_income"].fillna(0),
                 df["interest"].fillna(0))
    )
    df["icr_display"] = df["interest_coverage"].apply(
        lambda x: "Debt Free" if pd.isna(x) else round(x, 2)
    )

    df["icr_warning"] = np.where(
        df["interest_coverage"] < 1.5, True, False
    )

    # Net Debt = borrowings - investments
    df["net_debt_cr"] = df["borrowings"].fillna(0) - df["investments"].fillna(0)

    # Net Debt / EBITDA
    df["net_debt_to_ebitda"] = np.where(
        df["operating_profit"] <= 0, np.nan,
        safe_div(df["net_debt_cr"], df["operating_profit"])
    )
    return df


def compute_efficiency(df):
    """Asset Turnover, Fixed Asset Turnover, Working Capital Days."""
    df["asset_turnover"] = np.where(
        df["total_assets"] <= 0, np.nan,
        safe_div(df["sales"], df["total_assets"])
    )
    df["fixed_asset_turnover"] = np.where(
        df["fixed_assets"].fillna(0) <= 0, np.nan,
        safe_div(df["sales"], df["fixed_assets"].fillna(0))
    )
    df["working_capital_days"] = np.where(
        df["sales"] <= 0, np.nan,
        safe_div(df["other_asset"].fillna(0) - df["other_liabilities"].fillna(0),
                 df["sales"]) * 365
    )
    return df


def compute_cashflow_kpis(df):
    """FCF, CFO/PAT, CapEx Intensity, FCF Conversion."""
    df["free_cash_flow_cr"] = (df["operating_activity"].fillna(0) +
                               df["investing_activity"].fillna(0))
    df["cash_from_operations_cr"] = df["operating_activity"].fillna(0)
    df["capex_cr"] = df["investing_activity"].fillna(0).abs()

    df["cfo_pat_ratio"] = np.where(
        df["net_profit"] == 0, np.nan,
        safe_div(df["operating_activity"].fillna(0), df["net_profit"])
    )
    df["capex_intensity_pct"] = np.where(
        df["sales"] <= 0, np.nan,
        safe_div(df["capex_cr"], df["sales"]) * 100
    )
    df["fcf_conversion_pct"] = np.where(
        df["operating_profit"] <= 0, np.nan,
        safe_div(df["free_cash_flow_cr"], df["operating_profit"]) * 100
    )
    return df


def compute_per_share(df):
    """EPS, Book Value Per Share with defensive data casting."""
    df["earnings_per_share"] = df["eps"].fillna(np.nan)
    
    # Clean face_value safely up front to handle text artifacts or empty strings
    fv_numeric = pd.to_numeric(df["face_value"], errors="coerce")
    
    df["shares_outstanding"] = np.where(
        fv_numeric.fillna(0) == 0, np.nan,
        df["equity_capital"].fillna(0) / fv_numeric.fillna(1) * 1e7
    )
    
    df["book_value_per_share"] = np.where(
        df["shares_outstanding"].isna(), np.nan,
        safe_div(df["total_equity"] * 1e7, df["shares_outstanding"])
    )
    
    df["dividend_payout_ratio_pct"] = df["dividend_payout"].fillna(np.nan)
    df["total_debt_cr"] = df["borrowings"].fillna(0)
    
    return df


def run_ratio_engine():
    conn = sqlite3.connect(DB_PATH)
    pl, bs, cf, se = get_data(conn)

    # Merge all on company_id + year
    df = pl.merge(bs, on=["company_id","year"], suffixes=("","_bs"))
    df = df.merge(cf, on=["company_id","year"], suffixes=("","_cf"))
    df = df.merge(se, on="company_id", how="left")

    # Also bring face_value from companies
    co = pd.read_sql("SELECT id AS company_id, face_value FROM companies", conn)
    df = df.merge(co, on="company_id", how="left")

    financial_sectors = FINANCIAL_SECTORS

    df = compute_profitability(df)
    df = compute_leverage(df, financial_sectors)
    df = compute_efficiency(df)
    df = compute_cashflow_kpis(df)
    df = compute_per_share(df)

    # Select final columns for financial_ratios table
    RATIO_COLS = [
        "company_id","year",
        "net_profit_margin_pct","operating_profit_margin_pct",
        "return_on_equity_pct","return_on_capital_pct","return_on_assets_pct",
        "debt_to_equity","de_flag","interest_coverage","icr_display",
        "net_debt_cr","net_debt_to_ebitda",
        "asset_turnover","fixed_asset_turnover","working_capital_days",
        "free_cash_flow_cr","cash_from_operations_cr","capex_cr",
        "cfo_pat_ratio","capex_intensity_pct","fcf_conversion_pct",
        "earnings_per_share","book_value_per_share",
        "dividend_payout_ratio_pct","total_debt_cr",
        "ebit","ebit_margin_pct","total_equity","capital_employed",
    ]
    out = df[[c for c in RATIO_COLS if c in df.columns]].copy()

    cagr = pd.read_sql("SELECT company_id, revenue_cagr_5yr, pat_cagr_5yr, eps_cagr_5yr FROM cagr_metrics", conn)
    out = out.merge(cagr, on="company_id", how="left")

    out.to_sql("financial_ratios", conn, if_exists="replace", index=False)
    logger.info("financial_ratios: %d rows written", len(out))

    edge_cases = out[out[["return_on_equity_pct","return_on_capital_pct","debt_to_equity"]].isnull().any(axis=1)][["company_id","year"]].copy()
    edge_cases["note"] = "One or more KPIs null — negative equity or zero denominator"
    edge_cases.to_csv("data/ratio_edge_cases.csv", index=False)
    logger.info("ratio_edge_cases.csv: %d rows", len(edge_cases))

    out.to_csv("data/financial_ratios_computed.csv", index=False)
    conn.close()
    logger.info("Ratio engine complete.")


if __name__ == "__main__":
    run_ratio_engine()
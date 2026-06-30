import os, sqlite3, logging
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
logger = logging.getLogger(__name__)


def compute_cagr(start, end, n) -> tuple:
    """Returns (cagr_value, flag)."""
    if pd.isna(start) or pd.isna(end) or n < 1:
        return np.nan, "INSUFFICIENT"
    if start == 0:
        return np.nan, "ZERO_BASE"
    if start > 0 and end < 0:
        return np.nan, "DECLINE_TO_LOSS"
    if start < 0 and end > 0:
        return np.nan, "TURNAROUND"
    if start < 0 and end < 0:
        return np.nan, "BOTH_NEGATIVE"
    return round((pow(end / start, 1 / n) - 1) * 100, 4), "OK"


def cagr_series(group: pd.DataFrame, col: str, windows: list) -> dict:
    """Compute CAGR for multiple windows for one company."""
    group = group.sort_values("year")
    results = {}
    for n in windows:
        if len(group) < n + 1:
            results[f"{col}_cagr_{n}yr"] = np.nan
            results[f"{col}_cagr_{n}yr_flag"] = "INSUFFICIENT"
            continue
        latest = group.iloc[-1][col]
        base   = group.iloc[-1 - n][col]
        val, flag = compute_cagr(base, latest, n)
        results[f"{col}_cagr_{n}yr"]      = val
        results[f"{col}_cagr_{n}yr_flag"] = flag
    return results


def run_cagr_engine():
    conn = sqlite3.connect(DB_PATH)
    pl   = pd.read_sql("SELECT company_id, year, sales, net_profit, eps FROM profitandloss", conn)

    pl["year"] = pl["year"].astype(str)
    pl = pl.sort_values(["company_id","year"])

    WINDOWS = [3, 5, 10]
    METRICS = {"sales": "revenue", "net_profit": "pat", "eps": "eps"}

    records = []
    for cid, grp in pl.groupby("company_id"):
        row = {"company_id": cid, "latest_year": grp["year"].max()}
        for col, label in METRICS.items():
            grp_clean = grp.dropna(subset=[col])
            for n in WINDOWS:
                if len(grp_clean) < n + 1:
                    row[f"{label}_cagr_{n}yr"]      = np.nan
                    row[f"{label}_cagr_{n}yr_flag"] = "INSUFFICIENT"
                else:
                    latest = grp_clean.iloc[-1][col]
                    base   = grp_clean.iloc[-1 - n][col]
                    val, flag = compute_cagr(base, latest, n)
                    row[f"{label}_cagr_{n}yr"]      = val
                    row[f"{label}_cagr_{n}yr_flag"] = flag
        records.append(row)

    df = pd.DataFrame(records)
    df.to_sql("cagr_metrics", conn, if_exists="replace", index=False)
    df.to_csv("data/cagr_metrics.csv", index=False)

    conn.close()
    logger.info("CAGR engine: %d companies processed", len(df))
    print(f"Done — cagr_metrics table: {len(df)} rows")
    print(df[["company_id","revenue_cagr_5yr","revenue_cagr_5yr_flag",
              "pat_cagr_5yr","pat_cagr_5yr_flag"]].head(10).to_string())


if __name__ == "__main__":
    run_cagr_engine()
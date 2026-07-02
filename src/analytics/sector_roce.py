import os, sqlite3, logging
import pandas as pd
import numpy as np
from dotenv import load_dotenv


load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
logger = logging.getLogger(__name__)

FINANCIAL_SECTORS = {"Financials"}


def run_sector_roce():
    conn = sqlite3.connect(DB_PATH)

    ratios  = pd.read_sql("SELECT * FROM financial_ratios", conn)
    sectors = pd.read_sql("SELECT company_id, broad_sector, sub_sector FROM sectors", conn)
    co      = pd.read_sql("SELECT id AS company_id, roce_percentage FROM companies", conn)
    co["roce_percentage"] = pd.to_numeric(co["roce_percentage"], errors="coerce")

    df = ratios.merge(sectors, on="company_id", how="left")

    # Sector median for each KPI
    KPI_COLS = [
        "return_on_equity_pct","return_on_capital_pct","net_profit_margin_pct",
        "operating_profit_margin_pct","debt_to_equity","asset_turnover",
        "free_cash_flow_cr","revenue_cagr_5yr","pat_cagr_5yr"
    ]
    available = [c for c in KPI_COLS if c in df.columns]

    latest = df.sort_values("year").groupby("company_id").last().reset_index()
    latest = latest.merge(sectors, on="company_id", how="left", suffixes=("_drop", ""))
    latest = latest.drop(columns=[c for c in latest.columns if c.endswith("_drop")])

    sector_medians = latest.groupby("broad_sector")[available].median().round(2)
    sector_medians.to_sql("sector_benchmarks", conn, if_exists="replace")
    sector_medians.to_csv("data/sector_benchmarks.csv")
    print("\n===== SECTOR MEDIANS =====")
    print(sector_medians[["return_on_equity_pct","return_on_capital_pct",
                           "net_profit_margin_pct","debt_to_equity"]].to_string())

    # ROCE anomaly check vs companies.xlsx pre-computed
    latest_roce = latest[["company_id","return_on_capital_pct"]].copy()
    merged = latest_roce.merge(co, on="company_id", how="left")
    merged["diff"] = abs(merged["return_on_capital_pct"].fillna(0) -
                         merged["roce_percentage"].fillna(0))

    anomalies = merged[merged["diff"] > 10].copy()
    anomalies["note"] = "ROCE diff >10% — possible year mismatch or bank/NBFC"
    anomalies.to_csv("data/sector_roce_notes.csv", index=False)

    print(f"\n===== ROCE ANOMALIES: {len(anomalies)} =====")
    print(anomalies[["company_id","return_on_capital_pct",
                      "roce_percentage","diff"]].to_string())

    # Sector ranking by median ROE
    ranking = sector_medians["return_on_equity_pct"].sort_values(
        ascending=False).reset_index()
    ranking.columns = ["broad_sector","median_roe"]
    ranking["rank"] = range(1, len(ranking)+1)
    ranking.to_sql("sector_ranking", conn, if_exists="replace", index=False)
    ranking.to_csv("data/sector_ranking.csv", index=False)

    print("\n===== SECTOR RANKING (ROE) =====")
    print(ranking.to_string(index=False))

    conn.close()
    print("\nDone — sector_benchmarks, sector_ranking, sector_roce_notes saved.")


if __name__ == "__main__":
    run_sector_roce()
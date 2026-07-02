import os, sqlite3, logging
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
logger = logging.getLogger(__name__)

# 8 capital allocation patterns (CFO, CFI, CFF signs)
PATTERNS = {
    ("+","-","-"): "Reinvestor",
    ("+","-","+"): "Acquisitive Growth",
    ("+","+","-"): "Asset Seller",
    ("+","+","+"): "Aggressive Expansion",
    ("-","-","+"): "Distress",
    ("-","+","+"): "Turnaround Attempt",
    ("-","-","-"): "Declining",
    ("-","+","-"): "Asset Liquidator",
}

def sign(x):
    return "+" if x >= 0 else "-"

def classify_pattern(cfo, cfi, cff):
    return PATTERNS.get((sign(cfo), sign(cfi), sign(cff)), "Unknown")

def cfo_quality(cfo_pat_avg):
    if pd.isna(cfo_pat_avg): return "Insufficient Data"
    if cfo_pat_avg >= 1.0:   return "High Quality Earnings"
    if cfo_pat_avg >= 0.5:   return "Moderate Quality"
    return "Accrual Risk"

def capex_category(capex_pct):
    if pd.isna(capex_pct):  return "Unknown"
    if capex_pct < 3:       return "Asset Light"
    if capex_pct <= 8:      return "Moderate CapEx"
    return "Capital Intensive"

def run_cashflow_intelligence():
    conn = sqlite3.connect(DB_PATH)
    cf = pd.read_sql("SELECT * FROM cashflow", conn)
    pl = pd.read_sql("SELECT company_id, year, net_profit, sales, operating_profit FROM profitandloss", conn)

    df = cf.merge(pl, on=["company_id","year"], how="left")
    df = df.sort_values(["company_id","year"])

    # Per-row capital allocation pattern
    df["cfo_sign"] = df["operating_activity"].apply(sign)
    df["cfi_sign"] = df["investing_activity"].apply(sign)
    df["cff_sign"] = df["financing_activity"].apply(sign)
    df["pattern_label"] = df.apply(
        lambda r: classify_pattern(r["operating_activity"],
                                   r["investing_activity"],
                                   r["financing_activity"]), axis=1)

    # FCF
    df["free_cash_flow_cr"] = df["operating_activity"].fillna(0) + df["investing_activity"].fillna(0)
    df["capex_cr"]          = df["investing_activity"].fillna(0).abs()
    df["cfo_pat_ratio"]     = np.where(df["net_profit"]==0, np.nan,
                                        df["operating_activity"] / df["net_profit"])
    df["capex_intensity_pct"] = np.where(df["sales"]<=0, np.nan,
                                          df["capex_cr"] / df["sales"] * 100)
    df["fcf_conversion_pct"]  = np.where(df["operating_profit"]<=0, np.nan,
                                          df["free_cash_flow_cr"] / df["operating_profit"] * 100)

    # Save per-row capital allocation
    alloc_cols = ["company_id","year","cfo_sign","cfi_sign","cff_sign",
                  "pattern_label","free_cash_flow_cr","capex_cr",
                  "cfo_pat_ratio","capex_intensity_pct","fcf_conversion_pct"]
    alloc = df[alloc_cols].copy()
    alloc.to_sql("capital_allocation", conn, if_exists="replace", index=False)
    alloc.to_csv("data/capital_allocation.csv", index=False)

    # Company-level summary (5yr averages)
    records = []
    distress = []

    for cid, grp in df.groupby("company_id"):
        grp = grp.sort_values("year")
        last5 = grp.tail(5)

        avg_cfo_pat  = last5["cfo_pat_ratio"].mean()
        avg_capex    = last5["capex_intensity_pct"].mean()
        latest_pat   = grp.iloc[-1]["pattern_label"]
        fcf_positive = int((last5["free_cash_flow_cr"] > 0).sum())

        # FCF concern — negative 3yr consecutive
        fcf_vals = grp["free_cash_flow_cr"].tail(3).values
        fcf_concern = bool(all(v < 0 for v in fcf_vals))

        # Distress flag — CFO<0 and CFF>0
        latest = grp.iloc[-1]
        is_distress = (latest["operating_activity"] < 0 and
                       latest["financing_activity"] > 0)

        # Deleveraging flag
        if len(grp) >= 2:
            borr_col = "borrowings" if "borrowings" in grp.columns else None
        else:
            borr_col = None

        row = {
            "company_id":        cid,
            "latest_pattern":    latest_pat,
            "cfo_quality":       cfo_quality(avg_cfo_pat),
            "avg_cfo_pat_5yr":   round(avg_cfo_pat, 3) if not pd.isna(avg_cfo_pat) else None,
            "capex_category":    capex_category(avg_capex),
            "avg_capex_pct_5yr": round(avg_capex, 2) if not pd.isna(avg_capex) else None,
            "fcf_positive_yrs_of_5": fcf_positive,
            "fcf_concern_flag":  fcf_concern,
            "distress_flag":     is_distress,
        }
        records.append(row)
        if is_distress:
            distress.append({"company_id": cid, "pattern": latest_pat,
                             "cfo": latest["operating_activity"],
                             "cff": latest["financing_activity"]})

    summary = pd.DataFrame(records)
    summary.to_sql("cashflow_intelligence", conn, if_exists="replace", index=False)
    summary.to_excel("data/cashflow_intelligence.xlsx", index=False)

    pd.DataFrame(distress).to_csv("data/distress_alerts.csv", index=False)

    conn.close()
    print(f"capital_allocation: {len(alloc)} rows")
    print(f"cashflow_intelligence: {len(summary)} companies")
    print(f"distress_alerts: {len(distress)} flagged")
    print(summary[["company_id","latest_pattern","cfo_quality","capex_category"]].head(10).to_string())

if __name__ == "__main__":
    run_cashflow_intelligence()
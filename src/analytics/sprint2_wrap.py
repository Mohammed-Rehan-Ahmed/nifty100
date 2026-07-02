import sqlite3, os, pandas as pd
from dotenv import load_dotenv
load_dotenv()
DB_PATH = os.getenv("DB_PATH","data/nifty100.db")

def wrap():
    conn = sqlite3.connect(DB_PATH)
    failures = []

    print("\n===== SPRINT 2 EXIT CRITERIA =====")

    # 1. financial_ratios rows
    n = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    ok = n >= 1100
    print(f"  {'✓' if ok else '✗'} financial_ratios rows: {n} (need ≥1100)")
    if not ok: failures.append("Low ratio rows")

    # 2. KPI columns present
    cols = [r[1] for r in conn.execute("PRAGMA table_info(financial_ratios)")]
    needed = ["return_on_equity_pct","debt_to_equity","free_cash_flow_cr",
              "revenue_cagr_5yr","pat_cagr_5yr","interest_coverage",
              "asset_turnover","net_profit_margin_pct"]
    for c in needed:
        ok = c in cols
        print(f"  {'✓' if ok else '✗'} column: {c}")
        if not ok: failures.append(f"Missing col: {c}")

    # 3. CAGR table
    n = conn.execute("SELECT COUNT(*) FROM cagr_metrics").fetchone()[0]
    ok = n >= 90
    print(f"  {'✓' if ok else '✗'} cagr_metrics rows: {n} (need ≥90)")
    if not ok: failures.append("cagr_metrics low")

    # 4. Capital allocation table
    n = conn.execute("SELECT COUNT(*) FROM capital_allocation").fetchone()[0]
    ok = n >= 1000
    print(f"  {'✓' if ok else '✗'} capital_allocation rows: {n} (need ≥1000)")
    if not ok: failures.append("capital_allocation low")

    # 5. Edge cases log
    ok = os.path.exists("data/ratio_edge_cases.csv")
    print(f"  {'✓' if ok else '✗'} ratio_edge_cases.csv exists")
    if not ok: failures.append("ratio_edge_cases.csv missing")

    # 6. Distress alerts
    ok = os.path.exists("data/distress_alerts.csv")
    print(f"  {'✓' if ok else '✗'} distress_alerts.csv exists")
    if not ok: failures.append("distress_alerts.csv missing")

    conn.close()
    print("\n===== RESULT =====")
    if not failures:
        print("  ✅ Sprint 2 COMPLETE — ready for Sprint 3 (Screener & Peers)")
    else:
        print("  ❌ ISSUES:")
        for f in failures: print(f"     - {f}")

if __name__ == "__main__":
    wrap()
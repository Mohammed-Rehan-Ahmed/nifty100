import sqlite3, os, pandas as pd
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")

SAMPLE = ["TCS", "HDFCBANK", "RELIANCE", "INFY", "MARUTI"]

def review():
    conn = sqlite3.connect(DB_PATH)

    print("\n===== ROW COUNTS =====")
    for t in ["companies","profitandloss","balancesheet","cashflow",
              "financial_ratios","sectors","market_cap","stock_prices","peer_groups","documents"]:
        c = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:25s}: {c}")

    print("\n===== YEAR COVERAGE (sample 5) =====")
    for ticker in SAMPLE:
        row = conn.execute("""
            SELECT p.company_id,
                   COUNT(DISTINCT p.year) AS pl_yrs,
                   COUNT(DISTINCT b.year) AS bs_yrs,
                   COUNT(DISTINCT c.year) AS cf_yrs
            FROM profitandloss p
            LEFT JOIN balancesheet b USING(company_id, year)
            LEFT JOIN cashflow     c USING(company_id, year)
            WHERE p.company_id = ?
        """, (ticker,)).fetchone()
        print(f"  {ticker}: P&L={row[1]}yr  BS={row[2]}yr  CF={row[3]}yr")

    print("\n===== NULL CHECKS =====")
    checks = [
        ("profitandloss", "sales"),
        ("profitandloss", "net_profit"),
        ("balancesheet",  "total_assets"),
        ("cashflow",      "operating_activity"),
    ]
    for table, col in checks:
        n = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL").fetchone()[0]
        print(f"  {table}.{col} NULLs: {n}")

    print("\n===== BS BALANCE VIOLATIONS =====")
    df = pd.read_sql("""
        SELECT company_id, year,
               ROUND(ABS(total_assets - total_liabilities),2) AS diff
        FROM balancesheet
        WHERE ABS(total_assets - total_liabilities) / total_assets > 0.01
        LIMIT 10
    """, conn)
    print(df if len(df) else "  None found [OK]")

    print("\n===== FK ORPHANS =====")
    for t in ["profitandloss","balancesheet","cashflow","sectors"]:
        n = conn.execute(f"""
            SELECT COUNT(*) FROM {t}
            WHERE company_id NOT IN (SELECT id FROM companies)
        """).fetchone()[0]
        print(f"  {t} orphans: {n}")

    print("\n===== DUPLICATE (company_id, year) =====")
    for t in ["profitandloss","balancesheet","cashflow"]:
        n = conn.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT company_id, year, COUNT(*) c FROM {t}
                GROUP BY company_id, year HAVING c > 1)
        """).fetchone()[0]
        print(f"  {t} dupes: {n}")

    conn.close()
    print("\n===== DQ REVIEW COMPLETE =====")

if __name__ == "__main__":
    review()
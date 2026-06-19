import os, sqlite3, logging, time
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from normaliser import normalize_year, normalize_ticker
from validator import run_all_validations

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
RAW = Path("data/raw")
SUP = Path("data/supporting")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CORE = {
    "companies":     (RAW / "companies.xlsx",     1),
    "profitandloss": (RAW / "profitandloss.xlsx", 1),
    "balancesheet":  (RAW / "balancesheet.xlsx",  1),
    "cashflow":      (RAW / "cashflow.xlsx",      1),
    "analysis":      (RAW / "analysis.xlsx",      1),
    "documents":     (RAW / "documents.xlsx",     1),
    "prosandcons":   (RAW / "prosandcons.xlsx",   1),
}
SUPP = {
    "financial_ratios": (SUP / "financial_ratios.xlsx", 0),
    "market_cap":       (SUP / "market_cap.xlsx",       0),
    "peer_groups":      (SUP / "peer_groups.xlsx",      0),
    "sectors":          (SUP / "sectors.xlsx",          0),
    "stock_prices":     (SUP / "stock_prices.xlsx",     0),
}

TIME_SERIES = {"profitandloss","balancesheet","cashflow","financial_ratios","market_cap","stock_prices"}
HAS_TICKER  = {"profitandloss","balancesheet","cashflow","analysis","documents","prosandcons",
               "financial_ratios","market_cap","peer_groups","sectors","stock_prices"}
AUDIT, FAILURES = [], []


def load_file(table, path, header):
    t0 = time.time()
    df = pd.read_excel(path, header=header)
    rows_in = len(df)

    if table in HAS_TICKER:
        col = "id" if table == "companies" else "company_id"
        df[col] = df[col].apply(normalize_ticker)
        bad = df[col] == ""
        if bad.any():
            FAILURES.extend([{"rule_id":"DQ-08","table":table,"company_id":r[col],
                              "year":None,"field":col,"issue":"bad_ticker","severity":"CRITICAL"}
                             for _,r in df[bad].iterrows()])
        df = df[~bad]

    if table in TIME_SERIES and "year" in df.columns:
        df["year"] = df["year"].apply(normalize_year)
        bad = df["year"].isna()
        if bad.any():
            FAILURES.extend([{"rule_id":"DQ-07","table":table,"company_id":r.get("company_id"),
                              "year":r["year"],"field":"year","issue":"bad_year","severity":"CRITICAL"}
                             for _,r in df[bad].iterrows()])
        df = df[~bad]

    if table in TIME_SERIES:
        key = "id" if table == "companies" else "company_id"
        # Dynamic handling to fix the stock_prices 'date' vs 'year' crash
        subset_cols = [key]
        if "year" in df.columns:
            subset_cols.append("year")
        elif "date" in df.columns:
            subset_cols.append("date")
        df = df.drop_duplicates(subset=subset_cols, keep="last")

    rows_out = len(df)
    AUDIT.append({"table":table,"rows_in":rows_in,"rows_out":rows_out,
                  "rejected":rows_in-rows_out,"runtime_s":round(time.time()-t0,3)})
    logger.info("%s: %d → %d rows", table, rows_in, rows_out)
    return df


# CHANGE 1: New helper function added right above run_etl()
def write_db(table: str, df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    try:
        conn.execute(f"DELETE FROM {table}")
    except sqlite3.OperationalError:
        pass  # table doesn't exist yet — schema.sql not run; fall back
    df.to_sql(table, conn, if_exists="append", index=False)
    logger.info("Loaded table: %s (%d rows)", table, len(df))


def run_etl():
    os.makedirs("data", exist_ok=True)
    dfs = {}

    for table, (path, hdr) in {**CORE, **SUPP}.items():
        if not path.exists():
            logger.error("MISSING: %s", path)
            AUDIT.append({"table":table,"rows_in":0,"rows_out":0,"rejected":0,"runtime_s":0,"error":"FILE_NOT_FOUND"})
            continue
        try:
            dfs[table] = load_file(table, path, hdr)
        except Exception as e:
            logger.error("FAILED %s: %s", table, e)

    # Run all 16 DQ rules
    dq_failures = run_all_validations(dfs)
    FAILURES.extend(dq_failures)

    # CHANGE 2: Replaced the old SQLite writing block completely
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # Read and initialize schema.sql rules directly before pushing data
    with open("db/schema.sql") as f:
        conn.executescript(f.read())

    for table, df in dfs.items():
        write_db(table, df, conn)

    conn.commit()
    conn.close()

    pd.DataFrame(AUDIT).to_csv("data/load_audit.csv", index=False)
    pd.DataFrame(FAILURES).to_csv("data/validation_failures.csv", index=False)
    logger.info("Done. AUDIT → data/load_audit.csv | FAILURES → data/validation_failures.csv")


if __name__ == "__main__":
    run_etl()
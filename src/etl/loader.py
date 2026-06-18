import os
import sqlite3
import logging
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from normaliser import normalize_year, normalize_ticker

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
RAW_DIR = Path("data/raw")
SUP_DIR = Path("data/supporting")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── File manifest ──────────────────────────────────────────────────────────────
CORE_FILES = {
    "companies":      (RAW_DIR / "companies.xlsx",     1),
    "profitandloss":  (RAW_DIR / "profitandloss.xlsx", 1),
    "balancesheet":   (RAW_DIR / "balancesheet.xlsx",  1),
    "cashflow":       (RAW_DIR / "cashflow.xlsx",      1),
    "analysis":       (RAW_DIR / "analysis.xlsx",      1),
    "documents":      (RAW_DIR / "documents.xlsx",     1),
    "prosandcons":    (RAW_DIR / "prosandcons.xlsx",   1),
}

SUPP_FILES = {
    "financial_ratios": (SUP_DIR / "financial_ratios.xlsx", 0),
    "market_cap":       (SUP_DIR / "market_cap.xlsx",       0),
    "peer_groups":      (SUP_DIR / "peer_groups.xlsx",      0),
    "sectors":          (SUP_DIR / "sectors.xlsx",          0),
    "stock_prices":     (SUP_DIR / "stock_prices.xlsx",     0),
}

# Tables with (company_id, year) composite key
TIME_SERIES = {"profitandloss", "balancesheet", "cashflow", "financial_ratios",
               "market_cap", "stock_prices"}

# Tables with company_id FK
HAS_TICKER = {"profitandloss", "balancesheet", "cashflow", "analysis",
              "documents", "prosandcons", "financial_ratios", "market_cap",
              "peer_groups", "sectors", "stock_prices"}

AUDIT = []
FAILURES = []


def load_file(table: str, path: Path, header: int) -> pd.DataFrame:
    """Load one Excel file, normalise tickers + years, deduplicate."""
    logger.info("Loading %s from %s", table, path)
    t0 = time.time()

    df = pd.read_excel(path, header=header)
    rows_in = len(df)

    # Normalise ticker
    if table in HAS_TICKER:
        col = "id" if table == "companies" else "company_id"
        df[col] = df[col].apply(normalize_ticker)
        bad = df[col] == ""
        if bad.any():
            for _, row in df[bad].iterrows():
                FAILURES.append({"table": table, "issue": "bad_ticker",
                                 "severity": "CRITICAL", "row": str(row.to_dict())})
        df = df[~bad]

    # Normalise year
    if table in TIME_SERIES and "year" in df.columns:
        df["year"] = df["year"].apply(normalize_year)
        parse_err = df["year"] == "PARSE_ERROR"
        if parse_err.any():
            for _, row in df[parse_err].iterrows():
                FAILURES.append({"table": table, "issue": "bad_year",
                                 "severity": "CRITICAL", "row": str(row.to_dict())})
        df = df[~parse_err]

    # Deduplicate composite key
# Deduplicate composite key
    if table in TIME_SERIES:
        key_col = "id" if table == "companies" else "company_id"
        before = len(df)
        
        # Determine the correct timeline column dynamically
        subset_cols = [key_col]
        if "year" in df.columns:
            subset_cols.append("year")
        elif "date" in df.columns:
            subset_cols.append("date")
            
        df = df.drop_duplicates(subset=subset_cols, keep="last")
        dupes = before - len(df)
        if dupes:
            logger.warning("%s: dropped %d duplicate rows", table, dupes)

    rows_out = len(df)
    rejected = rows_in - rows_out
    runtime = round(time.time() - t0, 3)
    AUDIT.append({"table": table, "rows_in": rows_in, "rows_out": rows_out,
                  "rejected": rejected, "runtime_s": runtime})
    logger.info("%s: %d → %d rows (%ds)", table, rows_in, rows_out, runtime)
    return df

def write_db(table: str, df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """Write DataFrame to SQLite table (replace)."""
    df.to_sql(table, conn, if_exists="replace", index=False)
    logger.info("Wrote %d rows → table '%s'", len(df), table)


def save_audit() -> None:
    pd.DataFrame(AUDIT).to_csv("data/load_audit.csv", index=False)
    logger.info("Saved load_audit.csv")


def save_failures() -> None:
    pd.DataFrame(FAILURES).to_csv("data/validation_failures.csv", index=False)
    logger.info("Saved validation_failures.csv (%d issues)", len(FAILURES))


def run_etl() -> None:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    all_files = {**CORE_FILES, **SUPP_FILES}
    for table, (path, header) in all_files.items():
        if not path.exists():
            logger.error("File not found: %s", path)
            AUDIT.append({"table": table, "rows_in": 0, "rows_out": 0,
                          "rejected": 0, "runtime_s": 0, "error": "FILE_NOT_FOUND"})
            continue
        try:
            df = load_file(table, path, header)
            write_db(table, df, conn)
        except Exception as e:
            logger.error("Failed loading %s: %s", table, e)
            FAILURES.append({"table": table, "issue": str(e),
                             "severity": "CRITICAL", "row": ""})

    conn.commit()
    conn.close()
    save_audit()
    save_failures()
    logger.info("ETL complete. DB: %s", DB_PATH)


if __name__ == "__main__":
    run_etl()
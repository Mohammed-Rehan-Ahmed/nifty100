import re
import logging
import pandas as pd
from typing import Dict, List

logger = logging.getLogger(__name__)

TIME_SERIES_TABLES = (
    "profitandloss", "balancesheet", "cashflow",
    "financial_ratios", "market_cap"
)


def _flag(failures: List[dict], rule_id: str, table: str,
          company_id, year, field: str, issue: str, severity: str) -> None:
    failures.append({
        "rule_id":    rule_id,
        "table":      table,
        "company_id": str(company_id) if company_id is not None else None,
        "year":       str(year)       if year       is not None else None,
        "field":      field,
        "issue":      issue,
        "severity":   severity,
    })


# ── CRITICAL ──────────────────────────────────────────────────────────────────

def dq01_company_pk_unique(dfs: Dict[str, pd.DataFrame],
                           failures: List[dict]) -> None:
    """DQ-01: companies.id must be unique."""
    df = dfs.get("companies")
    if df is None: return
    dupes = df[df["id"].duplicated(keep=False)]
    for _, row in dupes.iterrows():
        _flag(failures, "DQ-01", "companies", row["id"], None,
              "id", f"Duplicate company PK: {row['id']}", "CRITICAL")


def dq02_pl_pk_unique(dfs: Dict[str, pd.DataFrame],
                      failures: List[dict]) -> None:
    """DQ-02: No duplicate (company_id, year) in profitandloss."""
    df = dfs.get("profitandloss")
    if df is None: return
    dupes = df[df.duplicated(subset=["company_id", "year"], keep=False)]
    for _, row in dupes.iterrows():
        _flag(failures, "DQ-02", "profitandloss",
              row["company_id"], row["year"],
              "company_id+year", "Duplicate PK", "CRITICAL")


def dq03_bs_pk_unique(dfs: Dict[str, pd.DataFrame],
                      failures: List[dict]) -> None:
    """DQ-03: No duplicate (company_id, year) in balancesheet."""
    df = dfs.get("balancesheet")
    if df is None: return
    dupes = df[df.duplicated(subset=["company_id", "year"], keep=False)]
    for _, row in dupes.iterrows():
        _flag(failures, "DQ-03", "balancesheet",
              row["company_id"], row["year"],
              "company_id+year", "Duplicate PK", "CRITICAL")


def dq04_cf_pk_unique(dfs: Dict[str, pd.DataFrame],
                      failures: List[dict]) -> None:
    """DQ-04: No duplicate (company_id, year) in cashflow."""
    df = dfs.get("cashflow")
    if df is None: return
    dupes = df[df.duplicated(subset=["company_id", "year"], keep=False)]
    for _, row in dupes.iterrows():
        _flag(failures, "DQ-04", "cashflow",
              row["company_id"], row["year"],
              "company_id+year", "Duplicate PK", "CRITICAL")


def dq05_fk_integrity(dfs: Dict[str, pd.DataFrame],
                      failures: List[dict]) -> None:
    """DQ-05: All company_id values must exist in companies.id."""
    companies = dfs.get("companies")
    if companies is None: return
    valid_ids = set(companies["id"].dropna().str.strip().str.upper())

    child_tables = [
        "profitandloss", "balancesheet", "cashflow", "analysis",
        "documents", "prosandcons", "financial_ratios",
        "market_cap", "peer_groups", "sectors", "stock_prices",
    ]
    for table in child_tables:
        df = dfs.get(table)
        if df is None or "company_id" not in df.columns: continue
        orphans = df[~df["company_id"].isin(valid_ids)]
        for _, row in orphans.iterrows():
            _flag(failures, "DQ-05", table,
                  row["company_id"], row.get("year"),
                  "company_id",
                  f"Orphan FK '{row['company_id']}' not in companies.id",
                  "CRITICAL")


def dq06_stock_price_date_format(dfs: Dict[str, pd.DataFrame],
                                  failures: List[dict]) -> None:
    """DQ-06: stock_prices.date must match ISO YYYY-MM-DD (optional timestamp)."""
    df = dfs.get("stock_prices")
    if df is None or "date" not in df.columns: return
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?$")
    bad = df[~df["date"].astype(str).str.strip().str.match(pattern)]
    for _, row in bad.iterrows():
        _flag(failures, "DQ-06", "stock_prices",
              row.get("company_id"), None,
              "date",
              f"Invalid date format: '{row['date']}'",
              "CRITICAL")


def dq07_year_format(dfs: Dict[str, pd.DataFrame],
                     failures: List[dict]) -> None:
    """DQ-07: All year values must match YYYY-MM after normalisation.
    TTM and blank strings are safely skipped.
    """
    pattern = re.compile(r"^\d{4}-\d{2}$")
    SILENT_SKIP = {"ttm", "none", "nan", "", "parse_error"}

    for table in TIME_SERIES_TABLES:
        df = dfs.get(table)
        if df is None or "year" not in df.columns: continue
        
        year_strs = df["year"].astype(str).str.strip()
        skip_mask = year_strs.str.lower().isin(SILENT_SKIP) | df["year"].isna()
        
        # Catch anything that isn't valid standard format AND isn't in the skip set
        bad = df[~skip_mask & ~year_strs.str.match(pattern)]
        for _, row in bad.iterrows():
            _flag(failures, "DQ-07", table,
                  row.get("company_id"), row["year"],
                  "year",
                  "bad_year",
                  "CRITICAL")


def dq08_ticker_format(dfs: Dict[str, pd.DataFrame],
                       failures: List[dict]) -> None:
    """DQ-08: Ticker must be 2-12 uppercase alphanumeric chars."""
    pattern = re.compile(r"^[A-Z0-9&\-]{2,12}$")
    checks = [("companies", "id")] + [
        (t, "company_id") for t in (
            "profitandloss", "balancesheet", "cashflow",
            "sectors", "peer_groups", "documents", "prosandcons"
        )
    ]
    for table, col in checks:
        df = dfs.get(table)
        if df is None or col not in df.columns: continue
        bad = df[~df[col].astype(str).str.match(pattern)]
        for _, row in bad.iterrows():
            _flag(failures, "DQ-08", table,
                  row[col], None, col,
                  f"Invalid ticker format: '{row[col]}'",
                  "CRITICAL")


# ── WARNING ───────────────────────────────────────────────────────────────────

def dq09_opm_crosscheck(dfs: Dict[str, pd.DataFrame],
                        failures: List[dict]) -> None:
    """DQ-09: (sales - expenses) should equal operating_profit within 1%."""
    df = dfs.get("profitandloss")
    if df is None: return
    df = df.copy()
    df["_computed_op"] = df["sales"].fillna(0) - df["expenses"].fillna(0)
    df["_diff"] = (df["_computed_op"] - df["operating_profit"].fillna(0)).abs()
    threshold = (df["sales"].fillna(0).abs() * 0.01).clip(lower=1)
    for _, row in df[df["_diff"] > threshold].iterrows():
        _flag(failures, "DQ-09", "profitandloss",
              row["company_id"], row["year"],
              "operating_profit",
              f"sales-expenses={round(row['_computed_op'],2)} "
              f"!= operating_profit={round(row['operating_profit'],2)} "
              f"(diff={round(row['_diff'],2)})",
              "WARNING")


def dq10_opm_pct_crosscheck(dfs: Dict[str, pd.DataFrame],
                             failures: List[dict]) -> None:
    """DQ-10: opm_percentage should match computed OPM within 1 point."""
    df = dfs.get("profitandloss")
    if df is None: return
    df = df.copy()
    mask = df["sales"].fillna(0) > 0
    df.loc[mask, "_computed_opm"] = (
        df.loc[mask, "operating_profit"] / df.loc[mask, "sales"] * 100
    )
    df["_pct_diff"] = (
        df["opm_percentage"].fillna(0) - df["_computed_opm"].fillna(0)
    ).abs()
    for _, row in df[mask & (df["_pct_diff"] > 1.0)].iterrows():
        _flag(failures, "DQ-10", "profitandloss",
              row["company_id"], row["year"],
              "opm_percentage",
              f"Stored OPM={row['opm_percentage']} vs "
              f"computed={round(row.get('_computed_opm', 0), 2)} "
              f"(diff={round(row['_pct_diff'], 2)}pp)",
              "WARNING")


def dq11_bs_balance(dfs: Dict[str, pd.DataFrame],
                    failures: List[dict]) -> None:
    """DQ-11: total_assets must equal total_liabilities within 1%."""
    df = dfs.get("balancesheet")
    if df is None: return
    df = df.copy()
    mask = df["total_assets"].fillna(0) > 0
    df.loc[mask, "_diff_pct"] = (
        (df.loc[mask, "total_assets"] - df.loc[mask, "total_liabilities"]).abs()
        / df.loc[mask, "total_assets"] * 100
    )
    for _, row in df[mask & (df["_diff_pct"] > 1.0)].iterrows():
        _flag(failures, "DQ-11", "balancesheet",
              row["company_id"], row["year"],
              "total_assets",
              f"Assets={row['total_assets']} != "
              f"Liabilities={row['total_liabilities']} "
              f"(diff={round(row.get('_diff_pct', 0), 2)}%)",
              "WARNING")


def dq12_positive_sales(dfs: Dict[str, pd.DataFrame],
                        failures: List[dict]) -> None:
    """DQ-12: sales must be > 0."""
    df = dfs.get("profitandloss")
    if df is None: return
    for _, row in df[df["sales"].fillna(0) <= 0].iterrows():
        _flag(failures, "DQ-12", "profitandloss",
              row["company_id"], row["year"],
              "sales",
              f"sales={row['sales']} is zero or negative",
              "WARNING")


def dq13_analysis_text_quality(dfs: Dict[str, pd.DataFrame],
                                failures: List[dict]) -> None:
    """DQ-13: analysis text fields must be regex-parseable."""
    df = dfs.get("analysis")
    if df is None: return
    pattern = re.compile(r"\d+\s*Years?:?\s*[\d.]+\s*%", re.IGNORECASE)
    text_cols = ["compounded_sales_growth", "compounded_profit_growth",
                 "stock_price_cagr", "roe"]
    for col in text_cols:
        if col not in df.columns: continue
        for _, row in df.iterrows():
            val = str(row[col]).strip() if pd.notna(row[col]) else ""
            if not val or val.lower() in ("nan", "none", "-"): continue
            if not pattern.search(val):
                _flag(failures, "DQ-13", "analysis",
                      row["company_id"], None, col,
                      f"Unparseable text: '{val}'",
                      "WARNING")


def dq14_eps_sign(dfs: Dict[str, pd.DataFrame],
                  failures: List[dict]) -> None:
    """DQ-14: eps must be > 0 when net_profit > 0."""
    df = dfs.get("profitandloss")
    if df is None: return
    flagged = df[(df["net_profit"].fillna(0) > 0) &
                 (df["eps"].fillna(0) <= 0)]
    for _, row in flagged.iterrows():
        _flag(failures, "DQ-14", "profitandloss",
              row["company_id"], row["year"],
              "eps",
              f"net_profit={row['net_profit']} > 0 but eps={row['eps']}",
              "WARNING")


def dq15_dividend_payout_cap(dfs: Dict[str, pd.DataFrame],
                              failures: List[dict]) -> None:
    """DQ-15: dividend_payout > 200% is likely a data error."""
    df = dfs.get("profitandloss")
    if df is None: return
    for _, row in df[df["dividend_payout"].fillna(0) > 200].iterrows():
        _flag(failures, "DQ-15", "profitandloss",
              row["company_id"], row["year"],
              "dividend_payout",
              f"Payout={row['dividend_payout']}% exceeds 200% cap",
              "WARNING")


def dq16_coverage_check(dfs: Dict[str, pd.DataFrame],
                        failures: List[dict]) -> None:
    """DQ-16: Each company needs >= 5 years of data in all time-series tables."""
    companies = dfs.get("companies")
    if companies is None: return
    all_ids = set(companies["id"].dropna())

    for table in TIME_SERIES_TABLES:
        df = dfs.get(table)
        if df is None or "year" not in df.columns: continue
        counts = df.groupby("company_id")["year"].nunique()
        for cid in all_ids:
            yr_count = int(counts.get(cid, 0))
            if yr_count < 5:
                _flag(failures, "DQ-16", table,
                      cid, None, "year",
                      f"Only {yr_count} years of data (minimum 5 required)",
                      "WARNING")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all_validations(dfs: Dict[str, pd.DataFrame]) -> List[dict]:
    """Execute all 16 DQ rules. Returns list of failure dicts."""
    failures: List[dict] = []

    dq01_company_pk_unique(dfs, failures)
    dq02_pl_pk_unique(dfs, failures)
    dq03_bs_pk_unique(dfs, failures)
    dq04_cf_pk_unique(dfs, failures)
    dq05_fk_integrity(dfs, failures)
    dq06_stock_price_date_format(dfs, failures)
    dq07_year_format(dfs, failures)
    dq08_ticker_format(dfs, failures)
    dq09_opm_crosscheck(dfs, failures)
    dq10_opm_pct_crosscheck(dfs, failures)
    dq11_bs_balance(dfs, failures)
    dq12_positive_sales(dfs, failures)
    dq13_analysis_text_quality(dfs, failures)
    dq14_eps_sign(dfs, failures)
    dq15_dividend_payout_cap(dfs, failures)
    dq16_coverage_check(dfs, failures)

    critical = sum(1 for f in failures if f["severity"] == "CRITICAL")
    warning  = sum(1 for f in failures if f["severity"] == "WARNING")
    logger.info("DQ complete — CRITICAL: %d | WARNING: %d | TOTAL: %d",
                critical, warning, len(failures))
    return failures
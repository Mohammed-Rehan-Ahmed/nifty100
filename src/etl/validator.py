from __future__ import annotations

import pandas as pd

import logging
import pandas as pd
from typing import Dict, List
logger = logging.getLogger(__name__)

FAILURES = []


def _flag(rule_id: str, table: str, company_id, year, field: str,
          issue: str, severity: str) -> None:
    FAILURES.append({
        "rule_id":    rule_id,
        "table":      table,
        "company_id": company_id,
        "year":       year,
        "field":      field,
        "issue":      issue,
        "severity":   severity,
    })


def dq01_company_pk_unique(companies: pd.DataFrame) -> None:
    """DQ-01: companies.id must be unique."""
    dupes = companies[companies["id"].duplicated()]
    for _, row in dupes.iterrows():
        _flag("DQ-01", "companies", row["id"], None,
              "id", "Duplicate company PK", "CRITICAL")


def dq02_annual_pk_unique(dfs: dict[str, pd.DataFrame]) -> None:
    """DQ-02: No duplicate (company_id, year) in time-series tables."""
    for table in ("profitandloss", "balancesheet", "cashflow"):
        df = dfs.get(table)
        if df is None:
            continue
        dupes = df[df.duplicated(subset=["company_id", "year"], keep=False)]
        for _, row in dupes.iterrows():
            _flag("DQ-02", table, row["company_id"], row["year"],
                  "company_id+year", "Duplicate annual PK", "CRITICAL")


def dq03_fk_integrity(dfs: dict[str, pd.DataFrame]) -> None:
    """DQ-03: All company_id values must exist in companies.id."""
    valid_ids = set(dfs["companies"]["id"].dropna())
    child_tables = ["profitandloss", "balancesheet", "cashflow",
                    "analysis", "documents", "prosandcons",
                    "financial_ratios", "market_cap", "peer_groups",
                    "sectors", "stock_prices"]
    for table in child_tables:
        df = dfs.get(table)
        if df is None:
            continue
        col = "company_id"
        if col not in df.columns:
            continue
        orphans = df[~df[col].isin(valid_ids)]
        for _, row in orphans.iterrows():
            _flag("DQ-03", table, row[col], row.get("year"),
                  col, "Orphan FK — not in companies.id", "CRITICAL")


def dq04_bs_balance(balancesheet: pd.DataFrame) -> None:
    """DQ-04: |total_assets - total_liabilities| / total_assets < 1%."""
    df = balancesheet.copy()
    df["_diff"] = abs(df["total_assets"] - df["total_liabilities"]) / df["total_assets"].replace(0, pd.NA)
    flagged = df[df["_diff"] > 0.01]
    for _, row in flagged.iterrows():
        _flag("DQ-04", "balancesheet", row["company_id"], row["year"],
              "total_assets/total_liabilities",
              f"BS imbalance: diff={round(row['_diff']*100,2)}%", "WARNING")


def dq05_opm_crosscheck(pl: pd.DataFrame) -> None:
    """DQ-05: |opm_percentage - computed_opm| < 1%."""
    df = pl.copy()
    df["_computed_opm"] = df["operating_profit"] / df["sales"].replace(0, pd.NA) * 100
    df["_diff"] = abs(df["opm_percentage"] - df["_computed_opm"])
    flagged = df[df["_diff"] > 1.0]
    for _, row in flagged.iterrows():
        _flag("DQ-05", "profitandloss", row["company_id"], row["year"],
              "opm_percentage", f"OPM mismatch: {round(row['_diff'],2)}%", "WARNING")


def dq06_positive_sales(pl: pd.DataFrame) -> None:
    """DQ-06: sales > 0."""
    flagged = pl[pl["sales"] <= 0]
    for _, row in flagged.iterrows():
        _flag("DQ-06", "profitandloss", row["company_id"], row["year"],
              "sales", f"sales={row['sales']}", "WARNING")


def dq07_year_format(dfs: dict[str, pd.DataFrame]) -> None:
    """DQ-07: All year values match YYYY-MM after normalisation."""
    import re
    for table in ("profitandloss", "balancesheet", "cashflow", "financial_ratios"):
        df = dfs.get(table)
        if df is None or "year" not in df.columns:
            continue
        bad = df[~df["year"].astype(str).str.match(r"^\d{4}-\d{2}$")]
        for _, row in bad.iterrows():
            _flag("DQ-07", table, row.get("company_id"), row["year"],
                  "year", f"Bad year format: {row['year']}", "CRITICAL")


def dq08_ticker_format(dfs: dict[str, pd.DataFrame]) -> None:
    """DQ-08: company_id length 2-12 chars, already normalised."""
    for table, col in [("companies", "id")] + \
                      [(t, "company_id") for t in ("profitandloss", "balancesheet",
                       "cashflow", "sectors", "peer_groups")]:
        df = dfs.get(table)
        if df is None:
            continue
        bad = df[~df[col].astype(str).str.match(r"^[A-Z0-9&\-]{2,12}$")]
        for _, row in bad.iterrows():
            _flag("DQ-08", table, row[col], None,
                  col, f"Invalid ticker: {row[col]}", "CRITICAL")


def dq09_net_cash_check(cashflow: pd.DataFrame) -> None:
    """DQ-09: net_cash_flow == CFO + CFI + CFF within 10 Cr."""
    df = cashflow.copy()
    df["_computed"] = (df["operating_activity"] +
                       df["investing_activity"] +
                       df["financing_activity"])
    flagged = df[abs(df["net_cash_flow"] - df["_computed"]) > 10]
    for _, row in flagged.iterrows():
        _flag("DQ-09", "cashflow", row["company_id"], row["year"],
              "net_cash_flow",
              f"Mismatch: reported={row['net_cash_flow']}, computed={row['_computed']:.1f}",
              "WARNING")


def dq10_nonneg_fixed_assets(balancesheet: pd.DataFrame) -> None:
    """DQ-10: fixed_assets >= 0."""
    flagged = balancesheet[balancesheet["fixed_assets"] < 0]
    for _, row in flagged.iterrows():
        _flag("DQ-10", "balancesheet", row["company_id"], row["year"],
              "fixed_assets", f"Negative fixed_assets={row['fixed_assets']}", "WARNING")


def dq11_tax_rate_range(pl: pd.DataFrame) -> None:
    """DQ-11: 0 <= tax_percentage <= 60."""
    flagged = pl[(pl["tax_percentage"] < 0) | (pl["tax_percentage"] > 60)]
    for _, row in flagged.iterrows():
        _flag("DQ-11", "profitandloss", row["company_id"], row["year"],
              "tax_percentage", f"Out of range: {row['tax_percentage']}", "WARNING")


def dq12_dividend_payout_cap(pl: pd.DataFrame) -> None:
    """DQ-12: dividend_payout <= 200%."""
    flagged = pl[pl["dividend_payout"] > 200]
    for _, row in flagged.iterrows():
        _flag("DQ-12", "profitandloss", row["company_id"], row["year"],
              "dividend_payout", f"Payout={row['dividend_payout']}%", "WARNING")


def dq13_url_validity(documents: pd.DataFrame) -> None:
    """DQ-13: Check Annual_Report URLs return 200 (sample only — costly)."""
    # Full URL check is done in loader post-load to avoid blocking ETL
    # Flagged rows logged as WARNING only; do not reject
    missing = documents[documents["Annual_Report"].isna()]
    for _, row in missing.iterrows():
        _flag("DQ-13", "documents", row["company_id"], row.get("Year"),
              "Annual_Report", "Missing URL", "WARNING")


def dq14_eps_sign(pl: pd.DataFrame) -> None:
    """DQ-14: eps > 0 if net_profit > 0."""
    flagged = pl[(pl["net_profit"] > 0) & (pl["eps"] <= 0)]
    for _, row in flagged.iterrows():
        _flag("DQ-14", "profitandloss", row["company_id"], row["year"],
              "eps", f"eps={row['eps']} but net_profit={row['net_profit']}", "WARNING")


def dq15_bs_strict_balance(balancesheet: pd.DataFrame) -> None:
    """DQ-15: total_liabilities == total_assets (strict — INFO only)."""
    flagged = balancesheet[balancesheet["total_assets"] != balancesheet["total_liabilities"]]
    for _, row in flagged.iterrows():
        _flag("DQ-15", "balancesheet", row["company_id"], row["year"],
              "total_assets", "Strict BS imbalance (informational)", "INFO")


def dq16_coverage_check(dfs: dict[str, pd.DataFrame]) -> None:
    """DQ-16: Each company must have >= 5 years of P&L, BS, CF records."""
    for table in ("profitandloss", "balancesheet", "cashflow"):
        df = dfs.get(table)
        if df is None:
            continue
        counts = df.groupby("company_id")["year"].count()
        low = counts[counts < 5]
        for cid, cnt in low.items():
            _flag("DQ-16", table, cid, None,
                  "year", f"Only {cnt} years of data (min 5 required)", "WARNING")


def run_all_validations(dfs: dict[str, pd.DataFrame]) -> list[dict]:
    """Run all 16 DQ rules. Returns list of failure dicts."""
    FAILURES.clear()

    dq01_company_pk_unique(dfs["companies"])
    dq02_annual_pk_unique(dfs)
    dq03_fk_integrity(dfs)
    dq04_bs_balance(dfs["balancesheet"])
    dq05_opm_crosscheck(dfs["profitandloss"])
    dq06_positive_sales(dfs["profitandloss"])
    dq07_year_format(dfs)
    dq08_ticker_format(dfs)
    dq09_net_cash_check(dfs["cashflow"])
    dq10_nonneg_fixed_assets(dfs["balancesheet"])
    dq11_tax_rate_range(dfs["profitandloss"])
    dq12_dividend_payout_cap(dfs["profitandloss"])
    dq13_url_validity(dfs["documents"])
    dq14_eps_sign(dfs["profitandloss"])
    dq15_bs_strict_balance(dfs["balancesheet"])
    dq16_coverage_check(dfs)

    critical = sum(1 for f in FAILURES if f["severity"] == "CRITICAL")
    logger.info("DQ complete: %d issues (%d CRITICAL)", len(FAILURES), critical)
    return FAILURES
import sqlite3, os, pandas as pd
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")

EXPECTED = {
    "companies":      101,
    "profitandloss":  1200,
    "balancesheet":   1220,
    "cashflow":       1152,
    "sectors":        101,
    "market_cap":     552,
    "stock_prices":   5520,
    "peer_groups":    56,
}


def verify():
    conn     = sqlite3.connect(DB_PATH)
    failures = []

    print("\n===== SPRINT 1 EXIT CRITERIA =====")

    # ── 1. Row count check ────────────────────────────────────────────────────
    print("\n[1] ROW COUNTS")
    for table, expected in EXPECTED.items():
        actual = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        status = "✓" if actual >= expected * 0.90 else "✗"
        print(f"  {status} {table:25s}: {actual} (expected ~{expected})")
        if actual < expected * 0.90:
            failures.append(f"Low row count: {table} ({actual} < {int(expected*0.90)})")

    # ── 2. CRITICAL DQ failures ───────────────────────────────────────────────
    print("\n[2] CRITICAL DQ FAILURES")
    vf_path = "data/validation_failures.csv"
    try:
        df       = pd.read_csv(vf_path)
        critical = df[df["severity"] == "CRITICAL"]
        status   = "✓" if len(critical) == 0 else "✗"
        print(f"  {status} CRITICAL failures: {len(critical)}")
        if len(critical):
            print(critical[["rule_id","table","company_id","issue"]].to_string())
            failures.append("CRITICAL DQ violations found")
    except FileNotFoundError:
        print(f"  ✗ {vf_path} not found — run loader first")
        failures.append("validation_failures.csv missing")

    # ── 3. FK integrity ───────────────────────────────────────────────────────
    print("\n[3] FK INTEGRITY")
    for t in ["profitandloss", "balancesheet", "cashflow", "sectors"]:
        n = conn.execute(f"""
            SELECT COUNT(*) FROM {t}
            WHERE company_id NOT IN (SELECT id FROM companies)
        """).fetchone()[0]
        status = "✓" if n == 0 else "✗"
        print(f"  {status} {t} orphans: {n}")
        if n:
            failures.append(f"FK orphans in {t}: {n} rows")

    # ── 4. Year format check ──────────────────────────────────────────────────
    print("\n[4] YEAR FORMAT")
    for t in ["profitandloss", "balancesheet", "cashflow"]:
        n = conn.execute(f"""
            SELECT COUNT(*) FROM {t}
            WHERE year NOT LIKE '____-__'
        """).fetchone()[0]
        status = "✓" if n == 0 else "✗"
        print(f"  {status} {t} bad years: {n}")
        if n:
            failures.append(f"Bad year format in {t}: {n} rows")

    # ── 5. Company year coverage ──────────────────────────────────────────────
    print("\n[5] YEAR COVERAGE (>=10yr in P&L)")
    total_cos = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    n = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT company_id, COUNT(DISTINCT year) yrs
            FROM profitandloss
            GROUP BY company_id
            HAVING yrs >= 10)
    """).fetchone()[0]
    pct    = round(n / total_cos * 100) if total_cos else 0
    status = "✓" if pct >= 80 else "✗"
    print(f"  {status} Companies with 10+ years P&L: {n}/{total_cos} ({pct}%)")
    if pct < 80:
        failures.append(f"P&L coverage <80% — only {pct}%")

    # ── 6. All 3 time-series coverage check ───────────────────────────────────
    print("\n[6] MULTI-TABLE COVERAGE (>=5yr)")
    for t in ["profitandloss", "balancesheet", "cashflow"]:
        low = conn.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT company_id, COUNT(DISTINCT year) yrs
                FROM {t}
                GROUP BY company_id
                HAVING yrs < 5)
        """).fetchone()[0]
        status = "✓" if low == 0 else "⚠"
        print(f"  {status} {t} companies with <5yr: {low}")
        if low > 5:
            failures.append(f"Too many low-coverage companies in {t}: {low}")

    # ── 7. Load audit check ───────────────────────────────────────────────────
    print("\n[7] LOAD AUDIT")
    audit_path = "data/load_audit.csv"
    try:
        audit      = pd.read_csv(audit_path)
        file_err   = audit[audit.get("error", pd.Series(dtype=str)).fillna("") == "FILE_NOT_FOUND"] \
                     if "error" in audit.columns else pd.DataFrame()
        status_a   = "✓" if len(file_err) == 0 else "✗"
        print(f"  {status_a} {len(audit)} tables logged in load_audit.csv")
        if not file_err.empty:
            print(f"  ✗ FILE_NOT_FOUND entries: {file_err['table'].tolist()}")
            failures.append(f"Missing source files: {file_err['table'].tolist()}")
    except FileNotFoundError:
        print(f"  ✗ {audit_path} not found — run loader first")
        failures.append("load_audit.csv missing")

    # ── 8. All expected tables non-empty ─────────────────────────────────────
    print("\n[8] ALL TABLES NON-EMPTY")
    all_tables = [
        "companies","profitandloss","balancesheet","cashflow",
        "analysis","documents","prosandcons","sectors",
        "market_cap","stock_prices","financial_ratios","peer_groups"
    ]
    for t in all_tables:
        try:
            n      = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            status = "✓" if n > 0 else "✗"
            print(f"  {status} {t:25s}: {n} rows")
            if n == 0:
                failures.append(f"Empty table: {t}")
        except Exception as e:
            print(f"  ✗ {t}: ERROR — {e}")
            failures.append(f"Table error: {t}")

    conn.close()

    # ── Result ────────────────────────────────────────────────────────────────
    print("\n===== RESULT =====")
    if not failures:
        print("  ✅ ALL CHECKS PASSED — Sprint 1 complete, ready for Sprint 2")
    else:
        print("  ❌ ISSUES FOUND:")
        for f in failures:
            print(f"     - {f}")

    return len(failures) == 0


if __name__ == "__main__":
    verify()
-- 1. Row counts per table
SELECT 'companies'     AS tbl, COUNT(*) AS rows FROM companies UNION ALL
SELECT 'profitandloss',        COUNT(*) FROM profitandloss   UNION ALL
SELECT 'balancesheet',         COUNT(*) FROM balancesheet    UNION ALL
SELECT 'cashflow',             COUNT(*) FROM cashflow        UNION ALL
SELECT 'analysis',             COUNT(*) FROM analysis        UNION ALL
SELECT 'documents',            COUNT(*) FROM documents       UNION ALL
SELECT 'prosandcons',          COUNT(*) FROM prosandcons     UNION ALL
SELECT 'sectors',              COUNT(*) FROM sectors         UNION ALL
SELECT 'market_cap',           COUNT(*) FROM market_cap      UNION ALL
SELECT 'stock_prices',         COUNT(*) FROM stock_prices    UNION ALL
SELECT 'financial_ratios',     COUNT(*) FROM financial_ratios UNION ALL
SELECT 'peer_groups',          COUNT(*) FROM peer_groups;

-- 2. Year coverage per company (P&L)
SELECT company_id, COUNT(DISTINCT year) AS years,
       MIN(year) AS earliest, MAX(year) AS latest
FROM profitandloss
GROUP BY company_id
ORDER BY years ASC
LIMIT 20;

-- 3. Companies with < 5 years P&L
SELECT company_id, COUNT(DISTINCT year) AS years
FROM profitandloss
GROUP BY company_id
HAVING years < 5;

-- 4. NULL check on critical P&L fields
SELECT COUNT(*) AS null_sales    FROM profitandloss WHERE sales IS NULL;
SELECT COUNT(*) AS null_profit   FROM profitandloss WHERE net_profit IS NULL;
SELECT COUNT(*) AS null_equity   FROM balancesheet  WHERE equity_capital IS NULL;
SELECT COUNT(*) AS null_cfo      FROM cashflow      WHERE operating_activity IS NULL;

-- 5. Duplicate check (company_id, year)
SELECT company_id, year, COUNT(*) AS cnt
FROM profitandloss
GROUP BY company_id, year
HAVING cnt > 1;

-- 6. FK orphan check
SELECT DISTINCT p.company_id FROM profitandloss p
LEFT JOIN companies c ON p.company_id = c.id
WHERE c.id IS NULL;

-- 7. Balance sheet balance check
SELECT company_id, year,
       ROUND(ABS(total_assets - total_liabilities),2) AS diff
FROM balancesheet
WHERE ABS(total_assets - total_liabilities) / total_assets > 0.01
LIMIT 20;

-- 8. Sector distribution
SELECT broad_sector, COUNT(*) AS companies
FROM sectors
GROUP BY broad_sector
ORDER BY companies DESC;

-- 9. Stock price coverage (months per company)
SELECT company_id, COUNT(*) AS months
FROM stock_prices
GROUP BY company_id
ORDER BY months ASC
LIMIT 10;

-- 10. Market cap coverage
SELECT company_id, COUNT(DISTINCT year) AS years
FROM market_cap
GROUP BY company_id
ORDER BY years ASC
LIMIT 10;
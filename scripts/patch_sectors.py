import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Fallback to the default path if DB_PATH environment variable isn't set
DB = os.getenv("DB_PATH", "data/nifty100.db")
print(f"Connecting to database at: {DB}")

conn = sqlite3.connect(DB)

# Identify companies that exist in 'companies' but lack a record in 'sectors'
missing = pd.read_sql("""
    SELECT c.id FROM companies c
    LEFT JOIN sectors s ON c.id = s.company_id
    WHERE s.company_id IS NULL
""", conn)

missing_list = missing["id"].tolist()
print("Missing from sectors:", missing_list)

if missing_list:
    # Build default rows for the missing companies
    rows = [{
        "company_id": cid, 
        "broad_sector": "Unknown",
        "sub_sector": "Unknown", 
        "index_weight_pct": 0.0,
        "market_cap_category": "Large Cap"
    } for cid in missing_list]

    # Enable foreign keys and append rows to the sectors table
    conn.execute("PRAGMA foreign_keys = ON")
    pd.DataFrame(rows).to_sql("sectors", conn, if_exists="append", index=False)
    conn.commit()
    print(f"Successfully inserted {len(rows)} missing sector rows.")
else:
    print("No missing sector rows found.")

conn.close()
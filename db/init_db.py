import sqlite3, os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")

def init_schema():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with open("db/schema.sql", "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Schema created: {DB_PATH}")

if __name__ == "__main__":
    init_schema()
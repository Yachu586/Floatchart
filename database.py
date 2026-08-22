import sqlite3
import re
import os
from typing import Dict, Any, List, Tuple

DB_PATH = "argo_data.db"

ALLOWED_TABLES = {"floats", "profiles", "measurements", "argo_data_view"}
ALLOWED_COLUMNS = {
    "wmo_id", "region", "deployment_date", "is_bgc",
    "profile_id", "cycle_number", "profile_date", "latitude", "longitude",
    "measurement_id", "depth_m", "temperature", "salinity", "qc_flag", "chlorophyll"
}

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", 
    "EXEC", "EXECUTE", "REPLACE", "PRAGMA", "ATTACH", "DETACH"
]

def ensure_database_exists():
    """Check if database exists and has data; if not, trigger seed generator."""
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        print("[Database] argo_data.db missing or empty. Seeding database...")
        from seed_db import seed_database
        seed_database()

def is_safe_sql(sql: str) -> Tuple[bool, str]:
    """Validate that the query is a safe, read-only SELECT query."""
    clean_sql = sql.strip().strip(";").upper()

    if not (clean_sql.startswith("SELECT") or clean_sql.startswith("WITH")):
        return False, "Query must begin with SELECT or WITH."

    # Check for forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(r'\b' + keyword + r'\b', clean_sql):
            return False, f"Forbidden keyword detected: {keyword}"

    # Disallow multiple statements
    if ";" in sql.strip(";"):
        return False, "Multiple SQL statements are not allowed."

    return True, ""

def execute_read_query(sql: str) -> Dict[str, Any]:
    """Execute a safe read-only SQL query against the SQLite database."""
    ensure_database_exists()

    safe, msg = is_safe_sql(sql)
    if not safe:
        raise ValueError(f"Security check failed: {msg}")

    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except Exception:
        conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        result_rows = [dict(row) for row in rows]
        return {
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows)
        }
    except Exception as e:
        raise RuntimeError(f"Database execution error: {str(e)}")
    finally:
        conn.close()

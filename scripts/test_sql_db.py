"""Manual smoke-test script for verifying SQLDatabase connectivity."""

from src.data.database import db_connector


def test_sql_db():
    """Print dialect, available tables, and a sample SELECT query result."""
    print(f"Database URL: {db_connector.database_url}")
    db = db_connector.sql_db
    print(f"Dialect: {db.dialect}")
    print(f"Available tables: {db.get_usable_table_names()}")
    
    # Try a simple query
    try:
        res = db.run("SELECT title FROM movies LIMIT 3;")
        print(f"Sample output: {res}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sql_db()

#!/usr/bin/env python3
r"""
Database Explorer Script

An interactive CLI tool for exploring the movie database using SQL queries.
Run with: uv run python scripts/db_explorer.py

Commands:
  - Type SQL queries directly
  \tables       - List all tables
  \schema TABLE - Show schema for a table
  \count TABLE  - Count rows in a table
  \sample TABLE [N] - Show N sample rows (default 5)
  \movies [N]   - Show movies with actors and directors
  \actors [N]   - List actors with movie counts
  \directors [N] - List directors with movie counts
  \genres      - List genres with movie counts
  \quit or \q   - Exit the explorer
  \help or \?   - Show this help message

Examples:
  SELECT * FROM movies LIMIT 5;
  SELECT title, year, vote_average FROM movies WHERE year > 2020 ORDER BY vote_average DESC;
  SELECT a.name, ma.character_name FROM actors a
      JOIN movie_actor ma ON a.id = ma.actor_id
      JOIN movies m ON ma.movie_id = m.id
      WHERE m.title = 'Avatar';
"""

import os
import sys
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from tabulate import tabulate

from src.data.database import db_connector


def get_tables():
    """Get list of all tables in the database."""
    inspector = inspect(db_connector.engine)
    return inspector.get_table_names()


def get_schema(table_name: str) -> Optional[list]:
    """Get schema information for a table."""
    inspector = inspect(db_connector.engine)
    if table_name not in inspector.get_table_names():
        return None
    return inspector.get_columns(table_name)


def execute_query(query: str, params: Optional[dict] = None):
    """Execute a SQL query and return results."""
    session = db_connector.get_db()
    try:
        result = session.execute(text(query), params or {})
        rows = result.fetchall()
        columns = result.keys()
        return columns, rows
    except Exception:
        raise
    finally:
        session.close()


def format_results(columns, rows, max_width: int = 120):
    """Format query results as a table."""
    if not rows:
        return "No rows returned."

    # Convert rows to list of lists for tabulate
    data = [[str(cell) for cell in row] for row in rows]

    # Truncate long cell values
    for row in data:
        for i, cell in enumerate(row):
            if len(cell) > 100:
                row[i] = cell[:97] + "..."

    return tabulate(data, headers=columns, tablefmt="grid", showindex=False)


def print_help():
    """Print help message."""
    print(__doc__)


def cmd_tables():
    """List all tables."""
    tables = get_tables()
    if tables:
        print("\nTables:")
        for table in sorted(tables):
            print(f"  - {table}")
    else:
        print("\nNo tables found.")


def cmd_schema(table_name: str):
    """Show schema for a table."""
    columns = get_schema(table_name)
    if columns is None:
        print(f"\nTable '{table_name}' not found.")
        return

    print(f"\nSchema for table '{table_name}':")
    data = [[col['name'], str(col['type']), col.get('nullable', True)] for col in columns]
    print(tabulate(data, headers=["Column", "Type", "Nullable"], tablefmt="grid"))


def cmd_count(table_name: str):
    """Count rows in a table."""
    tables = get_tables()
    if table_name not in tables:
        print(f"\nTable '{table_name}' not found.")
        return

    try:
        columns, rows = execute_query(f"SELECT COUNT(*) FROM {table_name}")
        count = rows[0][0] if rows else 0
        print(f"\nTable '{table_name}' has {count} rows.")
    except Exception as e:
        print(f"\nError: {e}")


def cmd_sample(table_name: str, limit: int = 5):
    """Show sample rows from a table."""
    tables = get_tables()
    if table_name not in tables:
        print(f"\nTable '{table_name}' not found.")
        return

    try:
        columns, rows = execute_query(f"SELECT * FROM {table_name} LIMIT {limit}")
        print(f"\nSample rows from '{table_name}' (limit {limit}):")
        print(format_results(columns, rows))
    except Exception as e:
        print(f"\nError: {e}")


def cmd_movies(limit: int = 10):
    """Show movies with actors and directors."""
    try:
        query = """
        SELECT m.id, m.title, m.year, m.vote_average,
               GROUP_CONCAT(DISTINCT d.name) as directors,
               GROUP_CONCAT(DISTINCT a.name) as top_actors
        FROM movies m
        LEFT JOIN movie_director md ON m.id = md.movie_id
        LEFT JOIN directors d ON md.director_id = d.id
        LEFT JOIN movie_actor ma ON m.id = ma.movie_id
        LEFT JOIN actors a ON ma.actor_id = a.id
        GROUP BY m.id
        LIMIT {}
        """.format(limit)
        columns, rows = execute_query(query)
        print(f"\nMovies (showing top {limit}):")
        print(format_results(columns, rows))
    except Exception as e:
        print(f"\nError: {e}")


def cmd_actors(limit: int = 20):
    """List actors with movie counts."""
    try:
        query = """
        SELECT a.id, a.name, COUNT(DISTINCT ma.movie_id) as movie_count
        FROM actors a
        JOIN movie_actor ma ON a.id = ma.actor_id
        GROUP BY a.id, a.name
        ORDER BY movie_count DESC
        LIMIT {}
        """.format(limit)
        columns, rows = execute_query(query)
        print(f"\nTop {limit} actors by movie count:")
        print(format_results(columns, rows))
    except Exception as e:
        print(f"\nError: {e}")


def cmd_directors(limit: int = 20):
    """List directors with movie counts."""
    try:
        query = """
        SELECT d.id, d.name, COUNT(DISTINCT md.movie_id) as movie_count
        FROM directors d
        JOIN movie_director md ON d.id = md.director_id
        GROUP BY d.id, d.name
        ORDER BY movie_count DESC
        LIMIT {}
        """.format(limit)
        columns, rows = execute_query(query)
        print(f"\nTop {limit} directors by movie count:")
        print(format_results(columns, rows))
    except Exception as e:
        print(f"\nError: {e}")


def cmd_genres():
    """List genres with movie counts."""
    try:
        query = """
        SELECT g.id, g.name, COUNT(DISTINCT mg.movie_id) as movie_count
        FROM genres g
        LEFT JOIN movie_genre mg ON g.id = mg.genre_id
        GROUP BY g.id, g.name
        ORDER BY movie_count DESC
        """
        columns, rows = execute_query(query)
        print("\nGenres with movie counts:")
        print(format_results(columns, rows))
    except Exception as e:
        print(f"\nError: {e}")


def main():
    """Main interactive loop."""
    print("=" * 60)
    print("  Database Explorer")
    print("  Type \\help for commands or SQL queries directly")
    print("=" * 60)
    print(f"\nConnected to: {db_connector.database_url}\n")

    # Ensure tables exist
    # db_connector.create_tables()

    while True:
        try:
            user_input = input("\ndb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        command = user_input.lower()

        # Handle special commands
        if command in ('\\quit', '\\q', 'exit', 'quit'):
            print("\nGoodbye!")
            break

        if command in ('\\help', '\\?', 'help'):
            print_help()
            continue

        if command == '\\tables':
            cmd_tables()
            continue

        if command == '\\genres':
            cmd_genres()
            continue

        if command.startswith('\\schema '):
            parts = user_input.split(None, 1)
            if len(parts) < 2:
                print("Usage: \\schema TABLE_NAME")
                continue
            cmd_schema(parts[1].strip())
            continue

        if command.startswith('\\count '):
            parts = user_input.split(None, 1)
            if len(parts) < 2:
                print("Usage: \\count TABLE_NAME")
                continue
            cmd_count(parts[1].strip())
            continue

        if command.startswith('\\sample '):
            parts = user_input.split()
            if len(parts) < 2:
                print("Usage: \\sample TABLE_NAME [LIMIT]")
                continue
            table = parts[1]
            try:
                limit = int(parts[2]) if len(parts) > 2 else 5
            except ValueError:
                print("Error: limit must be an integer.")
                continue
            cmd_sample(table, limit)
            continue

        if command.startswith('\\movies'):
            parts = user_input.split()
            try:
                limit = int(parts[1]) if len(parts) > 1 else 10
            except ValueError:
                print("Error: limit must be an integer.")
                continue
            cmd_movies(limit)
            continue

        if command.startswith('\\actors'):
            parts = user_input.split()
            try:
                limit = int(parts[1]) if len(parts) > 1 else 20
            except ValueError:
                print("Error: limit must be an integer.")
                continue
            cmd_actors(limit)
            continue

        if command.startswith('\\directors'):
            parts = user_input.split()
            try:
                limit = int(parts[1]) if len(parts) > 1 else 20
            except ValueError:
                print("Error: limit must be an integer.")
                continue
            cmd_directors(limit)
            continue

        # Execute SQL query
        if not user_input.endswith(';'):
            user_input += ';'

        try:
            columns, rows = execute_query(user_input)
            if rows:
                print(format_results(columns, rows))
                print(f"\n{len(rows)} row(s) returned.")
            else:
                print("Query executed successfully. No rows returned.")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()

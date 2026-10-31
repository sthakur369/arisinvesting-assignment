import sqlite3
from config.config import DB_PATH


def open_database():
    """Open a read-only SQLite connection."""

    # Check whether the database file exists.
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    # Open SQLite in read-only mode.
    database_uri = DB_PATH.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)

    # Add another layer of protection against database modifications.
    connection.execute("PRAGMA query_only = ON")

    # Return the connection so the entire application can reuse it.
    return connection


def validate_user_id(connection, role, user_id):
    """Check whether the entered user ID exists."""

    if role == "advisor":
        query = "SELECT 1 FROM advisor WHERE advisor_id = ?"

    elif role == "sponsor_admin":
        query = "SELECT 1 FROM sponsor WHERE sponsor_id = ?"

    else:
        raise ValueError("Invalid user role.")

    # Execute query using the existing database connection.
    result = connection.execute(query, (user_id,)).fetchone()

    return result is not None


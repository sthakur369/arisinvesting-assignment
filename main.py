import sqlite3

from database.db import open_database
from ui.terminal import select_user, run_chat_session

def main():

    # Keep the database connection available for the entire session.
    connection = None

    try:
        # Step 1: Open the database once when the application starts.
        print("\nConnecting to Ask-ARIS database...")

        connection = open_database()

        print("Database connected successfully (read-only).")

        # Step 2: Display login menu and validate the user's ID.
        user = select_user(connection)

        # Step 3: Start the chat session after successful validation.
        run_chat_session(user, connection)

    except KeyboardInterrupt:
        print("\n\nAsk-ARIS interrupted.")

    except (FileNotFoundError, sqlite3.Error, ValueError) as error:
        print(f"\nApplication error: {error}")

    finally:
        # Close the database connection only when the application exits.
        if connection is not None:
            connection.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()
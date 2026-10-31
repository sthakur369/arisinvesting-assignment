import sys
from database.db import validate_user_id
from assistant import ask
import json
import sqlite3

from rich.console import Console
from rich.table import Table
from rich.markup import escape
from rich.console import Console
from rich.markdown import Markdown

from database.db import execute_sql_query

console = Console()

# Minimalist color codes
class Style:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'

# Stores previous user questions and GPT responses.
conversation_history = []



def print_header(text):
    """Prints a clean, minimalist boxed header."""
    width = 40
    print(f"\n{Style.CYAN}╭{'─' * width}╮")
    print(f"│{text.center(width)}│")
    print(f"╰{'─' * width}╯{Style.RESET}")

def prompt(text):
    """Custom input handler that allows exiting the app from anywhere."""
    user_input = input(text).strip()
    if user_input.lower() == 'exit':
        print(f"\n{Style.CYAN}Goodbye! Thank you for using Ask-ARIS.{Style.RESET}\n")
        sys.exit(0) # Closes the Python program immediately
    return user_input


def display_database_result(database_result):
    """Display database results as a formatted terminal table."""

    columns = database_result["columns"]
    rows = database_result["rows"]

    if not rows:
        print("\nNo matching records found.")
        return

    table = Table(show_header=True, header_style="bold cyan")

    # Create table columns.
    for column in columns:
        table.add_column(escape(str(column)), overflow="fold")

    # Add database records.
    for row in rows:
        table.add_row(*[
            escape(str(value)) if value is not None else "NULL"
            for value in row
        ])

    console.print(table)
    console.print(
        f"[dim]{database_result['row_count']} records returned.[/dim]"
    )


def display_answer(answer):
    Console().print()
    Console().print(Markdown(answer))
    Console().print()


def select_user(connection):
    """Display login menu and validate the selected user."""
    print_header("ASK-ARIS LOGIN")
    print(f"{Style.CYAN}ℹ Tip: Type 'exit' at any time to quit.{Style.RESET}\n")

    while True:
        print("Select User Type:")
        print("  1. Advisor")
        print("  2. Sponsor Admin")

        choice = prompt("\n➜ Choice (1 or 2): ")

        if choice == "1":
            role, id_col, label = "advisor", "advisor_id", "Advisor"
        elif choice == "2":
            role, id_col, label = "sponsor_admin", "sponsor_id", "Sponsor Admin"
        else:
            print(f"{Style.RED}✗ Invalid choice. Please select 1 or 2.{Style.RESET}")
            continue

        # Keep asking until a valid ID is entered or user goes back.
        while True:
            print()
            entered_id = prompt(f"➜ Enter {label} ID (type 'b' to go back): ")

            if entered_id.lower() == "b":
                print("") # Spacing before menu reprints
                break

            try:
                user_id = int(entered_id)
                if user_id <= 0:
                    raise ValueError
            except ValueError:
                print(f"{Style.RED}✗ Please enter a valid numeric ID.{Style.RESET}")
                continue

            
            # ----------------------------------------------------------------------------------
            # ✅ Validate using the shared connection

            if validate_user_id(connection, role, user_id):
                # Return immediately; the success message will print in the chat_loop
                return {"role": role, id_col: user_id}

            print(f"{Style.RED}✗ Invalid {label} ID: {user_id}.{Style.RESET}")


def run_chat_session(user, connection):
    # Stores the compressed summary and recent conversation.
    conversation = {
        "summary": "",
        "history": []
    }

    """Start the interactive CMD chat loop."""
    if user["role"] == "advisor":
        identity = f"Advisor {user['advisor_id']}"
    else:
        identity = f"Sponsor Admin {user['sponsor_id']}"

    print_header("✨ Welcome to Ask-ARIS")
    print(f"{Style.GREEN}✓ Logged in successfully as {identity}.{Style.RESET}\n")

    

    while True:
        print()
        question = prompt(f"{Style.GREEN}Ask-ARIS > {Style.RESET}")

        if not question:
            continue

        print(f"{Style.CYAN}⚙ Thinking...{Style.RESET}")

        try:
            response = ask(question, user, connection, conversation)
            print(json.dumps(response, indent=2, ensure_ascii=False))

        except Exception as error:
            print(f"\n{Style.RED}✗ Error: {error}{Style.RESET}\n")
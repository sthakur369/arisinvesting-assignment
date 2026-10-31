import sys
from database.db import validate_user_id
from llm.openai_llm import generate_response

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


def run_chat_session(user):
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
        question = prompt(f"{Style.GREEN}Ask-ARIS > {Style.RESET}")

        if not question:
            continue

        print(f"{Style.CYAN}⚙ Thinking...{Style.RESET}")

        try:
            answer = generate_response(question, conversation)

            print(f"\n{Style.GREEN}{answer}{Style.RESET}\n")

            # Save both messages for the next API request.
            conversation_history.append({
                "role": "user",
                "content": question
            })

            conversation_history.append({
                "role": "assistant",
                "content": answer
            })

            # print(f"[DEBUG] conversation_history: {conversation_history}")
            # print(f"[DEBUG] conversation with summary:::: {conversation}")


        except Exception as error:
            print(f"\n{Style.RED}✗ OpenAI API Error: {error}{Style.RESET}\n")
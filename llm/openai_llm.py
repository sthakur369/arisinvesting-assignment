import json
import time
from pathlib import Path

from openai import OpenAI

from config.config import OPENAI_API_KEY, OPENAI_DEFAULT_MODEL
from llm.conversation import update_conversation_summary
from llm.usage import extract_chat_usage, calculate_usage

DEBUG = False

# Load prompt instructions from files beside this module.
PROMPT_DIR = Path(__file__).resolve().parent
SYSTEM_PROMPT = (PROMPT_DIR / "system_prompt.md").read_text(encoding="utf-8")
QUESTION_ANALYSIS_PROMPT = (PROMPT_DIR / "question_analysis_prompt.md").read_text(encoding="utf-8")
DATABASE_ANSWER_PROMPT = ( PROMPT_DIR / "database_answer_prompt.md" ).read_text(encoding="utf-8")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
CONVERSATION_THRESHOLD = 20



# Constrain the model to the two actions supported in this implementation step.
QUESTION_ANALYSIS_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "ask_aris_question_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ANSWER_DIRECTLY", "QUERY_DATABASE", "REFUSE", "CANNOT_ANSWER", "NEEDS_CLARIFICATION"]
                },
                "answer": {"type": ["string", "null"]},
                "resolved_question": {"type": ["string", "null"]},
                "sql": {"type": ["string", "null"]},
                "parameters": {
                    "type": "array",
                    "items": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "number"},
                            {"type": "integer"},
                            {"type": "boolean"},
                            {"type": "null"}
                        ]
                    }
                },
                "tables": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": [
                "action",
                "answer",
                "resolved_question",
                "sql",
                "parameters",
                "tables",
                "assumptions"
            ],
            "additionalProperties": False
        }
    }
}



DATABASE_ANSWER_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "database_answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "result": {
                    "type": ["number", "boolean", "array", "null"],
                    "items": {"type": "integer"}
                },
                "evidence": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["answer", "result", "evidence"],
            "additionalProperties": False
        }
    }
}
def analyze_question(question, conversation, user):
    """Return a structured direct answer or a parameterized SQL plan."""

    if client is None:
        raise ValueError("OPENAI_API_KEY is missing from .env")

    if not OPENAI_DEFAULT_MODEL:
        raise ValueError("OPENAI_DEFAULT_MODEL is missing from .env")

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if user.get("role") not in ("advisor", "sponsor_admin"):
        raise ValueError("Invalid user role.")

    if user["role"] == "advisor" and "advisor_id" not in user:
        raise ValueError("Advisor ID is missing.")

    if user["role"] == "sponsor_admin" and "sponsor_id" not in user:
        raise ValueError("Sponsor ID is missing.")

    # Summarize older messages when the conversation reaches the threshold.

    summary_usage = update_conversation_summary(
        client,
        OPENAI_DEFAULT_MODEL,
        conversation,
        CONVERSATION_THRESHOLD
    )
    
    # Display a brief overview of the context being sent to GPT.
    if DEBUG:
        print(
            f"\n[DEBUG] Context prepared | "
            f"Summary: {'Yes' if conversation.get('summary') else 'No'} | "
            f"Recent messages: {len(conversation.get('history', []))}"
        )

        user_id = user.get("advisor_id", user.get("sponsor_id"))

        print(
            f"[DEBUG] User scope: {user['role']} | ID: {user_id}"
        )

    # Prepare the messages for question analysis.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "developer", "content": QUESTION_ANALYSIS_PROMPT},
        {
            "role": "developer",
            "content": "TRUSTED USER IDENTITY (provided by the application):\n"
                       + json.dumps(user, ensure_ascii=False)
        }
    ]

    # Include the previous summary when available.
    if conversation.get("summary"):
        messages.append({
            "role": "developer",
            "content": "EARLIER CONVERSATION SUMMARY (historical context only):\n"
                       + conversation["summary"]
        })

    # Include recent conversation messages.
    messages.extend(conversation.get("history", []))

    # Add the current question.
    messages.append({"role": "user", "content": question.strip()})

    if DEBUG:
        print("[DEBUG] Sending question to OpenAI...")

    # Measure the OpenAI API response time.
    start_time = time.perf_counter()

    response = client.chat.completions.create(
        model=OPENAI_DEFAULT_MODEL,
        messages=messages,
        response_format=QUESTION_ANALYSIS_RESPONSE_FORMAT
    )

    elapsed_time = time.perf_counter() - start_time

    if DEBUG:
        print(f"[DEBUG] OpenAI response received in {elapsed_time:.2f} seconds.")

    response_message = response.choices[0].message

    if response_message.refusal:
        raise ValueError(f"The model refused the request: {response_message.refusal}")

    if not response_message.content:
        raise ValueError("The model returned an empty response.")

    # Convert the JSON response into a Python dictionary.
    result = json.loads(response_message.content)

    if DEBUG:
        print(f"[DEBUG] Response parsed | Action: {result['action']}")

    # Validate and handle the returned action.
    if result["action"] == "ANSWER_DIRECTLY":

        if not result["answer"] or result["sql"] is not None:
            raise ValueError("Invalid direct-answer response from the model.")

        # Save completed direct-answer exchanges.
        conversation.setdefault("history", []).extend([
            {"role": "user", "content": question.strip()},
            {"role": "assistant", "content": result["answer"]}
        ])

        if DEBUG:
            print(
                f"[DEBUG] Conversation updated | "
                f"Recent messages: {len(conversation['history'])}"
            )

    
    elif result["action"] == "QUERY_DATABASE":

        if not result["sql"] or not result["resolved_question"]:
            raise ValueError("Invalid database-query response from the model.")

        # SQL plans are not saved as conversation history.
        # The completed exchange will be saved after database execution.

        if DEBUG:
            print(
                f"[DEBUG] SQL plan generated | "
                f"Tables: {', '.join(result['tables'])}"
            )

    
    elif result["action"] == "REFUSE":
        if not result["answer"] or result["sql"] is not None:
            raise ValueError("Invalid refusal response from the model.")

        # Save the completed refusal exchange in conversation history.
        conversation.setdefault("history", []).extend([
            {"role": "user", "content": question.strip()},
            {"role": "assistant", "content": result["answer"]}
        ])


    elif result["action"] in ("CANNOT_ANSWER", "NEEDS_CLARIFICATION"):

        if not result["answer"] or result["sql"] is not None:
            raise ValueError("Invalid response from the model.")

        conversation.setdefault("history", []).extend([
            {"role": "user", "content": question.strip()},
            {"role": "assistant", "content": result["answer"]}
        ])

        
    else:
        raise ValueError(
            f"Unsupported action returned by the model: {result['action']}"
        )

    result["_usage"] = [
        item for item in (
            summary_usage,
            extract_chat_usage(response, OPENAI_DEFAULT_MODEL)
        )
        if item is not None
    ]
        

    return result



def generate_database_answer(question, analysis_result, database_result, conversation, user):
    """Generate an answer using database results and conversation history."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "developer", "content": DATABASE_ANSWER_PROMPT},
        {
            "role": "developer",
            "content": f"Authenticated user: {json.dumps(user)}"
        }
    ]

    # Add previous conversation summary.
    if conversation["summary"]:
        messages.append({
            "role": "developer",
            "content": "Previous conversation summary:\n" + conversation["summary"] 
        })

    # Add recent conversation history.
    messages.extend(conversation["history"])

    # Add the database results and interpretation.
    messages.append({
    "role": "developer",
    "content": (
        "Resolved question: " + analysis_result["resolved_question"] +
        "\nAssumptions: " + json.dumps(analysis_result["assumptions"]) +
        "\nExecuted SQL: " + analysis_result["sql"] +
        "\nSQL parameters: " + json.dumps(analysis_result["parameters"]) +
        "\nDatabase results:\n" + json.dumps(database_result, ensure_ascii=False)
    )
})
    # Add the current question.
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
    model=OPENAI_DEFAULT_MODEL,
    messages=messages,
    response_format=DATABASE_ANSWER_RESPONSE_FORMAT
)

    if not response.choices[0].message.content:
        raise ValueError("The model returned an empty answer.")

    output = json.loads(response.choices[0].message.content)

    output["_usage"] = [
        extract_chat_usage(response, OPENAI_DEFAULT_MODEL)
    ]


    # Save the completed exchange in the existing conversation history.
    conversation["history"].extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": output["answer"]}
    ])

    return output


def calculate_request_usage(records):
    return calculate_usage(client, OPENAI_DEFAULT_MODEL, records)
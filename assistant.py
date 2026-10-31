
from database.db import open_database, execute_sql_query
from llm.openai_llm import (
    analyze_question,
    generate_database_answer,
    calculate_request_usage
)
import json

DEBUG = False


def ask(question, user, connection=None, conversation=None):
    """Process a user question and return the final response."""

    close_connection = connection is None
    if close_connection:
        connection = open_database()

    if conversation is None:
        conversation = {"summary": "", "history": []}

    # Store usage from every LLM call.
    usage_records = []

    try:
        # Understand the question and determine the required action.
        analysis = analyze_question(question, conversation, user)

        # Collect usage from question analysis and summarization.
        usage_records.extend(analysis.pop("_usage", []))

        action = analysis["action"]
        assumptions = analysis["assumptions"]

        if action == "QUERY_DATABASE":

            if DEBUG:
                print("\n[DEBUG] Generated SQL:")
                print(analysis["sql"])
                print("[DEBUG] SQL parameters:", analysis["parameters"])
                print("[DEBUG] Assumptions:", assumptions)

            # Execute the generated SQL.
            database_result = execute_sql_query(
                connection, analysis["sql"], analysis["parameters"]
            )

            if DEBUG:
                print("\n[DEBUG] Database result columns:")
                print(database_result["columns"])
                print("[DEBUG] Database row count:", database_result["row_count"])
                print("[DEBUG] Database result rows:")
                print(json.dumps(database_result["rows"], indent=2, ensure_ascii=False))

            # Generate the final answer and structured result.
            generated = generate_database_answer(
                question, analysis, database_result, conversation, user
            )

            # Collect usage from database-answer generation.
            usage_records.extend(generated.pop("_usage", []))

            if DEBUG:
                print("\n[DEBUG] Second LLM output:")
                print(json.dumps(generated, indent=2, ensure_ascii=False))

            answer = generated["answer"]
            result = generated["result"]
            evidence = generated["evidence"]
            status = "ANSWERED"

        else:
            evidence = []
            answer = analysis["answer"]
            result = None

            status = {
                "ANSWER_DIRECTLY": "ANSWERED",
                "REFUSE": "REFUSED",
                "CANNOT_ANSWER": "CANNOT_ANSWER",
                "NEEDS_CLARIFICATION": "NEEDS_CLARIFICATION"
            }[action]

        # Calculate total token usage and API cost.
        try:
            usage = calculate_request_usage(usage_records)
        except Exception:
            usage = {
                "input_tokens": sum(item["input_tokens"] for item in usage_records),
                "output_tokens": sum(item["output_tokens"] for item in usage_records),
                "cost_usd": None
            }

        return {
            "status": status,
            "answer": answer,
            "result": result,
            "evidence": evidence,
            "assumptions": assumptions,
            "usage": usage
        }

    finally:
        if close_connection:
            connection.close()

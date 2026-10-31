
from llm.conversation import update_conversation_summary
from pathlib import Path
from openai import OpenAI

from config.config import OPENAI_API_KEY, OPENAI_DEFAULT_MODEL, CONVERSATION_THRESHOLD


# Load system prompt from the separate Markdown file.
PROMPT_PATH = Path(__file__).parent / "system_prompt.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

# Initialize OpenAI client once and reuse it.
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def generate_response(question, conversation):
    """Generate GPT response using recent history and conversation summary."""

    if client is None:
        raise ValueError("OPENAI_API_KEY is missing from .env")

    if not OPENAI_DEFAULT_MODEL:
        raise ValueError("OPENAI_DEFAULT_MODEL is missing from .env")

    # Summarize every 10 exchanges before processing the next question.
    update_conversation_summary(
        client,
        OPENAI_DEFAULT_MODEL,
        conversation,
        CONVERSATION_THRESHOLD
    )

    # Prepare messages for the API request.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Include compressed context when available.
    if conversation["summary"]:
        messages.append({
            "role": "assistant",
            "content": (
                "Earlier conversation context for continuity:\n"
                + conversation["summary"]
            )
        })

    # Include recent conversation messages.
    messages.extend(conversation["history"])

    # Add the current question.
    messages.append({
        "role": "user",
        "content": question
    })

    response = client.chat.completions.create(
        model=OPENAI_DEFAULT_MODEL,
        messages=messages
    )

    answer = response.choices[0].message.content

    if not answer:
        raise ValueError("GPT returned an empty response.")

    answer = answer.strip()

    # Store the completed exchange for future context.
    conversation["history"].extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer}
    ])

    return answer

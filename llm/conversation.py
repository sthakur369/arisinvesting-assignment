
import json
from pathlib import Path

# Load system prompt from the separate Markdown file.
PROMPT_PATH = Path(__file__).parent / "summary_prompt.md"
SUMMARY_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


def update_conversation_summary(client, model, conversation, conversation_threshold=20):
    """Summarize every 10 completed exchanges and reset recent history."""

    history = conversation["history"]

    # 10 exchanges = 20 messages (10 user + 10 assistant).
    if len(history) < conversation_threshold:
        return

    # Include the previous summary so older context is not lost.
    conversation_data = {
        "previous_summary": conversation["summary"],
        "recent_conversation": history
    }

    print("\n[DEBUG] Conversation summarization started.")
    print(f"[DEBUG] Previous summary exists: {bool(conversation['summary'])}")
    print(f"[DEBUG] Messages being summarized: {len(history)}")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {
                "role": "user",
                "content": json.dumps(conversation_data, ensure_ascii=False)
            }
        ]
    )

    new_summary = response.choices[0].message.content

    # Validate before updating or clearing the conversation.
    if not new_summary or not new_summary.strip():
        raise ValueError("Conversation summarization returned an empty response.")

    # Replace the previous summary with the updated summary.
    conversation["summary"] = new_summary.strip()

    # Clear old messages only after successful summarization.
    history.clear()

    print(f"[DEBUG] New summary: {conversation['summary']}")
    print("[DEBUG] Recent conversation history cleared.")

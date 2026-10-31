
import json


PRICING_RESPONSE_FORMAT = {
    "type": "json_schema",
    "name": "usage_pricing",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "pricing_verified": {"type": "boolean"},
            "input_price": {"type": ["number", "null"]},
            "cached_input_price": {"type": ["number", "null"]},
            "output_price": {"type": ["number", "null"]},
            "web_search_price_per_1000": {"type": ["number", "null"]},
            "cost_usd": {"type": ["number", "null"]},
            "source_url": {"type": ["string", "null"]}
        },
        "required": [
            "pricing_verified",
            "input_price",
            "cached_input_price",
            "output_price",
            "web_search_price_per_1000",
            "cost_usd",
            "source_url"
        ],
        "additionalProperties": False
    }
}


def extract_chat_usage(response, requested_model):
    """Extract token usage from a Chat Completions response."""

    usage = response.usage

    if usage is None:
        return None

    details = getattr(usage, "prompt_tokens_details", None)

    return {
        "model": response.model or requested_model,
        "input_tokens": usage.prompt_tokens or 0,
        "output_tokens": usage.completion_tokens or 0,
        "cached_input_tokens": getattr(details, "cached_tokens", 0) or 0
    }


def calculate_usage(client, model, records):
    """Find current model pricing and calculate total API usage cost."""

    input_tokens = sum(item["input_tokens"] for item in records)
    output_tokens = sum(item["output_tokens"] for item in records)

    models = list({item["model"] for item in records})

    if len(models) != 1:
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": None
        }

    response = client.responses.create(
        model=model,
        tools=[
            {
                "type": "web_search",
                "filters": {
                    "allowed_domains": [
                        "openai.com",
                        "developers.openai.com"
                    ]
                }
            }
        ],
        tool_choice="required",
        input=f"""
        Find the current official OpenAI API pricing for model: {models[0]}.

        Use standard, short-context API pricing.
        Find input, cached input and output prices per million tokens.
        Also find the web search price per 1000 calls.

        Calculate the total cost for these API usage records.
        Each record contains input tokens, output tokens and cached input tokens.

        Usage records:
        {json.dumps(records)}

        Calculate using:
        - Uncached input tokens at the input price.
        - Cached input tokens at the cached input price.
        - Output tokens at the output price.

        Use official OpenAI pricing sources only.
        Do not guess prices. If pricing cannot be verified,
        set pricing_verified to false and cost_usd to null.

        Return the pricing rates and calculated cost in the required JSON.
        """,
        text={"format": PRICING_RESPONSE_FORMAT}
    )

    pricing = json.loads(response.output_text)

    # Include the pricing lookup call's own token usage.
    lookup_usage = response.usage

    lookup_cost = 0.0

    if lookup_usage:
        lookup_input = lookup_usage.input_tokens or 0
        lookup_output = lookup_usage.output_tokens or 0

        input_tokens += lookup_input
        output_tokens += lookup_output

        details = getattr(lookup_usage, "input_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) or 0

        if pricing["pricing_verified"]:
            lookup_cost = (
                (lookup_input - cached) * pricing["input_price"]
                + cached * pricing["cached_input_price"]
                + lookup_output * pricing["output_price"]
            ) / 1_000_000

            search_calls = sum(
                1 for item in response.output
                if getattr(item, "type", None) == "web_search_call"
            )

            lookup_cost += (
                search_calls
                * pricing["web_search_price_per_1000"]
                / 1000
            )

    cost = None

    if pricing["pricing_verified"] and pricing["cost_usd"] is not None:
        cost = round(pricing["cost_usd"] + lookup_cost, 10)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost
    }

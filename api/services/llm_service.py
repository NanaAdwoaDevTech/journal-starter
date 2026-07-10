import json
from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from api.config import get_settings


def _default_client() -> AsyncOpenAI:
    """Construct the real OpenAI client from application settings."""
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


async def analyze_journal_entry(
    entry_id: str,
    entry_text: str,
    client: AsyncOpenAI | None = None,
) -> dict:
    """Analyze a journal entry using an OpenAI-compatible LLM."""
    if client is None:
        client = _default_client()

    settings = get_settings()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a journaling assistant. Analyze the journal entry "
                "and respond with ONLY a JSON object (no markdown, no extra "
                "text) with exactly these keys: "
                '"sentiment" (one of "positive", "negative", "neutral"), '
                '"summary" (a 2 sentence summary), '
                '"topics" (a list of 2-4 short topic strings).'
            ),
        },
        {
            "role": "user",
            "content": entry_text,
        },
    ]

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=cast(list[ChatCompletionMessageParam], messages),
    )

    raw_content = response.choices[0].message.content
    if raw_content is None:
        raise ValueError("LLM response had no content to parse")
    parsed = json.loads(raw_content)

    return {
        "entry_id": entry_id,
        "sentiment": parsed["sentiment"],
        "summary": parsed["summary"],
        "topics": parsed["topics"],
    }

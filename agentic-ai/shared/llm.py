"""Anthropic client factory — Sonnet 4.5 for complex reasoning, Haiku 4.5 for routing/classification."""
import anthropic
from langfuse import Langfuse

from shared.config import settings

_client: anthropic.AsyncAnthropic | None = None
_langfuse: Langfuse | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def get_langfuse() -> Langfuse:
    global _langfuse
    if _langfuse is None:
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return _langfuse


# Model aliases — change here to update everywhere
SONNET = "claude-sonnet-4-5"   # credit risk reasoning, CAM drafting, fraud recommendation
HAIKU = "claude-haiku-4-5-20251001"   # classification, scoring, channel selection


async def complete(
    messages: list[dict],
    model: str = SONNET,
    system: str = "",
    max_tokens: int = 1024,
    trace_name: str = "llm_call",
) -> str:
    """Single-turn completion with Langfuse tracing."""
    client = get_client()
    lf = get_langfuse()

    generation = lf.generation(
        name=trace_name,
        model=model,
        input=messages,
    )

    try:
        resp = await client.messages.create(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        text = resp.content[0].text
        generation.end(output=text, usage={"input": resp.usage.input_tokens, "output": resp.usage.output_tokens})
        return text
    except Exception as exc:
        generation.end(level="ERROR", status_message=str(exc))
        raise

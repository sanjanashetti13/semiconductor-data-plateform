"""Groq LLM client — prompt in, text out. No SQL."""

from __future__ import annotations

from groq import Groq

from ai.config import Settings, get_settings


def get_client(settings: Settings | None = None) -> Groq:
    """Create a Groq client from settings."""
    cfg = settings or get_settings()
    return Groq(api_key=cfg.groq_api_key)


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    json_mode: bool = False,
    settings: Settings | None = None,
) -> str:
    """
    Send a chat completion request to Groq and return the assistant text.

    When ``json_mode`` is True, the model is asked to return valid JSON.
    """
    cfg = settings or get_settings()
    client = get_client(cfg)

    kwargs: dict = {
        "model": model or cfg.groq_model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    return content or ""

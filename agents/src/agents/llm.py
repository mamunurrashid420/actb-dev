"""LangChain LLM wrapper for agent calls.

Rate Limiting:
    This module implements per-provider rate limiting using LangChain's InMemoryRateLimiter.
    Rate limiters are defined as module-level singletons to ensure consistent rate limiting
    across all LLMClient instances. All providers use 5 req/sec (300 RPM).
"""

import os
from typing import TypeVar

from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from pydantic import BaseModel

_cache_enabled = False

# Per-provider rate limiters (module-level singletons)
# These are shared across all LLMClient instances to ensure consistent rate limiting
_rate_limiters: dict[str, InMemoryRateLimiter] = {
    "google": InMemoryRateLimiter(requests_per_second=5, max_bucket_size=10),
    "anthropic": InMemoryRateLimiter(requests_per_second=5, max_bucket_size=10),
    "openai": InMemoryRateLimiter(requests_per_second=5, max_bucket_size=10),
}

# Default rate limiter for unknown providers
_default_rate_limiter = InMemoryRateLimiter(requests_per_second=5, max_bucket_size=10)


def get_rate_limiter(provider: str) -> InMemoryRateLimiter:
    """Get the rate limiter for a given provider."""
    return _rate_limiters.get(provider, _default_rate_limiter)


def enable_cache() -> None:
    """Enable in-memory caching for all LLM calls.

    Cached responses are stored for the duration of the Python session.
    Useful for eval reruns and notebook iteration.
    """
    global _cache_enabled
    if not _cache_enabled:
        set_llm_cache(InMemoryCache())
        _cache_enabled = True


def disable_cache() -> None:
    """Disable LLM caching."""
    global _cache_enabled
    set_llm_cache(None)
    _cache_enabled = False


T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "google:gemini-3-flash-preview"


def parse_model_string(model_string: str) -> tuple[str, str]:
    """Parse 'provider:model' format. Returns (provider, model_name)."""
    if ":" in model_string:
        provider, model_name = model_string.split(":", 1)
        return provider.lower(), model_name
    # Legacy: assume anthropic if no prefix
    return "anthropic", model_string


class LLMClient:
    """Thin wrapper around LangChain for LLM calls. Supports multiple providers."""

    def __init__(self, model: str | None = None):
        model_string = model or os.getenv("AGENT_MODEL", DEFAULT_MODEL)
        provider, model_name = parse_model_string(model_string)
        rate_limiter = get_rate_limiter(provider)

        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            self.llm = ChatGoogleGenerativeAI(
                model=model_name, rate_limiter=rate_limiter
            )
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            self.llm = ChatAnthropic(model=model_name, rate_limiter=rate_limiter)
        elif provider == "openai":
            from langchain_openai import ChatOpenAI

            self.llm = ChatOpenAI(model=model_name, rate_limiter=rate_limiter)
        else:
            raise ValueError(
                f"Unknown provider: {provider}. Use 'anthropic:', 'google:', or 'openai:'"
            )

    async def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: type[T],
    ) -> T:
        """Generate a structured response matching the output schema."""
        structured_llm = self.llm.with_structured_output(output_schema)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        return await structured_llm.ainvoke(messages)

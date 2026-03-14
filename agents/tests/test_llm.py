"""Unit tests for LLMClient rate limiting."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the llm module directly to avoid triggering agents/__init__.py
# which has a broken import dependency during test collection
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "agents.llm", Path(__file__).parent.parent / "src" / "agents" / "llm.py"
)
llm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_module)

LLMClient = llm_module.LLMClient
_default_rate_limiter = llm_module._default_rate_limiter
_rate_limiters = llm_module._rate_limiters
get_rate_limiter = llm_module.get_rate_limiter


class TestRateLimiterConfiguration:
    """Tests for rate limiter configuration."""

    def test_google_rate_limiter_exists(self):
        """Google provider should have a rate limiter configured."""
        assert "google" in _rate_limiters
        limiter = _rate_limiters["google"]
        assert limiter.requests_per_second == 5
        assert limiter.max_bucket_size == 10

    def test_anthropic_rate_limiter_exists(self):
        """Anthropic provider should have a rate limiter configured."""
        assert "anthropic" in _rate_limiters
        limiter = _rate_limiters["anthropic"]
        assert limiter.requests_per_second == 5
        assert limiter.max_bucket_size == 10

    def test_openai_rate_limiter_exists(self):
        """OpenAI provider should have a rate limiter configured."""
        assert "openai" in _rate_limiters
        limiter = _rate_limiters["openai"]
        assert limiter.requests_per_second == 5
        assert limiter.max_bucket_size == 10

    def test_default_rate_limiter_configuration(self):
        """Default rate limiter should have standard settings."""
        assert _default_rate_limiter.requests_per_second == 5
        assert _default_rate_limiter.max_bucket_size == 10


class TestGetRateLimiter:
    """Tests for get_rate_limiter function."""

    def test_get_google_rate_limiter(self):
        """Should return google-specific rate limiter."""
        limiter = get_rate_limiter("google")
        assert limiter is _rate_limiters["google"]

    def test_get_anthropic_rate_limiter(self):
        """Should return anthropic-specific rate limiter."""
        limiter = get_rate_limiter("anthropic")
        assert limiter is _rate_limiters["anthropic"]

    def test_get_openai_rate_limiter(self):
        """Should return openai-specific rate limiter."""
        limiter = get_rate_limiter("openai")
        assert limiter is _rate_limiters["openai"]

    def test_unknown_provider_gets_default_rate_limiter(self):
        """Unknown provider should get the default rate limiter."""
        limiter = get_rate_limiter("unknown_provider")
        assert limiter is _default_rate_limiter


class TestLLMClientRateLimiting:
    """Tests for LLMClient rate limiter attachment."""

    def test_google_model_gets_rate_limiter(self):
        """Google model should be constructed with rate limiter."""
        mock_chat_class = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "langchain_google_genai": MagicMock(
                    ChatGoogleGenerativeAI=mock_chat_class
                )
            },
        ):
            # Reload module to pick up patched import
            import importlib

            spec = importlib.util.spec_from_file_location(
                "agents_llm_test",
                Path(__file__).parent.parent / "src" / "agents" / "llm.py",
            )
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)

            test_module.LLMClient(model="google:gemini-pro")

            mock_chat_class.assert_called_once()
            call_kwargs = mock_chat_class.call_args.kwargs
            assert "rate_limiter" in call_kwargs
            assert call_kwargs["rate_limiter"] is test_module._rate_limiters["google"]

    def test_anthropic_model_gets_rate_limiter(self):
        """Anthropic model should be constructed with rate limiter."""
        mock_chat_class = MagicMock()
        with patch.dict(
            "sys.modules",
            {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_class)},
        ):
            import importlib

            spec = importlib.util.spec_from_file_location(
                "agents_llm_test2",
                Path(__file__).parent.parent / "src" / "agents" / "llm.py",
            )
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)

            test_module.LLMClient(model="anthropic:claude-3-sonnet")

            mock_chat_class.assert_called_once()
            call_kwargs = mock_chat_class.call_args.kwargs
            assert "rate_limiter" in call_kwargs
            assert (
                call_kwargs["rate_limiter"] is test_module._rate_limiters["anthropic"]
            )

    def test_openai_model_gets_rate_limiter(self):
        """OpenAI model should be constructed with rate limiter."""
        mock_chat_class = MagicMock()
        with patch.dict(
            "sys.modules", {"langchain_openai": MagicMock(ChatOpenAI=mock_chat_class)}
        ):
            import importlib

            spec = importlib.util.spec_from_file_location(
                "agents_llm_test3",
                Path(__file__).parent.parent / "src" / "agents" / "llm.py",
            )
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)

            test_module.LLMClient(model="openai:gpt-4")

            mock_chat_class.assert_called_once()
            call_kwargs = mock_chat_class.call_args.kwargs
            assert "rate_limiter" in call_kwargs
            assert call_kwargs["rate_limiter"] is test_module._rate_limiters["openai"]

    def test_different_providers_get_different_rate_limiters(self):
        """Different providers should get different rate limiter instances."""
        mock_google = MagicMock()
        with patch.dict(
            "sys.modules",
            {"langchain_google_genai": MagicMock(ChatGoogleGenerativeAI=mock_google)},
        ):
            import importlib

            spec = importlib.util.spec_from_file_location(
                "agents_llm_test4",
                Path(__file__).parent.parent / "src" / "agents" / "llm.py",
            )
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)

            test_module.LLMClient(model="google:gemini-pro")

            google_limiter = mock_google.call_args.kwargs["rate_limiter"]

            # Verify they are different
            assert google_limiter is test_module._rate_limiters["google"]
            assert google_limiter is not test_module._rate_limiters["anthropic"]
            assert google_limiter is not test_module._rate_limiters["openai"]

    def test_rate_limiters_are_singletons(self):
        """Rate limiters should be shared across LLMClient instances."""
        # Multiple calls to get_rate_limiter should return same instance
        limiter1 = get_rate_limiter("google")
        limiter2 = get_rate_limiter("google")

        assert limiter1 is limiter2


class TestLLMClientUnknownProvider:
    """Tests for unknown provider handling."""

    def test_unknown_provider_raises_error(self):
        """Unknown provider should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            LLMClient(model="unknown:some-model")

        assert "Unknown provider: unknown" in str(exc_info.value)
        assert "anthropic:" in str(exc_info.value)
        assert "google:" in str(exc_info.value)
        assert "openai:" in str(exc_info.value)

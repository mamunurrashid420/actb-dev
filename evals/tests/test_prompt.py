"""Tests for prompt resolution."""

import pytest

from evals.framework.prompt import resolve_prompt


class TestPromptResolver:
    """Tests for prompt resolution from various sources."""

    def test_inline_prompt_returned_directly(self):
        """Inline prompts should be returned as-is."""
        prompt = "You are a helpful assistant."
        resolved = resolve_prompt(prompt)

        assert resolved.content == prompt
        assert resolved.source == "inline"
        assert resolved.ref is None
        assert resolved.hash is not None
        assert len(resolved.hash) == 12

    def test_py_reference_imports_from_module(self):
        """py:// prompts should import from Python modules."""
        resolved = resolve_prompt("py://agents.intent_classifier.agent:DEFAULT_PROMPT")

        assert resolved.source == "py"
        assert resolved.ref == "py://agents.intent_classifier.agent:DEFAULT_PROMPT"
        assert "IntentClassifier" in resolved.content
        assert len(resolved.hash) == 12

    def test_invalid_module_raises_value_error(self):
        """Invalid module paths should raise ValueError."""
        with pytest.raises(ValueError, match="Module not found"):
            resolve_prompt("py://nonexistent.module:PROMPT")

    def test_invalid_attribute_raises_value_error(self):
        """Invalid attributes should raise ValueError."""
        with pytest.raises(ValueError, match="Attribute .* not found"):
            resolve_prompt("py://agents.intent_classifier.agent:NONEXISTENT")

    def test_missing_colon_raises_value_error(self):
        """Missing colon in py:// reference should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid py:// reference"):
            resolve_prompt("py://agents.intent_classifier.agent")

    def test_xms_reference_not_implemented(self):
        """xms:// references should raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            resolve_prompt("xms://prompt-id@v1")

    def test_hash_is_deterministic(self):
        """Same content should produce same hash."""
        prompt = "Test prompt content"
        resolved1 = resolve_prompt(prompt)
        resolved2 = resolve_prompt(prompt)

        assert resolved1.hash == resolved2.hash

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        resolved1 = resolve_prompt("Prompt A")
        resolved2 = resolve_prompt("Prompt B")

        assert resolved1.hash != resolved2.hash

"""Prompt resolver for fetching prompts from various sources."""

import hashlib
import importlib
from dataclasses import dataclass


@dataclass
class ResolvedPrompt:
    """Prompt with provenance information."""

    content: str
    source: str  # "py" or "inline" (Phase 2: "xms")
    ref: str | None  # Original reference (e.g., "py://agents.ic:PROMPT")
    version: str | None  # Version if from XMS
    hash: str  # SHA256[:12] of content


def _hash_content(content: str) -> str:
    """Compute short SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()[:12]


class PromptResolver:
    """Resolves prompts from various sources."""

    @staticmethod
    def resolve(prompt: str) -> ResolvedPrompt:
        """Resolve prompt from any source.

        Supported formats:
        - Inline string (no prefix): Used directly
        - py://module.path:ATTRIBUTE: Import from Python module
        - xms://prompt-id@version: From XMS (Phase 2, not implemented)
        """
        # Inline string (no prefix)
        if not prompt.startswith(("xms://", "py://")):
            return ResolvedPrompt(
                content=prompt,
                source="inline",
                ref=None,
                version=None,
                hash=_hash_content(prompt),
            )

        # Python module reference
        if prompt.startswith("py://"):
            return PromptResolver._resolve_py(prompt)

        # XMS reference (Phase 2)
        if prompt.startswith("xms://"):
            raise NotImplementedError(
                "XMS integration not yet implemented. Use py:// or inline prompts."
            )

        raise ValueError(f"Unknown prompt source: {prompt}")

    @staticmethod
    def _resolve_py(ref: str) -> ResolvedPrompt:
        """Resolve a py:// reference."""
        # Parse py://module.path:ATTRIBUTE
        path = ref.replace("py://", "")
        if ":" not in path:
            raise ValueError(
                f"Invalid py:// reference: {ref}. Expected format: py://module.path:ATTRIBUTE"
            )

        module_path, attr_name = path.rsplit(":", 1)

        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as e:
            raise ValueError(f"Module not found: {module_path}") from e

        if not hasattr(module, attr_name):
            raise ValueError(
                f"Attribute '{attr_name}' not found in module {module_path}"
            )

        content = getattr(module, attr_name)
        if not isinstance(content, str):
            raise TypeError(f"Expected string, got {type(content).__name__} for {ref}")

        return ResolvedPrompt(
            content=content,
            source="py",
            ref=ref,
            version=None,
            hash=_hash_content(content),
        )


# Convenience function
def resolve_prompt(prompt: str) -> ResolvedPrompt:
    """Resolve prompt from any source."""
    return PromptResolver.resolve(prompt)

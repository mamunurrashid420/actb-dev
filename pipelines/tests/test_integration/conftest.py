"""Shared fixtures for integration tests.

Note: Full integration tests that materialize assets with mocks are complex
due to Dagster's resource system requirements. The smoke tests provide good
coverage for catching common bugs (deps vs ins, column names, etc.).

For future enhancements, consider using Dagster's testing utilities or
creating lightweight test assets that don't require external API mocking.
"""

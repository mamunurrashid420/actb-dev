from __future__ import annotations

from xlake.core import UserContext


def test_user_context_defaults() -> None:
    data = {
        "user_id": "u123",
        "tenant_id": "acme",
        "role": "viewer",
    }
    ctx = UserContext.model_validate(data)
    assert ctx.user_id == "u123"
    assert ctx.tenant_id == "acme"
    assert ctx.role == "viewer"
    assert ctx.permissions.can_run_queries is True
    assert ctx.permissions.can_modify_schema is False
    assert ctx.preferences.units == "EUR"
    assert ctx.preferences.verbosity == "concise"

"""Common error helpers for API services."""

from fastapi import HTTPException, status


def _coerce_status_code(value) -> int:
    """Return a safe HTTP status code from Supabase errors."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return status.HTTP_500_INTERNAL_SERVER_ERROR
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def raise_for_supabase_error(result, message: str) -> None:
    """Raise HTTP errors based on Supabase response."""
    error = getattr(result, "error", None)
    if not error:
        return
    status_code = _coerce_status_code(getattr(error, "status_code", None))
    raise HTTPException(
        status_code=status_code,
        detail=f"{message}: {error.message}",
    )

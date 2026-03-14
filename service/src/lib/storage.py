"""Storage helpers for tenant assets."""

from supabase import Client

from src.app.config import get_settings


class SupabaseStorageProvider:
    """Storage provider backed by Supabase Storage."""

    def __init__(self, supabase: Client, bucket: str) -> None:
        self._supabase = supabase
        self._bucket = bucket

    def upload(
        self, storage_path: str, content: bytes, content_type: str | None
    ) -> None:
        file_options = None
        if content_type:
            file_options = {"content-type": content_type}
        self._supabase.storage.from_(self._bucket).upload(
            storage_path, content, file_options
        )


def get_storage_provider(supabase: Client) -> SupabaseStorageProvider:
    """Return the configured storage provider."""
    settings = get_settings()
    if settings.storage_backend != "supabase":
        raise ValueError(
            f"Unsupported storage backend: {settings.storage_backend}"
        )
    return SupabaseStorageProvider(supabase, settings.storage_bucket)

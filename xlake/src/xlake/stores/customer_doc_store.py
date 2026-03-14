"""CustomerDocStore protocol and fsspec-backed implementations.

Implements Section 1.2.3 (CustomerDocStore) of the XLake architecture:
 - Stores raw documents in an object store (local fs in development)
 - Stores provenance metadata alongside each document as metadata.json
 - Layout per document: /{tenant_id}/{document_name}/file.<ext> and metadata.json
"""

from __future__ import annotations

import contextlib
import json
from typing import Any, BinaryIO, Protocol, runtime_checkable

import fsspec

from .config import (
    ConnectorsRegistryConfig,
    CustomerDocStoreConfig,
    FSSpecLocalDocConfig,
    FSSpecObjectDocConfig,
)


@runtime_checkable
class CustomerDocStore(Protocol):
    """Protocol for storing and retrieving customer documents and provenance metadata."""

    def save_document(
        self,
        tenant_id: str,
        document_name: str,
        extension: str,
        content: bytes | BinaryIO,
        metadata: dict[str, Any],
        overwrite: bool = False,
    ) -> str:  # pragma: no cover
        """Save a document and its metadata. Returns the URI to the document directory."""
        ...

    def get_document(
        self, tenant_id: str, document_name: str
    ) -> tuple[bytes, str]:  # pragma: no cover
        """Return (content_bytes, extension) for the stored file."""
        ...

    def get_metadata(
        self, tenant_id: str, document_name: str
    ) -> dict[str, Any]:  # pragma: no cover
        """Return the provenance metadata stored for a document."""
        ...

    def set_metadata(
        self,
        tenant_id: str,
        document_name: str,
        metadata: dict[str, Any],
        merge: bool = False,
    ) -> None:  # pragma: no cover
        """Replace or merge metadata for a document."""
        ...

    def list_documents(self, tenant_id: str) -> list[str]:  # pragma: no cover
        """List document names available for a tenant."""
        ...

    def delete_document(
        self, tenant_id: str, document_name: str
    ) -> None:  # pragma: no cover
        """Delete a document directory (file + metadata.json)."""
        ...

    def close(self) -> None:  # pragma: no cover
        """Release resources held by the store (connections, clients)."""
        ...


def _ensure_bytes(content: bytes | BinaryIO) -> bytes:
    if isinstance(content, (bytes, bytearray)):
        return bytes(content)
    # Assume file-like
    if hasattr(content, "read"):
        data = content.read()
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        # If text was provided, encode as utf-8
        if isinstance(data, str):
            return data.encode("utf-8")
    raise TypeError("content must be bytes or a binary file-like object")


def _normalize_extension(ext: str) -> str:
    # Accept inputs like "pdf", ".pdf", "file.pdf" and normalize to "pdf"
    if not ext:
        return ""
    # If ext includes path-like pieces, take last token after last slash
    token = ext.split("/")[-1].split("\\")[-1]
    # If contains a dot, take suffix after last dot
    if "." in token:
        token = token.split(".")[-1]
    return token.lower()


class _BaseFSSpecDocStore(CustomerDocStore):
    """Common fsspec helpers."""

    def __init__(self, base_uri: str) -> None:
        # base_uri examples: "file:///abs/path", "/abs/path", "gcs://bucket/prefix"
        self._base_uri = base_uri.rstrip("/")

    # Path helpers
    def _doc_dir(self, tenant_id: str, document_name: str) -> str:
        return f"{self._base_uri}/{tenant_id}/{document_name}"

    def _file_path(self, tenant_id: str, document_name: str, extension: str) -> str:
        norm_ext = _normalize_extension(extension)
        return f"{self._doc_dir(tenant_id, document_name)}/file.{norm_ext}"

    def _meta_path(self, tenant_id: str, document_name: str) -> str:
        return f"{self._doc_dir(tenant_id, document_name)}/metadata.json"

    def save_document(
        self,
        tenant_id: str,
        document_name: str,
        extension: str,
        content: bytes | BinaryIO,
        metadata: dict[str, Any],
        overwrite: bool = False,
    ) -> str:
        data = _ensure_bytes(content)
        file_path = self._file_path(tenant_id, document_name, extension)
        meta_path = self._meta_path(tenant_id, document_name)

        # Ensure directory exists (works for local; object stores ignore)
        # We attempt to create via fs.mkdirs when available.
        doc_dir = self._doc_dir(tenant_id, document_name)
        fs, dir_path = fsspec.core.url_to_fs(doc_dir)
        if hasattr(fs, "makedirs"):
            # Some object store implementations may not support makedirs
            with contextlib.suppress(Exception):
                fs.makedirs(dir_path, exist_ok=True)  # type: ignore[attr-defined]

        # Write file
        with fsspec.open(file_path, mode="wb", overwrite=overwrite) as f:
            f.write(data)

        # Write metadata (pretty to aid debugging)
        with fsspec.open(meta_path, mode="w", overwrite=True) as f:
            json.dump(metadata, f, indent=2, sort_keys=True)

        return doc_dir

    def get_document(self, tenant_id: str, document_name: str) -> tuple[bytes, str]:
        # Infer extension by listing
        doc_dir = self._doc_dir(tenant_id, document_name)
        listing = fsspec.open_files(f"{doc_dir}/file.*", mode="rb")
        if not listing:
            raise FileNotFoundError(f"No file for document '{document_name}'")
        # Pick the first match deterministically
        of = sorted(listing, key=lambda o: o.path)[0]
        # Extract extension
        path = of.path
        ext = path.split(".")[-1] if "." in path else ""
        with of as f:
            data = f.read()
        return data, ext

    def get_metadata(self, tenant_id: str, document_name: str) -> dict[str, Any]:
        meta_path = self._meta_path(tenant_id, document_name)
        with fsspec.open(meta_path, mode="r") as f:
            return json.load(f)

    def set_metadata(
        self,
        tenant_id: str,
        document_name: str,
        metadata: dict[str, Any],
        merge: bool = False,
    ) -> None:
        meta_path = self._meta_path(tenant_id, document_name)
        if merge:
            try:
                current = self.get_metadata(tenant_id, document_name)
            except FileNotFoundError:
                current = {}
            current.update(metadata)
            new_obj = current
        else:
            new_obj = metadata
        with fsspec.open(meta_path, mode="w", overwrite=True) as f:
            json.dump(new_obj, f, indent=2, sort_keys=True)

    def list_documents(self, tenant_id: str) -> list[str]:
        # List directories under tenant
        base_prefix = f"{self._base_uri}/{tenant_id}"
        fs, path = fsspec.core.url_to_fs(base_prefix)
        try:
            entries = fs.ls(path, detail=True)  # type: ignore[attr-defined]
        except FileNotFoundError:
            return []
        docs: list[str] = []
        for e in entries:
            # Detail format varies; try to infer directory vs file
            name = e["name"] if isinstance(e, dict) else str(e)
            if name.endswith("/metadata.json"):
                # skip metadata file if object store flattens ls
                continue
            # Strip prefix
            rel = name[len(path) :].lstrip("/")
            # Directory name is first segment
            doc_name = rel.split("/", 1)[0] if rel else ""
            if doc_name and doc_name not in docs:
                docs.append(doc_name)
        docs.sort()
        return docs

    def delete_document(self, tenant_id: str, document_name: str) -> None:
        doc_dir = self._doc_dir(tenant_id, document_name)
        fs, path = fsspec.core.url_to_fs(doc_dir)
        # Best-effort recursive delete
        try:
            if hasattr(fs, "rm"):
                fs.rm(path, recursive=True)  # type: ignore[attr-defined]
                return
        except FileNotFoundError:
            return
        # Fallback: remove known files
        try:
            for of in fsspec.open_files(f"{doc_dir}/*", mode="rb"):
                try:
                    fs2, p2 = fsspec.core.url_to_fs(of.path)
                    if hasattr(fs2, "rm"):
                        fs2.rm(p2, recursive=False)  # type: ignore[attr-defined]
                except Exception:
                    pass
        except Exception:
            pass

    def close(self) -> None:
        # fsspec uses context managers for each file operation;
        # no persistent connections to clean up.
        pass


class FSSpecLocalCustomerDocStore(_BaseFSSpecDocStore):
    """Local filesystem-backed CustomerDocStore using fsspec."""

    def __init__(self, config: FSSpecLocalDocConfig) -> None:
        # Normalize to file:// URI so url_to_fs handles it properly
        base = config.base_dir
        if "://" not in base:
            base = f"file://{base}"
        super().__init__(base)


class ConnectorsCustomerDocStore(_BaseFSSpecDocStore):
    """Connectors-backed Document Store (staging/production).

    Uses fsspec to write to cloud object storage (e.g., GCS via gcsfs).
    The base URI should be resolved via the connectors registry; until implemented,
    we accept an explicit `base_uri` and raise otherwise.
    """

    def __init__(
        self,
        registry: ConnectorsRegistryConfig | None,
        object_cfg: FSSpecObjectDocConfig | None,
    ) -> None:
        base_uri = (object_cfg.base_uri if object_cfg else "").rstrip("/")
        if not base_uri:
            raise NotImplementedError(
                "ConnectorsCustomerDocStore requires XLAKE_CUSTOMER_DOC_OBJECT_BASE_URI "
                "to be set until registry resolution is implemented."
            )
        super().__init__(base_uri)
        self._registry = registry


def create_customer_doc_store(config: CustomerDocStoreConfig) -> CustomerDocStore:
    """Create a CustomerDocStore instance based on the provided configuration."""
    if config.backend == "fsspec_local":
        assert config.fsspec_local is not None, "fsspec_local config must be provided"
        return FSSpecLocalCustomerDocStore(config.fsspec_local)
    if config.backend == "connectors":
        # Registry may be None for now; runtime resolution to be implemented later.
        return ConnectorsCustomerDocStore(
            registry=config.connectors_registry,
            object_cfg=config.fsspec_object,
        )
    raise ValueError(f"Unsupported backend: {config.backend}")

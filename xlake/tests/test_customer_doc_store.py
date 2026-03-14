from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from xlake.stores.config import (
    ConnectorsRegistryConfig,
    CustomerDocStoreConfig,
    FSSpecLocalDocConfig,
    FSSpecObjectDocConfig,
)
from xlake.stores.customer_doc_store import create_customer_doc_store


def test_local_doc_store_save_get_list_delete(tmp_path: Path) -> None:
    base_dir = tmp_path / "docs"
    cfg = CustomerDocStoreConfig(
        backend="fsspec_local",
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(base_dir)),
    )
    store = create_customer_doc_store(cfg)

    tenant = "tenant-a"
    doc = "policy-doc"
    ext = "txt"
    content = b"hello world"
    metadata = {
        "author": "alice",
        "title": "Policy",
        "page_count": 1,
        "tags": ["example"],
    }

    # Save
    uri = store.save_document(tenant, doc, ext, content, metadata, overwrite=True)
    assert uri.endswith(f"/{tenant}/{doc}")

    # Get file
    data, returned_ext = store.get_document(tenant, doc)
    assert data == content
    assert returned_ext == ext

    # Get metadata
    meta = store.get_metadata(tenant, doc)
    assert meta["author"] == "alice"
    assert meta["title"] == "Policy"
    assert meta["page_count"] == 1
    assert meta["tags"] == ["example"]

    # Merge metadata
    store.set_metadata(
        tenant, doc, {"version": 2, "tags": ["example", "merged"]}, merge=True
    )
    meta2 = store.get_metadata(tenant, doc)
    assert meta2["version"] == 2
    assert meta2["tags"] == ["example", "merged"]

    # List
    docs = store.list_documents(tenant)
    assert doc in docs

    # Delete
    store.delete_document(tenant, doc)
    with pytest.raises(FileNotFoundError):
        _ = store.get_metadata(tenant, doc)


def test_connectors_doc_store_requires_base_uri() -> None:
    # Until connectors registry resolution is implemented, require explicit base_uri
    cfg = CustomerDocStoreConfig(
        backend="connectors",
        connectors_registry=ConnectorsRegistryConfig(
            uri=SecretStr("postgres://registry")
        ),
        fsspec_object=FSSpecObjectDocConfig(base_uri=""),
    )
    with pytest.raises(NotImplementedError):
        _ = create_customer_doc_store(cfg)


def test_local_doc_store_directory_includes_extension(tmp_path: Path) -> None:
    base_dir = tmp_path / "docs2"
    cfg = CustomerDocStoreConfig(
        backend="fsspec_local",
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(base_dir)),
    )
    store = create_customer_doc_store(cfg)

    tenant = "tenant-b"
    doc = "financial_fda.pdf"  # directory should include the extension in its name
    ext = "pdf"
    content = b"%PDF-1.7..."
    metadata = {"author": "bob", "title": "FDA Form"}

    uri = store.save_document(tenant, doc, ext, content, metadata, overwrite=True)
    assert uri.endswith(f"/{tenant}/{doc}")

    # Ensure listing includes the directory named with extension
    docs = store.list_documents(tenant)
    assert doc in docs

    # Validate we can read back and the extension resolution works
    data, returned_ext = store.get_document(tenant, doc)
    assert data.startswith(b"%PDF")
    assert returned_ext == "pdf"


def test_local_doc_store_close(tmp_path: Path) -> None:
    """Verify close() method exists and can be called without error."""
    base_dir = tmp_path / "docs_close"
    cfg = CustomerDocStoreConfig(
        backend="fsspec_local",
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(base_dir)),
    )
    store = create_customer_doc_store(cfg)

    # Save a document
    store.save_document(
        "tenant", "doc", "txt", b"content", {"key": "value"}, overwrite=True
    )

    # close() should be callable and not raise
    store.close()

    # Store should still work after close (no persistent connection)
    data, _ = store.get_document("tenant", "doc")
    assert data == b"content"

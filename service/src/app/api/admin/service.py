from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.app.config import get_settings
from src.lib.api.errors import raise_for_supabase_error
from src.lib.db.connection_test import test_connection
from src.lib.security.encryption import decrypt_payload, encrypt_payload
from src.lib.supabase.client import get_supabase_admin_client

from .schema import (
    CreateConnectionRequest,
    CreateTenantRequest,
    CreateUserRequest,
    InviteUserRequest,
    ResendInviteRequest,
    TestConnectionRequest,
    UpdateConnectionRequest,
    UpdateTenantRequest,
    UpdateUserRequest,
)


class AdminService:
    def __init__(self, supabase: Client = Depends(get_supabase_admin_client)):
        self.supabase = supabase
        self.settings = get_settings()

    def _get_bi_redirect_url(self) -> str:
        bi_url = None
        if len(self.settings.cors_origins) > 1:
            bi_url = self.settings.cors_origins[1]
        elif len(self.settings.cors_origins) > 0:
            bi_url = self.settings.cors_origins[0]
        bi_url = bi_url or "http://localhost:3002"
        return f"{bi_url}/auth/accept-invite"

    def _storage_bucket(self) -> str:
        return self.settings.storage_bucket

    # ─────────────────────────────────────────────────────────────────
    # Tenants
    # ─────────────────────────────────────────────────────────────────
    async def list_tenants(
        self, page: int, limit: int, search: str | None, status_value: str | None
    ) -> dict:
        query = (
            self.supabase.table("tenants")
            .select(
                "*, tenant_users(user_id, role, status), tenant_database_connections(id)",
                count="exact",
            )
            .order("created_at", desc=True)
        )

        if search:
            query = query.or_(f"name.ilike.%{search}%,description.ilike.%{search}%")
        if status_value:
            query = query.eq("status", status_value)

        offset = (page - 1) * limit
        result = query.range(offset, offset + limit - 1).execute()
        raise_for_supabase_error(result, "Failed to fetch tenants")

        tenants = []
        for tenant in result.data or []:
            members = tenant.get("tenant_users") or []
            connections = tenant.get("tenant_database_connections") or []
            admins = [
                member
                for member in members
                if member.get("role") in ("admin", "superadmin")
            ]
            tenants.append(
                {
                    "id": tenant.get("id"),
                    "name": tenant.get("name"),
                    "description": tenant.get("description"),
                    "status": tenant.get("status"),
                    "branding": tenant.get("branding"),
                    "context_metadata": tenant.get("context_metadata"),
                    "logo_url": tenant.get("logo_url"),
                    "document_name": tenant.get("document_name"),
                    "created_at": tenant.get("created_at"),
                    "updated_at": tenant.get("updated_at"),
                    "member_count": len(members),
                    "connection_count": len(connections),
                    "admins": admins,
                }
            )

        total = result.count or 0
        return {
            "tenants": tenants,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit if limit else 0,
            },
        }

    async def create_tenant(self, data: CreateTenantRequest) -> dict:
        payload = {
            "name": data.name.strip(),
            "description": data.description.strip() if data.description else None,
            "status": data.status or "active",
            "branding": data.branding or {},
        }
        result = self.supabase.table("tenants").insert(payload).execute()
        raise_for_supabase_error(result, "Failed to create tenant")
        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create tenant")
        return result.data[0]

    async def update_tenant(self, tenant_id: str, data: UpdateTenantRequest) -> dict:
        update_data: dict[str, Any] = {}
        if data.name is not None:
            update_data["name"] = data.name.strip()
        if data.description is not None:
            update_data["description"] = data.description.strip() or None
        if data.status is not None:
            update_data["status"] = data.status
        if data.branding is not None:
            update_data["branding"] = data.branding
        if data.context_metadata is not None:
            update_data["context_metadata"] = data.context_metadata
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = (
            self.supabase.table("tenants")
            .update(update_data)
            .eq("id", tenant_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to update tenant")
        if not result.data:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return result.data[0]

    async def update_tenant_status(self, tenant_id: str, status_value: str) -> dict:
        result = (
            self.supabase.table("tenants")
            .update(
                {
                    "status": status_value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", tenant_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to update tenant status")
        if not result.data:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return result.data[0]

    async def delete_tenant(self, tenant_id: str) -> None:
        active_members = (
            self.supabase.table("tenant_users")
            .select("user_id")
            .eq("tenant_id", tenant_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        raise_for_supabase_error(active_members, "Failed to validate tenant deletion")
        if active_members.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete tenant with active members.",
            )
        result = (
            self.supabase.table("tenants").delete().eq("id", tenant_id).execute()
        )
        raise_for_supabase_error(result, "Failed to delete tenant")

    def _enrich_assets(self, assets: list[dict], include_content: bool) -> list[dict]:
        bucket = self.supabase.storage.from_(self._storage_bucket())
        ttl = self.settings.storage_signed_url_ttl_seconds
        enriched: list[dict] = []
        for asset in assets or []:
            storage_path = asset.get("storage_path")
            signed_url = None
            if storage_path:
                try:
                    signed = bucket.create_signed_url(storage_path, ttl)
                    if isinstance(signed, dict):
                        signed_url = signed.get("signedUrl") or signed.get("signed_url")
                except Exception:
                    signed_url = None
            content = None
            if include_content and asset.get("asset_type") == "markdown" and storage_path:
                try:
                    download = bucket.download(storage_path)
                    if download and isinstance(download, bytes):
                        content = download.decode("utf-8", errors="ignore")
                except Exception:
                    content = None
            enriched.append({**asset, "signed_url": signed_url, "content": content})
        return enriched

    async def get_tenant(self, tenant_id: str, include_assets_content: bool = False) -> dict:
        result = (
            self.supabase.table("tenants")
            .select(
                "*, tenant_users(user_id, role, status, invited_at, accepted_at), "
                "tenant_assets(id, asset_type, storage_path, file_name, file_size, content_type, created_at), "
                "tenant_database_connections(id, name, type, is_active, last_test_status, last_tested_at, created_at)"
            )
            .eq("id", tenant_id)
            .maybe_single()
            .execute()
        )
        raise_for_supabase_error(result, "Failed to fetch tenant")
        if not result.data:
            raise HTTPException(status_code=404, detail="Tenant not found")
        tenant = result.data
        members = tenant.get("tenant_users") or []
        connections = tenant.get("tenant_database_connections") or []
        tenant["member_count"] = len(members)
        tenant["active_members"] = len([m for m in members if m.get("status") == "active"])
        tenant["admins"] = [
            m for m in members if m.get("role") in ("admin", "superadmin")
        ]
        # Enrich members with profile details for UI
        tenant["members"] = await self.list_members(tenant_id)
        tenant["assets"] = self._enrich_assets(
            tenant.get("tenant_assets") or [], include_assets_content
        )
        tenant["connections"] = connections
        return tenant

    # ─────────────────────────────────────────────────────────────────
    # Tenant assets
    # ─────────────────────────────────────────────────────────────────
    async def list_assets(self, tenant_id: str, include_content: bool) -> list[dict]:
        result = (
            self.supabase.table("tenant_assets")
            .select(
                "id, asset_type, storage_path, file_name, file_size, content_type, created_at"
            )
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to load tenant assets")
        bucket = self.supabase.storage.from_(self._storage_bucket())
        ttl = self.settings.storage_signed_url_ttl_seconds
        enriched = []
        for asset in result.data or []:
            signed = bucket.create_signed_url(asset["storage_path"], ttl)
            signed_url = None
            if isinstance(signed, dict):
                signed_url = signed.get("signedUrl") or signed.get("signed_url")
            content = None
            if include_content and asset.get("asset_type") == "markdown":
                download = bucket.download(asset["storage_path"])
                if download and isinstance(download, bytes):
                    content = download.decode("utf-8", errors="ignore")
            enriched.append({**asset, "signed_url": signed_url, "content": content})
        return enriched

    async def upload_asset(
        self,
        tenant_id: str,
        asset_type: str,
        file_name: str,
        content: bytes,
        content_type: str | None,
    ) -> dict:
        storage_path = (
            f"tenants/{tenant_id}/logo"
            if asset_type == "logo"
            else f"tenants/{tenant_id}/knowledge.md"
        )
        bucket = self.supabase.storage.from_(self._storage_bucket())
        # storage3 expects header values as strings
        file_options = {"upsert": "true"}
        if content_type:
            file_options["content-type"] = content_type
        bucket.upload(storage_path, content, file_options)

        result = (
            self.supabase.table("tenant_assets")
            .upsert(
                {
                    "tenant_id": tenant_id,
                    "asset_type": asset_type,
                    "storage_path": storage_path,
                    "file_name": file_name,
                    "file_size": len(content),
                    "content_type": content_type,
                },
                on_conflict="tenant_id,asset_type",
            )
            .execute()
        )
        raise_for_supabase_error(result, "Failed to save asset metadata")
        return result.data[0]

    # ─────────────────────────────────────────────────────────────────
    # Tenant members
    # ─────────────────────────────────────────────────────────────────
    async def list_members(self, tenant_id: str) -> list[dict]:
        members = (
            self.supabase.table("tenant_users")
            .select("user_id, role, status, invited_at, accepted_at")
            .eq("tenant_id", tenant_id)
            .order("role")
            .execute()
        )
        raise_for_supabase_error(members, "Failed to load members")
        user_ids = [m["user_id"] for m in members.data or []]
        profiles = []
        if user_ids:
            profiles_result = (
                self.supabase.table("user_profiles")
                .select("id, email, full_name")
                .in_("id", user_ids)
                .execute()
            )
            raise_for_supabase_error(profiles_result, "Failed to load user profiles")
            profiles = profiles_result.data or []
        profile_map = {p["id"]: p for p in profiles}
        transformed = []
        for member in members.data or []:
            profile = profile_map.get(member["user_id"])
            transformed.append(
                {
                    "user_id": member["user_id"],
                    "role": member.get("role"),
                    "status": member.get("status"),
                    "invited_at": member.get("invited_at"),
                    "accepted_at": member.get("accepted_at"),
                    "user": {
                        "email": profile.get("email"),
                        "full_name": profile.get("full_name"),
                    }
                    if profile
                    else None,
                }
            )
        return transformed

    # ─────────────────────────────────────────────────────────────────
    # Connections
    # ─────────────────────────────────────────────────────────────────
    def _serialize_config(self, config: dict) -> dict:
        metadata = {k: v for k, v in config.items() if k != "password"}
        encrypted = encrypt_payload(config)
        return {"encrypted": True, "ciphertext": encrypted, "metadata": metadata}

    def _decrypt_config(self, stored: dict) -> dict:
        if stored.get("encrypted"):
            return decrypt_payload(stored.get("ciphertext", ""))
        return stored

    async def list_connections(self, tenant_id: str) -> list[dict]:
        result = (
            self.supabase.table("tenant_database_connections")
            .select("id, name, type, is_active, last_test_status, last_tested_at, created_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to load tenant connections")
        return result.data or []

    async def test_connection_config(self, payload: TestConnectionRequest) -> None:
        test_connection(payload.type, payload.connection_config)

    async def create_connection(self, payload: CreateConnectionRequest) -> dict:
        existing = (
            self.supabase.table("tenant_database_connections")
            .select("id")
            .eq("tenant_id", payload.tenant_id)
            .eq("name", payload.name.strip())
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connection name already exists for this tenant",
            )

        test_connection(payload.type, payload.connection_config)
        encrypted = self._serialize_config(payload.connection_config)
        now = datetime.now(timezone.utc).isoformat()
        result = (
            self.supabase.table("tenant_database_connections")
            .insert(
                {
                    "tenant_id": payload.tenant_id,
                    "name": payload.name.strip(),
                    "type": payload.type,
                    "connection_config": encrypted,
                    "is_active": True,
                    "last_test_status": "success",
                    "last_tested_at": now,
                    "updated_at": now,
                }
            )
            .execute()
        )
        raise_for_supabase_error(result, "Failed to create connection")
        connection = result.data[0]
        connection.pop("connection_config", None)
        return connection

    async def update_connection(self, connection_id: str, payload: UpdateConnectionRequest) -> dict:
        existing = (
            self.supabase.table("tenant_database_connections")
            .select("id, tenant_id, name, type, is_active, last_test_status, last_tested_at")
            .eq("id", connection_id)
            .maybe_single()
            .execute()
        )
        raise_for_supabase_error(existing, "Connection not found")
        if not existing.data:
            raise HTTPException(status_code=404, detail="Connection not found")

        existing_row = existing.data
        updates: dict[str, Any] = {}
        now = datetime.now(timezone.utc).isoformat()

        if payload.name:
            trimmed = payload.name.strip()
            if trimmed != existing_row.get("name"):
                conflict = (
                    self.supabase.table("tenant_database_connections")
                    .select("id")
                    .eq("tenant_id", existing_row.get("tenant_id"))
                    .eq("name", trimmed)
                    .maybe_single()
                    .execute()
                )
                if conflict.data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Connection name already exists for this tenant",
                    )
            updates["name"] = trimmed

        if payload.is_active is not None:
            if payload.is_active and payload.connection_config is None:
                if existing_row.get("last_test_status") != "success":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Connection must be successfully tested before activation.",
                    )
            updates["is_active"] = payload.is_active

        if payload.connection_config is not None:
            test_connection(existing_row.get("type"), payload.connection_config)
            updates["connection_config"] = self._serialize_config(payload.connection_config)
            updates["last_test_status"] = "success"
            updates["last_tested_at"] = now

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        updates["updated_at"] = now

        result = (
            self.supabase.table("tenant_database_connections")
            .update(updates)
            .eq("id", connection_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to update connection")
        updated = result.data[0]
        updated.pop("connection_config", None)
        return updated

    async def delete_connection(self, connection_id: str) -> None:
        result = (
            self.supabase.table("tenant_database_connections")
            .delete()
            .eq("id", connection_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to delete connection")

    async def test_existing_connection(self, connection_id: str) -> None:
        result = (
            self.supabase.table("tenant_database_connections")
            .select("id, type, connection_config")
            .eq("id", connection_id)
            .maybe_single()
            .execute()
        )
        raise_for_supabase_error(result, "Connection not found")
        if not result.data:
            raise HTTPException(status_code=404, detail="Connection not found")
        config = self._decrypt_config(result.data.get("connection_config") or {})
        try:
            test_connection(result.data["type"], config)
        except Exception as exc:
            self.supabase.table("tenant_database_connections").update(
                {
                    "last_test_status": "error",
                    "last_tested_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", connection_id).execute()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        self.supabase.table("tenant_database_connections").update(
            {
                "last_test_status": "success",
                "last_tested_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", connection_id).execute()

    # ─────────────────────────────────────────────────────────────────
    # Users & invites
    # ─────────────────────────────────────────────────────────────────
    async def list_users(self) -> dict:
        users_result = (
            self.supabase.table("user_profiles")
            .select("id,email,full_name,avatar_url,is_app_admin,created_at")
            .order("created_at", desc=True)
            .execute()
        )
        raise_for_supabase_error(users_result, "Failed to load users")

        tenants_result = (
            self.supabase.table("tenants").select("id,name").order("name").execute()
        )
        raise_for_supabase_error(tenants_result, "Failed to load tenants")

        user_ids = [u["id"] for u in users_result.data or []]
        memberships: dict[str, dict[str, Any]] = {}
        if user_ids:
            membership_rows = (
                self.supabase.table("tenant_users")
                .select("user_id,status,tenant_id,role,accepted_at,invited_at")
                .in_("user_id", user_ids)
                .order("accepted_at", desc=True, nullsfirst=False)
                .execute()
            )
            raise_for_supabase_error(membership_rows, "Failed to load memberships")
            for row in membership_rows.data or []:
                if row["user_id"] not in memberships:
                    memberships[row["user_id"]] = {
                        "status": row.get("status"),
                        "tenant_id": row.get("tenant_id"),
                        "role": row.get("role"),
                        "invited_at": row.get("invited_at"),
                        "accepted_at": row.get("accepted_at"),
                    }

        users = []
        for user in users_result.data or []:
            membership = memberships.get(user["id"]) or {}
            users.append(
                {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "full_name": user.get("full_name"),
                    "avatar_url": user.get("avatar_url"),
                    "is_app_admin": user.get("is_app_admin"),
                    "status": membership.get("status"),
                    "tenant_id": membership.get("tenant_id"),
                    "role": membership.get("role"),
                    "invited_at": membership.get("invited_at"),
                    "accepted_at": membership.get("accepted_at"),
                }
            )

        return {"users": users, "tenants": tenants_result.data or []}

    async def invite_user(self, data: InviteUserRequest) -> dict:
        redirect_to = self._get_bi_redirect_url()
        res = self.supabase.auth.admin.invite_user_by_email(
            data.email, options={"redirectTo": redirect_to}
        )
        user = res.user
        if not user:
            raise HTTPException(status_code=400, detail="Invite failed")

        tenant_id = data.tenant_id
        if tenant_id:
            role = data.role or "viewer"
            self.supabase.table("tenant_users").upsert(
                {
                    "tenant_id": tenant_id,
                    "user_id": user.id,
                    "role": role,
                    "status": "inactive",
                    "invited_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="tenant_id,user_id",
            ).execute()

        return {
            "userId": user.id,
            "email": user.email,
            "fullName": user.user_metadata.get("full_name") if user.user_metadata else "",
            "tenantId": tenant_id,
            "status": "inactive",
        }

    async def create_user(self, data: CreateUserRequest) -> dict:
        create_res = self.supabase.auth.admin.create_user(
            {
                "email": data.email,
                "password": data.password,
                "email_confirm": True,
                "user_metadata": {"full_name": data.full_name or data.email.split("@")[0]},
            }
        )
        if not create_res.user:
            raise HTTPException(status_code=400, detail="Failed to create user")
        user = create_res.user
        now = datetime.now(timezone.utc).isoformat()

        self.supabase.table("user_profiles").upsert(
            {
                "id": user.id,
                "email": data.email,
                "full_name": data.full_name or user.user_metadata.get("full_name"),
                "updated_at": now,
            },
            on_conflict="id",
        ).execute()

        tenant_id = data.tenant_id
        if tenant_id:
            role = data.role or "viewer"
            self.supabase.table("tenant_users").upsert(
                {
                    "tenant_id": tenant_id,
                    "user_id": user.id,
                    "role": role,
                    "status": "active",
                    "invited_at": now,
                    "accepted_at": now,
                    "created_at": now,
                },
                on_conflict="tenant_id,user_id",
            ).execute()

        return {
            "userId": user.id,
            "email": data.email,
            "fullName": data.full_name or data.email,
            "tenantId": tenant_id,
            "status": "active",
        }

    async def resend_invite(self, data: ResendInviteRequest) -> dict:
        profile = (
            self.supabase.table("user_profiles")
            .select("id,email")
            .ilike("email", data.email)
            .maybe_single()
            .execute()
        )
        if not profile.data:
            raise HTTPException(status_code=404, detail="User not found")

        membership_query = (
            self.supabase.table("tenant_users")
            .select("tenant_id,status")
            .eq("user_id", profile.data["id"])
            .order("invited_at", desc=True)
            .limit(1)
        )
        if data.tenant_id:
            membership_query = membership_query.eq("tenant_id", data.tenant_id)
        membership = membership_query.maybe_single().execute()
        if not membership.data:
            raise HTTPException(status_code=404, detail="No invite found for this user")
        if membership.data.get("status") == "active":
            raise HTTPException(status_code=400, detail="User already accepted the invite")

        redirect_to = self._get_bi_redirect_url()
        self.supabase.auth.reset_password_for_email(
            profile.data["email"], {"redirectTo": redirect_to}
        )

        self.supabase.table("tenant_users").update(
            {"invited_at": datetime.now(timezone.utc).isoformat()}
        ).eq("user_id", profile.data["id"]).eq(
            "tenant_id", membership.data["tenant_id"]
        ).execute()

        return {"success": True}

    async def update_user(self, user_id: str, data: UpdateUserRequest) -> dict:
        updates: dict[str, Any] = {}
        if data.full_name is not None:
            updates["full_name"] = data.full_name.strip() or None
        if updates:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.supabase.table("user_profiles").update(updates).eq("id", user_id).execute()

        if data.tenant_id:
            existing = (
                self.supabase.table("tenant_users")
                .select("role,status")
                .eq("tenant_id", data.tenant_id)
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            existing_role = existing.data.get("role") if existing.data else None
            existing_status = existing.data.get("status") if existing.data else "active"
            role = data.role or existing_role or "viewer"
            self.supabase.table("tenant_users").upsert(
                {
                    "tenant_id": data.tenant_id,
                    "user_id": user_id,
                    "role": role,
                    "status": existing_status,
                },
                on_conflict="tenant_id,user_id",
            ).execute()
        elif data.role is not None:
            raise HTTPException(status_code=400, detail="tenant_id is required to set role")

        return {"success": True}

    async def delete_user(self, user_id: str) -> None:
        self.supabase.table("tenant_users").delete().eq("user_id", user_id).execute()
        self.supabase.table("conversations").delete().eq("user_id", user_id).execute()
        self.supabase.table("user_profiles").delete().eq("id", user_id).execute()
        self.supabase.auth.admin.delete_user(user_id)

"""App role to permission mapping for UI gating."""

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "superadmin": [
        "tenant_settings.read",
        "tenant_settings.manage",
        "tenant_members.read",
        "tenant_members.manage",
        "conversations.create",
        "conversations.manage_all",
        "dashboards.create",
        "dashboards.manage_all",
        "reports.create",
        "reports.manage_all",
    ],
    "admin": [
        "tenant_members.read",
        "tenant_members.manage",
    ],
    "creator": [
        "conversations.create",
        "dashboards.create",
        "reports.create",
    ],
    "viewer": [],
}

import { AbilityBuilder, createMongoAbility, type MongoAbility } from "@casl/ability";

type Actions =
  | "manage"
  | "read"
  | "create"
  | "update"
  | "delete"
  | "admin"
  | "analytics"
  | "manage_roles";

type Subjects = string; // we map resources directly to string subjects

export type AppAbility = MongoAbility<[Actions, Subjects]>;

const ACTION_MAP: Record<string, Actions> = {
  read: "read",
  create: "create",
  update: "update",
  delete: "delete",
  admin: "admin",
  analytics: "analytics",
  manage_roles: "manage_roles",
};

export function buildAbility(
  permissionNames: string[],
  options?: { isAdmin?: boolean },
): AppAbility {
  const { can, build } = new AbilityBuilder<AppAbility>(createMongoAbility);

  if (options?.isAdmin) {
    can("manage", "all");
  }

  permissionNames.forEach((permission) => {
    const [resource, rawAction] = permission.split(".");
    const action = ACTION_MAP[rawAction] ?? "read";
    const subject = resource ?? "all";

    can(action, subject);

    // grant manage for admin/manage_roles style permissions for convenience
    if (action === "admin" || action === "manage_roles") {
      can("manage", subject);
    }
  });

  return build({
    detectSubjectType: (subject) => subject as Subjects,
  });
}

export function hasPermission(permissionNames: string[], target: string): boolean {
  return permissionNames.includes(target);
}

import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const USERS = [
  { name: "Ashley Brown", email: "ashley@example.com", role: "super-admin" },
  { name: "Dave Alvarez", email: "dave@example.com", role: "admin" },
  { name: "Matias Ignacio", email: "matias@example.com", role: "viewer", status: "Inactive" },
  { name: "John Doe", email: "sunil@example.com", role: "viewer", status: "Pending" },
];

export default function UsersSettingsPage() {
  return (
    <div className="bg-background min-h-screen px-6 py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-foreground text-2xl font-semibold">Users</h1>
          <p className="text-muted-foreground text-sm">Manage users and their access to your organization</p>
        </div>
        <Button size="sm" className="gap-2">
          <Plus className="size-4" />
          Add users
        </Button>
      </div>

      <div className="mt-8 flex justify-center">
        <div className="w-full max-w-3xl">
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Active users</CardTitle>
              <p className="text-muted-foreground text-sm">3 users have access to this organization</p>
            </CardHeader>
            <CardContent className="space-y-4">
              {USERS.map((user) => (
                <div
                  key={user.email}
                  className="flex flex-wrap items-center justify-between gap-4 border-b pb-4 last:border-b-0 last:pb-0"
                >
                  <div className="flex items-center gap-3">
                    <div className="bg-muted flex size-9 items-center justify-center rounded-full text-xs font-semibold">
                      {user.name
                        .split(" ")
                        .map((part) => part[0])
                        .join("")
                        .slice(0, 2)}
                    </div>
                    <div>
                      <p className="text-foreground text-sm font-semibold">{user.name}</p>
                      <p className="text-muted-foreground text-xs">{user.email}</p>
                    </div>
                    {user.status ? (
                      <span className="bg-muted text-muted-foreground rounded-full px-2 py-0.5 text-xs">
                        {user.status}
                      </span>
                    ) : null}
                  </div>
                  <Select defaultValue={user.role}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="super-admin">Super admin</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                      <SelectItem value="viewer">Viewer</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

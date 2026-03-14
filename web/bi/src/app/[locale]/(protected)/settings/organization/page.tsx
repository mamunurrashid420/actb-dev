import { Camera } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function OrganizationSettingsPage() {
  return (
    <div className="bg-background min-h-screen px-6 py-8">
      <div className="space-y-2">
        <h1 className="text-foreground text-2xl font-semibold">Organization Settings</h1>
        <p className="text-muted-foreground text-sm">Manage your organization profile and information</p>
      </div>

      <div className="mt-8 flex justify-center">
        <div className="w-full max-w-3xl">
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Organization profile</CardTitle>
              <p className="text-muted-foreground text-sm">Update your organization details and logo</p>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <Label>Company logo</Label>
                <div className="flex flex-wrap items-center gap-4">
                  <div className="bg-muted flex size-20 items-center justify-center rounded-full" />
                  <div className="space-y-1">
                    <Button variant="outline" size="sm" className="gap-2">
                      <Camera className="size-4" />
                      Change logo
                    </Button>
                    <p className="text-muted-foreground text-xs">Recommended: Square image, at least 256x256 pixels</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="org-name">Organization name</Label>
                <Input id="org-name" placeholder="Flat White LTD" defaultValue="Flat White LTD" />
                <p className="text-muted-foreground text-xs">
                  This name will be visible to all users in your organization
                </p>
              </div>

              <Button className="w-fit">Save changes</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

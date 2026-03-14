import { Camera } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function AccountSettingsPage() {
  return (
    <div className="bg-background min-h-screen px-6 py-8">
      <div className="space-y-2">
        <h1 className="text-foreground text-2xl font-semibold">Account Settings</h1>
        <p className="text-muted-foreground text-sm">Manage your personal information and account preferences</p>
      </div>

      <div className="mt-8 flex justify-center">
        <div className="w-full max-w-3xl">
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Profile information</CardTitle>
              <p className="text-muted-foreground text-sm">Update your personal details and photo</p>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex flex-wrap items-center gap-4">
                <div className="bg-muted flex size-20 items-center justify-center rounded-full" />
                <div className="space-y-1">
                  <Button variant="outline" size="sm" className="gap-2">
                    <Camera className="size-4" />
                    Change photo
                  </Button>
                  <p className="text-muted-foreground text-xs">Recommended: Square image, at least 256x256 pixels</p>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="first-name">First name</Label>
                  <Input id="first-name" placeholder="John" defaultValue="John" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="last-name">Last name</Label>
                  <Input id="last-name" placeholder="Doe" defaultValue="Doe" />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" placeholder="johndoe@example.com" defaultValue="johndoe@example.com" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Phone number</Label>
                <Input id="phone" placeholder="906 123 5678" defaultValue="906 123 5678" />
              </div>

              <Button className="w-fit">Save changes</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

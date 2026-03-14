"use client";

import { useState, useTransition } from "react";
import { useParams, useRouter } from "next/navigation";
import { Building2, CheckCircle2, Mail, User } from "lucide-react";
import { toast } from "sonner";

import { completeOnboarding } from "./actions";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type Props = {
  tenantId: string | null;
  defaultValues: {
    firstName: string;
    lastName: string;
    companyEmail: string;
    organization: string;
    description: string;
  };
};

export function OnboardingForm({ tenantId, defaultValues }: Props) {
  const router = useRouter();
  const params = useParams();
  const locale = typeof params?.locale === "string" ? params.locale : "en";
  const [form, setForm] = useState(defaultValues);
  const [pending, startTransition] = useTransition();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    startTransition(async () => {
      const result = await completeOnboarding({
        ...form,
        tenantId: tenantId ?? undefined,
      });
      if (result.error) {
        toast.error("Could not finish onboarding", { description: result.error });
        return;
      }
      toast.success("Welcome! Profile saved.");
      router.push(`/${locale}/dashboard`);
    });
  };

  return (
    <div className="bg-muted/20 min-h-screen py-10">
      <div className="mx-auto w-full max-w-2xl px-4">
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <CheckCircle2 className="text-primary h-6 w-6" />
              Finish setting up your account
            </CardTitle>
            <CardDescription>
              Confirm your details so we can set up your workspace and AI context.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={handleSubmit}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="firstName" className="flex items-center gap-2">
                    <User className="text-muted-foreground h-4 w-4" />
                    First name
                  </Label>
                  <Input
                    id="firstName"
                    required
                    value={form.firstName}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, firstName: e.target.value }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last name</Label>
                  <Input
                    id="lastName"
                    required
                    value={form.lastName}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, lastName: e.target.value }))
                    }
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="companyEmail" className="flex items-center gap-2">
                  <Mail className="text-muted-foreground h-4 w-4" />
                  Company email
                </Label>
                <Input
                  id="companyEmail"
                  type="email"
                  required
                  value={form.companyEmail}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, companyEmail: e.target.value }))
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="organization" className="flex items-center gap-2">
                  <Building2 className="text-muted-foreground h-4 w-4" />
                  Organization
                </Label>
                <Input
                  id="organization"
                  required
                  value={form.organization}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, organization: e.target.value }))
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Context for the AI agent (optional)</Label>
                <Textarea
                  id="description"
                  placeholder="What do you want to achieve with Actbi?"
                  value={form.description}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, description: e.target.value }))
                  }
                />
              </div>

              <div className="flex justify-end">
                <Button type="submit" disabled={pending} className="min-w-[160px]">
                  {pending ? "Saving..." : "Save and continue"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

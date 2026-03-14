"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SignupStepProps {
  onContinue: (values: { name: string; email: string }) => void;
  defaultValues?: {
    name?: string;
    email?: string;
  };
}

export function SignupStep({ onContinue, defaultValues }: SignupStepProps) {
  const [name, setName] = useState(defaultValues?.name ?? "");
  const [email, setEmail] = useState(defaultValues?.email ?? "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !name) return;
    onContinue({ name, email });
  };

  return (
    <div className="flex w-full flex-col items-center justify-center">
      <div className="bg-card w-full max-w-[580px] rounded-xl border p-7 shadow-sm">
        <div className="mb-6 w-full">
          <div className="bg-muted relative h-2 w-36 overflow-hidden rounded-full">
            <div className="bg-primary absolute left-0 top-0 h-full w-1/5 rounded-full" />
          </div>
        </div>

        <div className="mb-6 space-y-2">
          <h2 className="text-card-foreground text-2xl font-semibold leading-snug">
            Nice to meet you!
            <br />
            What should we call you?
          </h2>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Your answers to the next few questions will help us create a dashboard for
            you
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <Input
            placeholder="John Mayer"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="h-10 rounded-md px-3 text-sm"
            required
          />
          <Input
            type="email"
            placeholder="john@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="h-10 rounded-md px-3 text-sm"
            required
          />

          <Button
            type="submit"
            className="bg-primary text-primary-foreground hover:bg-primary/90 h-10 w-full rounded-md text-sm font-medium"
          >
            Continue
          </Button>
        </form>
      </div>
    </div>
  );
}

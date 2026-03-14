"use client";

import { useCallback, useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { signInWithEmailAndPassword } from "@/lib/auth/actions";

const FormSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address." }),
  password: z.string().min(6, { message: "Password must be at least 6 characters." }),
  remember: z.boolean().optional(),
});

export type LoginPrefill = {
  email: string;
  password: string;
};

type LoginFormProps = {
  prefill?: LoginPrefill;
};

export function LoginForm({ prefill }: LoginFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      email: "root@actbi.ai",
      password: "Passw0rd!",
      remember: false,
    },
  });

  const onSubmit = useCallback(
    async (data: z.infer<typeof FormSchema>) => {
      setIsLoading(true);

      try {
        const result = await signInWithEmailAndPassword({
          email: data.email,
          password: data.password,
          remember: data.remember,
        });

        const errorMessage = (result as { error?: string } | null)?.error;
        if (errorMessage) {
          toast.error("Login failed", {
            description: errorMessage,
          });
          return;
        }

        toast.success("Login successful!", {
          description: "You are being redirected to the dashboard.",
        });
        router.push("/admin/tenants");
      } catch (err) {
        // Only unexpected failures should reach here now
        toast.error("Login failed", {
          description:
            err instanceof Error
              ? err.message
              : "An unexpected error occurred. Please try again.",
        });
      } finally {
        setIsLoading(false);
      }
    },
    [router],
  );

  // Prefill from demo selector
  useEffect(() => {
    if (!prefill) return;
    form.setValue("email", prefill.email, { shouldDirty: true });
    form.setValue("password", prefill.password, { shouldDirty: true });
    form.setValue("remember", false, { shouldDirty: true });
    void form.handleSubmit(onSubmit)();
  }, [prefill, form, onSubmit]);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email Address</FormLabel>
              <FormControl>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="remember"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center">
              <FormControl>
                <Checkbox
                  id="login-remember"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  className="size-4"
                />
              </FormControl>
              <FormLabel
                htmlFor="login-remember"
                className="text-muted-foreground ml-1 text-sm font-medium"
              >
                Remember me for 30 days
              </FormLabel>
            </FormItem>
          )}
        />
        <Button className="w-full" type="submit" disabled={isLoading}>
          {isLoading ? "Signing in..." : "Login"}
        </Button>
      </form>
    </Form>
  );
}

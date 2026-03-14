"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useParams, useRouter } from "next/navigation";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
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

const createFormSchema = (t: (key: string) => string) =>
  z.object({
    email: z.string().email({ message: t("invalidEmail") }),
    password: z.string().min(6, { message: t("passwordMin") }),
    remember: z.boolean().optional(),
  });

type LoginFormValues = z.infer<ReturnType<typeof createFormSchema>>;

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
  const params = useParams();
  const locale = typeof params?.locale === "string" ? params.locale : "en";
  const t = useTranslations("auth");
  const formSchema = useMemo(() => createFormSchema(t), [t]);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "root@actbi.ai",
      password: "Passw0rd!",
      remember: false,
    },
  });

  const onSubmit = useCallback(
    async (data: LoginFormValues) => {
      setIsLoading(true);

      try {
        const result = await signInWithEmailAndPassword({
          email: data.email,
          password: data.password,
          remember: data.remember,
        });

        if (result && "error" in result) {
          toast.error(t("loginFailed"), {
            description: result.error,
          });
          return;
        }

        toast.success(t("loginSuccess"), {
          description: t("redirecting"),
        });
        router.push(`/${locale}/dashboard`);
      } catch (err) {
        // Only unexpected failures should reach here now
        toast.error(t("loginFailed"), {
          description: err instanceof Error ? err.message : t("unexpectedError"),
        });
      } finally {
        setIsLoading(false);
      }
    },
    [router, t, locale],
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
              <FormLabel>{t("emailAddress")}</FormLabel>
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
              <FormLabel>{t("password")}</FormLabel>
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
                {t("rememberMe")}
              </FormLabel>
            </FormItem>
          )}
        />
        <Button className="w-full" type="submit" disabled={isLoading}>
          {isLoading ? t("signingIn") : t("login")}
        </Button>
      </form>
    </Form>
  );
}

"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function ConnectBigQueryPage() {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="flex items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="bg-primary flex size-8 items-center justify-center rounded-lg">
            <span className="text-primary-foreground text-lg font-semibold">A</span>
          </div>
          <span className="text-card-foreground text-xl font-semibold">Actbi</span>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 pb-12">
        <div className="bg-card w-full max-w-[720px] rounded-2xl border p-10 shadow-sm">
          <div className="mb-8 flex items-center gap-4">
            <Link
              href="/onboarding"
              className="bg-card hover:border-primary/40 inline-flex items-center justify-center rounded-lg border px-3 py-2 text-sm font-medium"
            >
              <ArrowLeft className="mr-2 size-4" />
              Back
            </Link>
            <div className="bg-muted relative h-2 w-36 overflow-hidden rounded-full">
              <div className="bg-primary absolute left-0 top-0 h-full w-1/3 rounded-full" />
            </div>
          </div>

          <div className="mb-8 space-y-3">
            <h1 className="text-card-foreground text-3xl font-semibold leading-tight">
              Connect to BigQuery
            </h1>
            <p className="text-muted-foreground text-base">
              You&apos;re in control — Actbi only reads the data sources you allow.
            </p>
          </div>

          <form className="space-y-5">
            <div className="space-y-2">
              <label className="text-card-foreground text-sm font-medium">
                Connection name *
              </label>
              <Input
                placeholder="Enter a name for this connection"
                className="h-12 rounded-lg text-base"
              />
            </div>

            <div className="space-y-2">
              <label className="text-card-foreground text-sm font-medium">
                Service account JSON *
              </label>
              <Input
                placeholder="Enter your service_account_json"
                type="password"
                className="h-12 rounded-lg text-base"
              />
            </div>

            <div className="space-y-2">
              <label className="text-card-foreground text-sm font-medium">
                Location
              </label>
              <Select defaultValue="default">
                <SelectTrigger className="h-12 rounded-lg text-base">
                  <SelectValue placeholder="Select location" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">Select location</SelectItem>
                  <SelectItem value="us">US</SelectItem>
                  <SelectItem value="eu">EU</SelectItem>
                  <SelectItem value="apac">APAC</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-card-foreground text-sm font-medium">
                MFA type
              </label>
              <Select defaultValue="default">
                <SelectTrigger className="h-12 rounded-lg text-base">
                  <SelectValue placeholder="Select your mfa_type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">Select your mfa_type</SelectItem>
                  <SelectItem value="totp">Authenticator app (TOTP)</SelectItem>
                  <SelectItem value="sms">SMS</SelectItem>
                  <SelectItem value="webauthn">Security key / WebAuthn</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="text-primary space-y-2 text-sm font-medium">
              <Link
                href="https://cloud.google.com/bigquery/docs"
                target="_blank"
                className="inline-flex items-center gap-2 underline-offset-4 hover:underline"
              >
                Read the documentation
              </Link>
              <Link
                href="https://cloud.google.com/security"
                target="_blank"
                className="inline-flex items-center gap-2 underline-offset-4 hover:underline"
              >
                Security &amp; Trust Center
              </Link>
            </div>

            <Link href="/onboarding/connect-bigquery/success" className="block">
              <Button
                type="button"
                className="bg-primary text-primary-foreground hover:bg-primary/90 h-12 w-full rounded-lg text-base font-medium"
              >
                Add connection
              </Button>
            </Link>
          </form>
        </div>
      </main>
    </div>
  );
}

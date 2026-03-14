"use client";

import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function BigQuerySuccessPage() {
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
          <div className="mb-10">
            <div className="bg-muted relative h-2 w-36 overflow-hidden rounded-full">
              <div className="bg-primary absolute left-0 top-0 h-full w-2/3 rounded-full" />
            </div>
          </div>

          <div className="mb-10 flex items-start gap-4">
            <div className="mt-1 flex items-center justify-center">
              <CheckCircle2 className="size-12 text-emerald-600" />
            </div>
            <div className="space-y-2">
              <h1 className="text-card-foreground text-3xl font-semibold leading-tight">
                Successfully connected
                <br />
                to BigQuery!
              </h1>
              <p className="text-muted-foreground text-base">
                Lorem ipsum dolor lorem ipsum.
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-start">
            <Link href="/onboarding/connect-bigquery" className="md:w-[240px]">
              <Button
                type="button"
                variant="outline"
                className="border-muted bg-background h-12 w-full rounded-lg text-base font-medium"
              >
                Add another connector
              </Button>
            </Link>
            <Link href="/onboarding" className="md:w-[180px]">
              <Button
                type="button"
                className="bg-primary text-primary-foreground hover:bg-primary/90 h-12 w-full rounded-lg text-base font-medium"
              >
                Continue
              </Button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

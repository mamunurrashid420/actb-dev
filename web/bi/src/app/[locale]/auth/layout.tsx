import { ReactNode } from "react";

import Image from "next/image";

export default function Layout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <main className="min-h-dvh bg-[var(--background-main,#f0f7fd)]">
      <div className="grid min-h-dvh lg:grid-cols-[minmax(320px,38%)_minmax(0,62%)]">
        <aside className="hidden bg-white px-12 py-12 lg:flex lg:items-center lg:justify-center">
          <div className="mx-auto flex w-full max-w-[310px] flex-col items-center gap-6 text-center">
            <Image
              src="/Logo/actbi-logo-trimmed.png"
              alt="ActBI logo"
              width={97}
              height={100}
              className="h-auto w-[97px]"
              priority
            />
            <div className="space-y-4">
              <h1 className="text-[28px] leading-[1.4] font-medium tracking-[-0.04em] text-[#1e1e1e]">
                Welcome to ActBI.AI
              </h1>
              <p className="text-muted-foreground text-base leading-[1.5]">
                Ask questions, uncover insights, and build dashboards from your business data in minutes.
              </p>
            </div>
          </div>
        </aside>

        <section className="flex items-center justify-center bg-[var(--background-main,#f0f7fd)] px-6 py-10 lg:px-16">
          {children}
        </section>
      </div>
    </main>
  );
}

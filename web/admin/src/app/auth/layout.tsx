import { ReactNode } from "react";

import Image from "next/image";

export default function Layout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <main>
      <div className="grid h-dvh lg:grid-cols-2">
        <div className="bg-primary relative order-2 hidden h-full lg:flex">
          {/* Full image on the left side */}
          <Image
            src="/vision2.jpeg" // Using existing image
            alt="Authentication background"
            fill
            className="object-cover"
            style={{ objectPosition: "center" }}
          />
        </div>
        <div className="relative order-1 flex h-full">{children}</div>
      </div>
    </main>
  );
}

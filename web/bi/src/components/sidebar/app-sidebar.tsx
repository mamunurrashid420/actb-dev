"use client";

import type { ComponentProps } from "react";

import Image from "next/image";
import Link from "next/link";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { sidebarItems } from "@/navigation/sidebar/sidebar-items";

import { NavMain } from "./nav-main";
import { NavUser } from "./nav-user";

type AppSidebarProps = ComponentProps<typeof Sidebar> & {
  readonly user: {
    readonly name: string;
    readonly email: string;
    readonly avatar: string;
  };
  readonly homeHref?: string;
};

export function AppSidebar({
  user,
  homeHref = "/dashboard",
  ...props
}: AppSidebarProps) {
  const visibleItems = sidebarItems.filter((group) => group.items.length > 0);
  return (
    <Sidebar {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:!p-1.5"
            >
              <Link href={homeHref} className="flex items-center gap-2">
                <div className="flex h-10 items-center group-data-[collapsible=icon]:hidden">
                  <Image
                    src="/Logo/actbi-logo-w-text.png"
                    alt="Actbi Logo"
                    width={120}
                    height={32}
                    className="block h-8 w-auto object-contain"
                    priority
                  />
                </div>
                <div className="text-primary-foreground hidden h-8 w-8 items-center justify-center rounded bg-transparent group-data-[collapsible=icon]:flex">
                  <Image
                    src="/Logo/actbi-logo-trimmed.png"
                    alt="Actbi icon"
                    width={32}
                    height={32}
                    className="block h-8 w-auto object-contain dark:hidden"
                    priority
                  />
                  <Image
                    src="/Logo/actbi-logo-trimmed.png"
                    alt="Actbi icon"
                    width={32}
                    height={32}
                    className="hidden h-8 w-auto object-contain dark:block"
                    priority
                  />
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={visibleItems} />
        {/* <NavDocuments items={data.documents} /> */}
        {/* <NavSecondary items={data.navSecondary} className="mt-auto" /> */}
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={user} />
      </SidebarFooter>
    </Sidebar>
  );
}

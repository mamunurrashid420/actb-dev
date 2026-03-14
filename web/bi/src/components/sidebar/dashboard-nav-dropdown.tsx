"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  ChevronDown,
  LayoutDashboard,
  BriefcaseBusiness,
  PiggyBank,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function DashboardNavDropdown() {
  const pathname = usePathname() ?? "";

  const navItems: Array<{
    name: string;
    href: string;
    icon: LucideIcon;
  }> = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
    },
    {
      name: "CRM",
      href: "/crm",
      icon: BriefcaseBusiness,
    },
    {
      name: "Finance",
      href: "/finance",
      icon: PiggyBank,
    },
  ];

  const currentItem = navItems.find((item) => pathname.startsWith(item.href));
  const CurrentIcon = currentItem?.icon;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="flex items-center gap-2">
          {CurrentIcon ? <CurrentIcon className="size-4" /> : null}
          {currentItem?.name ?? "Select Dashboard"}
          <ChevronDown className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {navItems.map((item) => (
          <DropdownMenuItem key={item.name} asChild>
            <Link href={item.href} className="flex items-center gap-2">
              <item.icon className="size-4" />
              {item.name}
            </Link>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

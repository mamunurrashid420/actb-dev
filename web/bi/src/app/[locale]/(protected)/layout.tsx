"use client";

import { useState, type ReactNode } from "react";

import {
  ChevronDown,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquareText,
  MoreHorizontal,
  Pin,
  Plus,
} from "lucide-react";

import { Link, usePathname, useRouter } from "@/i18n/routing";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { signOut } from "@/lib/auth/actions";
import { cn } from "@/lib/utils";

const PRIMARY_ITEMS = [
  {
    label: "Conversations",
    icon: MessageSquareText,
    href: "/conversations",
  },
  {
    label: "Dashboards",
    icon: LayoutDashboard,
    href: "/dashboard",
  },
  {
    label: "Reports",
    icon: FileText,
  },
];

const PINNED_ITEMS = [
  {
    label: "Product cost in Q4",
    count: 4,
  },
  {
    label: "Q4 Revenue Analysis",
    count: 3,
  },
];

const DASHBOARD_ITEMS = [
  {
    label: "Customer growth and retention",
    count: 2,
  },
  {
    label: "Channel performance breakdown",
    count: 1,
  },
];

export default function PublicLayout({ children }: Readonly<{ children: ReactNode }>) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isPinnedOpen, setIsPinnedOpen] = useState(true);
  const [isDashboardsOpen, setIsDashboardsOpen] = useState(true);
  const pathname = usePathname();
  const router = useRouter();
  const handleProfileNavigate = (path: string) => {
    router.push(path);
  };
  const handleLogout = async () => {
    await signOut();
  };

  return (
    <div className="bg-background text-foreground min-h-screen">
      <div className="flex min-h-screen flex-col md:h-screen md:flex-row md:overflow-hidden">
        <aside
          className={cn(
            "bg-sidebar flex w-full flex-col border-b border-sidebar-border transition-[width] duration-200 md:sticky md:top-0 md:h-screen md:border-r md:border-b-0",
            isCollapsed ? "md:w-16" : "md:w-72",
          )}
        >
          <div
            className={cn(
              "flex shrink-0 items-center justify-between px-4 py-3",
              isCollapsed && "md:flex-col md:gap-2 md:px-2",
            )}
          >
            <button
              type="button"
              aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={() => setIsCollapsed((prev) => !prev)}
              className="bg-background text-muted-foreground hover:bg-muted inline-flex size-9 items-center justify-center rounded-md border transition"
            >
              <Menu className="size-4" />
            </button>
            <div className="bg-background flex size-9 items-center justify-center rounded-md border">
              <span className="text-xs font-semibold">OM</span>
            </div>
          </div>

          <div className={cn("flex min-h-0 flex-1 flex-col overflow-y-auto", isCollapsed && "md:px-1")}>
            <div className={cn("px-4", isCollapsed && "md:px-2")}>
              <Link
                href="/conversations/new"
                className={cn(
                  "text-foreground flex items-center gap-2 text-[14px] font-normal leading-[1.5] transition",
                  isCollapsed ? "justify-center" : "px-1",
                )}
              >
                <span className="bg-primary text-primary-foreground inline-flex size-8 items-center justify-center rounded-full">
                  <Plus className="size-4" />
                </span>
                {!isCollapsed ? "New conversation" : null}
              </Link>
            </div>

            <div className={cn("mt-5 space-y-6 px-2 pb-4", isCollapsed && "md:px-1")}>
              <div>
                {!isCollapsed ? (
                  <div className="text-muted-foreground flex items-center justify-between px-2 text-[12px] font-semibold leading-[1.5]">
                    <span>Workspace</span>
                  </div>
                ) : null}
                <div className={cn("mt-2 space-y-1", isCollapsed && "md:space-y-2")}>
                  {PRIMARY_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const isActive = item.href ? pathname.startsWith(item.href) : false;
                    const itemClasses = cn(
                      "flex w-full items-center rounded-md text-[14px] font-normal leading-[1.5] transition",
                      isCollapsed ? "md:justify-center md:px-0 md:py-2" : "px-3 py-2 gap-2",
                      isActive
                        ? "bg-muted text-foreground"
                        : "text-foreground hover:bg-muted/60",
                    );

                    if (item.href) {
                      return (
                        <Link key={item.label} href={item.href} className={itemClasses}>
                          <Icon className="size-4" />
                          {!isCollapsed ? item.label : null}
                        </Link>
                      );
                    }

                    return (
                      <button key={item.label} type="button" className={itemClasses}>
                        <Icon className="size-4" />
                        {!isCollapsed ? item.label : null}
                      </button>
                    );
                  })}

                  {isCollapsed ? (
                    <button
                      type="button"
                      className="text-muted-foreground hover:bg-muted/60 hover:text-foreground flex w-full items-center justify-center rounded-md transition md:py-2"
                    >
                      <Pin className="size-4" />
                    </button>
                  ) : null}
                </div>
              </div>

              {!isCollapsed ? (
                <div>
                  <div className="text-muted-foreground flex items-center justify-between px-2 text-[12px] font-semibold leading-[1.5]">
                    <span>Pinned</span>
                    <button
                      type="button"
                      onClick={() => setIsPinnedOpen((prev) => !prev)}
                      className="hover:text-foreground inline-flex size-5 items-center justify-center rounded-sm transition"
                      aria-label={isPinnedOpen ? "Collapse pinned" : "Expand pinned"}
                    >
                      <ChevronDown className={cn("size-3 transition-transform", !isPinnedOpen && "-rotate-90")} />
                    </button>
                  </div>
                  {isPinnedOpen ? (
                    <div className="mt-2 space-y-1">
                      {PINNED_ITEMS.map((item) => (
                        <button
                          key={item.label}
                          type="button"
                          className="text-muted-foreground hover:bg-muted/60 hover:text-foreground flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-[14px] font-normal leading-[1.5] transition"
                        >
                          <span className="truncate text-popover-foreground">{item.label}</span>
                          <span className="text-muted-foreground text-[12px] font-normal leading-[1.5]">
                            {item.count}
                          </span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {!isCollapsed ? (
                <div>
                  <div className="text-muted-foreground flex items-center justify-between px-2 text-[12px] font-semibold leading-[1.5]">
                    <span>Dashboards</span>
                    <button
                      type="button"
                      onClick={() => setIsDashboardsOpen((prev) => !prev)}
                      className="hover:text-foreground inline-flex size-5 items-center justify-center rounded-sm transition"
                      aria-label={isDashboardsOpen ? "Collapse dashboards" : "Expand dashboards"}
                    >
                      <ChevronDown className={cn("size-3 transition-transform", !isDashboardsOpen && "-rotate-90")} />
                    </button>
                  </div>
                  {isDashboardsOpen ? (
                    <div className="mt-2 space-y-1">
                      {DASHBOARD_ITEMS.map((item) => (
                        <button
                          key={item.label}
                          type="button"
                          className="text-muted-foreground hover:bg-muted/60 hover:text-foreground flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-[14px] font-normal leading-[1.5] transition"
                        >
                          <span className="truncate text-popover-foreground">{item.label}</span>
                          <span className="text-muted-foreground text-[12px] font-normal leading-[1.5]">
                            {item.count}
                          </span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          </div>

          <div className={cn("mt-auto shrink-0 px-4 py-3", isCollapsed && "md:px-2")}>
            <div className={cn("flex items-center gap-3", isCollapsed && "md:flex-col md:gap-2")}>
              <div className="bg-muted flex size-9 items-center justify-center rounded-full text-xs font-semibold">
                JD
              </div>
              {!isCollapsed ? (
                <>
                  <div className="flex-1">
                    <p className="text-popover-foreground text-[14px] font-normal leading-[1.5]">John Doe</p>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button
                        type="button"
                        className="text-muted-foreground hover:bg-muted hover:text-foreground inline-flex size-8 items-center justify-center rounded-md transition"
                      >
                        <MoreHorizontal className="size-4" />
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onSelect={() => handleProfileNavigate("/settings/account")}>
                        Account settings
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={() => handleProfileNavigate("/settings/organization")}>
                        Organization settings
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={() => handleProfileNavigate("/settings/users")}>
                        Users
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={handleLogout}>
                        <LogOut className="size-4" />
                        Logout
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </>
              ) : (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      className="text-muted-foreground hover:bg-muted hover:text-foreground inline-flex size-8 items-center justify-center rounded-md transition"
                    >
                      <MoreHorizontal className="size-4" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onSelect={() => handleProfileNavigate("/settings/account")}>
                      Account settings
                    </DropdownMenuItem>
                    <DropdownMenuItem onSelect={() => handleProfileNavigate("/settings/organization")}>
                      Organization settings
                    </DropdownMenuItem>
                    <DropdownMenuItem onSelect={() => handleProfileNavigate("/settings/users")}>
                      Users
                    </DropdownMenuItem>
                    <DropdownMenuItem onSelect={handleLogout}>
                      <LogOut className="size-4" />
                      Logout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
        </aside>

        <main className="bg-background min-w-0 flex-1 overflow-x-hidden md:overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

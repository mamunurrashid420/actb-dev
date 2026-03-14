import { ReactNode } from "react";

import { cookies } from "next/headers";
import { AccountSwitcher } from "@/components/sidebar/account-switcher";
import { AppSidebar } from "@/components/sidebar/app-sidebar";
import { ThemeSwitcher } from "@/components/sidebar/theme-switcher";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { requireSuperadmin } from "@/lib/auth/require-superadmin";
import { apiServerRequest } from "@/lib/api-server";
import type { UserProfile } from "@/types/profile";
import { cn } from "@/lib/utils";

export default async function Layout({ children }: Readonly<{ children: ReactNode }>) {
  const authContext = await requireSuperadmin();

  const cookieStore = await cookies();
  const defaultOpen = cookieStore.get("sidebar_state")?.value !== "false";

  // Fixed layout choices; theme can still toggle light/dark via the header switcher.
  const layoutPreferences = {
    contentLayout: "centered",
    variant: "sidebar",
    collapsible: "icon",
    navbarStyle: "sticky",
  } as const;

  const profile = await apiServerRequest<UserProfile>("GET", "/users/me/profile");
  const email = authContext.email ?? "";
  const emailLocalPart = email.includes("@") ? email.split("@")[0] : "";
  const fullName = profile?.full_name ?? emailLocalPart;
  const avatarUrl = profile?.avatar_url ?? "";
  const transformedUser = {
    id: authContext.id,
    name: fullName ?? (emailLocalPart !== "" ? emailLocalPart : "User"),
    email,
    avatar: avatarUrl ?? "",
    role: authContext.claims?.["is_app_admin"] ? "App Admin" : "Member",
  };

  return (
    <SidebarProvider defaultOpen={defaultOpen}>
      <AppSidebar
        user={transformedUser}
        variant={layoutPreferences.variant}
        collapsible={layoutPreferences.collapsible}
      />
      <SidebarInset
        data-content-layout={layoutPreferences.contentLayout}
        className={cn(
          "data-[content-layout=centered]:!mx-auto data-[content-layout=centered]:max-w-screen-2xl",
          // Adds right margin for inset sidebar in centered layout up to 113rem.
          // On wider screens with collapsed sidebar, removes margin and sets margin auto for alignment.
          "max-[113rem]:peer-data-[variant=inset]:!mr-2 min-[101rem]:peer-data-[variant=inset]:peer-data-[state=collapsed]:!mr-auto",
        )}
      >
        <header
          data-navbar-style={layoutPreferences.navbarStyle}
          className={cn(
            "group-has-data-[collapsible=icon]/sidebar-wrapper:h-12 flex h-12 shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear",
            // Handle sticky navbar style with conditional classes so blur, background, z-index, and rounded corners remain consistent across all SidebarVariant layouts.
            "data-[navbar-style=sticky]:bg-background/50 data-[navbar-style=sticky]:sticky data-[navbar-style=sticky]:top-0 data-[navbar-style=sticky]:z-50 data-[navbar-style=sticky]:overflow-hidden data-[navbar-style=sticky]:rounded-t-[inherit] data-[navbar-style=sticky]:backdrop-blur-md",
          )}
        >
          <div className="flex w-full items-center justify-between px-4 lg:px-6">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <ThemeSwitcher />
              <AccountSwitcher users={[transformedUser]} />
            </div>
          </div>
        </header>
        <div className="h-full p-4 md:p-6">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}

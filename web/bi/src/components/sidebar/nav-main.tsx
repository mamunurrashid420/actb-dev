"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  ChevronRight,
  Database,
  LayoutDashboard,
  MailIcon,
  PlusCircleIcon,
  UserCircle,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  type NavGroup,
  type NavMainItem,
  type SidebarIconKey,
} from "@/navigation/sidebar/sidebar-items";

interface NavMainProps {
  readonly items: readonly NavGroup[];
}

const IsComingSoon = ({ label }: { label: string }) => (
  <span className="ml-auto rounded-md bg-gray-200 px-2 py-1 text-xs dark:text-gray-800">
    {label}
  </span>
);

const ICONS: Record<SidebarIconKey, LucideIcon> = {
  "layout-dashboard": LayoutDashboard,
  database: Database,
  "user-circle": UserCircle,
};

const getIcon = (icon?: SidebarIconKey) => (icon ? ICONS[icon] : null);

const NavItemExpanded = ({
  item,
  isActive,
  isSubmenuOpen,
  t,
}: {
  item: NavMainItem;
  isActive: (url: string, subItems?: NavMainItem["subItems"]) => boolean;
  isSubmenuOpen: (subItems?: NavMainItem["subItems"]) => boolean;
  t: (key: string) => string;
}) => {
  const title = t(item.titleKey);
  const ItemIcon = getIcon(item.icon);

  return (
    <Collapsible
      key={item.titleKey}
      asChild
      defaultOpen={isSubmenuOpen(item.subItems)}
      className="group/collapsible"
    >
      <SidebarMenuItem>
        <CollapsibleTrigger asChild>
          {item.subItems ? (
            <SidebarMenuButton
              disabled={item.comingSoon}
              isActive={isActive(item.url, item.subItems)}
              tooltip={title}
            >
              {ItemIcon && <ItemIcon />}
              <span>{title}</span>
              {item.comingSoon && <IsComingSoon label={t("soon")} />}
              <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
            </SidebarMenuButton>
          ) : (
            <SidebarMenuButton
              asChild
              aria-disabled={item.comingSoon}
              isActive={isActive(item.url)}
              tooltip={title}
            >
              <Link href={item.url} target={item.newTab ? "_blank" : undefined}>
                {ItemIcon && <ItemIcon />}
                <span>{title}</span>
                {item.comingSoon && <IsComingSoon label={t("soon")} />}
              </Link>
            </SidebarMenuButton>
          )}
        </CollapsibleTrigger>
        {item.subItems && (
          <CollapsibleContent>
            <SidebarMenuSub>
              {item.subItems.map((subItem) => {
                const subTitle = t(subItem.titleKey);
                const SubIcon = getIcon(subItem.icon);
                return (
                  <SidebarMenuSubItem key={subItem.titleKey}>
                    <SidebarMenuSubButton
                      aria-disabled={subItem.comingSoon}
                      isActive={isActive(subItem.url)}
                      asChild
                    >
                      <Link
                        href={subItem.url}
                        target={subItem.newTab ? "_blank" : undefined}
                      >
                        {SubIcon && <SubIcon />}
                        <span>{subTitle}</span>
                        {subItem.comingSoon && <IsComingSoon label={t("soon")} />}
                      </Link>
                    </SidebarMenuSubButton>
                  </SidebarMenuSubItem>
                );
              })}
            </SidebarMenuSub>
          </CollapsibleContent>
        )}
      </SidebarMenuItem>
    </Collapsible>
  );
};

const NavItemCollapsed = ({
  item,
  isActive,
  t,
}: {
  item: NavMainItem;
  isActive: (url: string, subItems?: NavMainItem["subItems"]) => boolean;
  t: (key: string) => string;
}) => {
  const title = t(item.titleKey);
  const ItemIcon = getIcon(item.icon);

  return (
    <SidebarMenuItem key={item.titleKey}>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton
            disabled={item.comingSoon}
            tooltip={title}
            isActive={isActive(item.url, item.subItems)}
          >
            {ItemIcon && <ItemIcon />}
            <span>{title}</span>
            <ChevronRight />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-50 space-y-1" side="right" align="start">
          {item.subItems?.map((subItem) => {
            const subTitle = t(subItem.titleKey);
            const SubIcon = getIcon(subItem.icon);
            return (
              <DropdownMenuItem key={subItem.titleKey} asChild>
                <SidebarMenuSubButton
                  key={subItem.titleKey}
                  asChild
                  className="focus-visible:ring-0"
                  aria-disabled={subItem.comingSoon}
                  isActive={isActive(subItem.url)}
                >
                  <Link
                    href={subItem.url}
                    target={subItem.newTab ? "_blank" : undefined}
                  >
                    {SubIcon && <SubIcon className="[&>svg]:text-sidebar-foreground" />}
                    <span>{subTitle}</span>
                    {subItem.comingSoon && <IsComingSoon label={t("soon")} />}
                  </Link>
                </SidebarMenuSubButton>
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  );
};

export function NavMain({ items }: NavMainProps) {
  const path = usePathname() ?? "";
  const { state, isMobile } = useSidebar();
  const t = useTranslations("sidebar");

  const isItemActive = (url: string, subItems?: NavMainItem["subItems"]) => {
    if (subItems?.length) {
      return subItems.some((sub) => path.startsWith(sub.url));
    }
    return path === url || path.endsWith(url);
  };

  const isSubmenuOpen = (subItems?: NavMainItem["subItems"]) => {
    return subItems?.some((sub) => path.startsWith(sub.url)) ?? false;
  };

  return (
    <>
      <SidebarGroup>
        <SidebarGroupContent className="flex flex-col gap-2">
          <SidebarMenu>
            <SidebarMenuItem className="flex items-center gap-2">
              <SidebarMenuButton
                tooltip={t("quickCreate")}
                className="bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground active:bg-primary/90 active:text-primary-foreground min-w-8 duration-200 ease-linear"
              >
                <PlusCircleIcon />
                <span>{t("quickCreate")}</span>
              </SidebarMenuButton>
              <Button
                size="icon"
                className="h-9 w-9 shrink-0 group-data-[collapsible=icon]:opacity-0"
                variant="outline"
              >
                <MailIcon />
                <span className="sr-only">{t("inbox")}</span>
              </Button>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      {items.map((group) => (
        <SidebarGroup key={group.id}>
          {group.labelKey && <SidebarGroupLabel>{t(group.labelKey)}</SidebarGroupLabel>}
          <SidebarGroupContent className="flex flex-col gap-2">
            <SidebarMenu>
              {group.items.map((item) => {
                const title = t(item.titleKey);
                const ItemIcon = getIcon(item.icon);
                if (state === "collapsed" && !isMobile) {
                  // If no subItems, just render the button as a link
                  if (!item.subItems) {
                    return (
                      <SidebarMenuItem key={item.titleKey}>
                        <SidebarMenuButton
                          asChild
                          aria-disabled={item.comingSoon}
                          tooltip={title}
                          isActive={isItemActive(item.url)}
                        >
                          <Link
                            href={item.url}
                            target={item.newTab ? "_blank" : undefined}
                          >
                            {ItemIcon && <ItemIcon />}
                            <span>{title}</span>
                          </Link>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    );
                  }
                  // Otherwise, render the dropdown as before
                  return (
                    <NavItemCollapsed
                      key={item.titleKey}
                      item={item}
                      isActive={isItemActive}
                      t={t}
                    />
                  );
                }
                // Expanded view
                return (
                  <NavItemExpanded
                    key={item.titleKey}
                    item={item}
                    isActive={isItemActive}
                    isSubmenuOpen={isSubmenuOpen}
                    t={t}
                  />
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      ))}
    </>
  );
}

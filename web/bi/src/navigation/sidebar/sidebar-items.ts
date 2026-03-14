export type SidebarIconKey =
  | "layout-dashboard"
  | "user-circle"
  | "database";

export interface NavSubItem {
  titleKey: string; // Translation key
  url: string;
  icon?: SidebarIconKey;
  comingSoon?: boolean;
  newTab?: boolean;
  isNew?: boolean;
}

export interface NavMainItem {
  titleKey: string; // Translation key
  url: string;
  icon?: SidebarIconKey;
  subItems?: NavSubItem[];
  comingSoon?: boolean;
  newTab?: boolean;
  isNew?: boolean;
}

export interface NavGroup {
  id: number;
  labelKey?: string; // Translation key
  items: NavMainItem[];
}

export const sidebarItems: NavGroup[] = [
  {
    id: 1,
    labelKey: "groups.dashboards",
    items: [
      {
        titleKey: "items.default",
        url: "/dashboard",
        icon: "layout-dashboard",
      },
      {
        titleKey: "items.profile",
        url: "/profile",
        icon: "user-circle",
      },
    ],
  },
];

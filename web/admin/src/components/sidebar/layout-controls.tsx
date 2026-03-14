"use client";

import { Settings } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { updateContentLayout, updateNavbarStyle } from "@/lib/layout-utils";
import { setPreferenceCookie } from "@/lib/actions/preferences-actions";
import { updateThemeMode } from "@/lib/theme-utils";
import { usePreferencesStore } from "@/stores/preferences/preferences-provider";
import type {
  SidebarVariant,
  SidebarCollapsible,
  ContentLayout,
  NavbarStyle,
} from "@/types/preferences/layout";
import { type ThemeMode } from "@/types/preferences/theme";

type LayoutControlsProps = {
  readonly variant: SidebarVariant;
  readonly collapsible: SidebarCollapsible;
  readonly contentLayout: ContentLayout;
  readonly navbarStyle: NavbarStyle;
};

export function LayoutControls(props: LayoutControlsProps) {
  const { variant, collapsible, contentLayout, navbarStyle } = props;

  const themeMode = usePreferencesStore((s) => s.themeMode);
  const setThemeMode = usePreferencesStore((s) => s.setThemeMode);

  const handleValueChange = async (key: string, value: string) => {
    if (key === "theme_mode") {
      updateThemeMode(value as ThemeMode);
      setThemeMode(value as ThemeMode);
    }

    if (key === "content_layout") {
      updateContentLayout(value as ContentLayout);
    }

    if (key === "navbar_style") {
      updateNavbarStyle(value as NavbarStyle);
    }
    await setPreferenceCookie(key, value);
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button size="icon" variant="ghost">
          <Settings />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end">
        <div className="flex flex-col gap-5">
          <div className="space-y-1.5">
            <h4 className="text-sm font-medium leading-none">Layout Settings</h4>
            <p className="text-muted-foreground text-xs">
              Customize your dashboard layout preferences.
            </p>
          </div>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label className="text-xs font-medium">Mode</Label>
              <ToggleGroup
                className="w-full"
                size="sm"
                variant="outline"
                type="single"
                value={themeMode}
                onValueChange={(value) => handleValueChange("theme_mode", value)}
              >
                <ToggleGroupItem
                  className="text-xs"
                  value="light"
                  aria-label="Toggle inset"
                >
                  Light
                </ToggleGroupItem>
                <ToggleGroupItem
                  className="text-xs"
                  value="dark"
                  aria-label="Toggle sidebar"
                >
                  Dark
                </ToggleGroupItem>
              </ToggleGroup>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">Sidebar Variant</Label>
              <ToggleGroup
                className="w-full"
                size="sm"
                variant="outline"
                type="single"
                value={variant}
                onValueChange={(value) => handleValueChange("sidebar_variant", value)}
              >
                <ToggleGroupItem
                  className="text-xs"
                  value="inset"
                  aria-label="Toggle inset"
                >
                  Inset
                </ToggleGroupItem>
                <ToggleGroupItem
                  className="text-xs"
                  value="sidebar"
                  aria-label="Toggle sidebar"
                >
                  Sidebar
                </ToggleGroupItem>
                <ToggleGroupItem
                  className="text-xs"
                  value="floating"
                  aria-label="Toggle floating"
                >
                  Floating
                </ToggleGroupItem>
              </ToggleGroup>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">Navbar Style</Label>
              <ToggleGroup
                className="w-full"
                size="sm"
                variant="outline"
                type="single"
                value={navbarStyle}
                onValueChange={(value) => handleValueChange("navbar_style", value)}
              >
                <ToggleGroupItem
                  className="text-xs"
                  value="sticky"
                  aria-label="Toggle sticky"
                >
                  Sticky
                </ToggleGroupItem>
                <ToggleGroupItem
                  className="text-xs"
                  value="scroll"
                  aria-label="Toggle scroll"
                >
                  Scroll
                </ToggleGroupItem>
              </ToggleGroup>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">Sidebar Collapsible</Label>
              <ToggleGroup
                className="w-full"
                size="sm"
                variant="outline"
                type="single"
                value={collapsible}
                onValueChange={(value) =>
                  handleValueChange("sidebar_collapsible", value)
                }
              >
                <ToggleGroupItem
                  className="text-xs"
                  value="icon"
                  aria-label="Toggle icon"
                >
                  Icon
                </ToggleGroupItem>
                <ToggleGroupItem
                  className="text-xs"
                  value="offcanvas"
                  aria-label="Toggle offcanvas"
                >
                  OffCanvas
                </ToggleGroupItem>
              </ToggleGroup>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">Content Layout</Label>
              <ToggleGroup
                className="w-full"
                size="sm"
                variant="outline"
                type="single"
                value={contentLayout}
                onValueChange={(value) => handleValueChange("content_layout", value)}
              >
                <ToggleGroupItem
                  className="text-xs"
                  value="centered"
                  aria-label="Toggle centered"
                >
                  Centered
                </ToggleGroupItem>
                <ToggleGroupItem
                  className="text-xs"
                  value="full-width"
                  aria-label="Toggle full-width"
                >
                  Full Width
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

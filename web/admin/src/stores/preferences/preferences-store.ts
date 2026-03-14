import { createStore } from "zustand/vanilla";

import type { ThemeMode } from "@/types/preferences/theme";

export type PreferencesState = {
  themeMode: ThemeMode;
  setThemeMode: (mode: ThemeMode) => void;
};

export const createPreferencesStore = (init?: Partial<PreferencesState>) =>
  createStore<PreferencesState>()((set) => ({
    themeMode: init?.themeMode ?? "light",
    setThemeMode: (mode) => set({ themeMode: mode }),
  }));

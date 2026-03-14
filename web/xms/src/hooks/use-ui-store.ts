import { create } from "zustand";

export type Workspace = "variables" | "snippets" | "prompts";

type UiState = {
  activeWorkspace: Workspace;
  setActiveWorkspace: (workspace: Workspace) => void;

  // Unsaved changes & save handlers per workspace
  unsaved: Partial<Record<Workspace, boolean>>;
  setUnsaved: (workspace: Workspace, value: boolean) => void;
  saveHandlers: Partial<Record<Workspace, () => void | Promise<void>>>;
  registerSaveHandler: (
    workspace: Workspace,
    handler: () => void | Promise<void>,
  ) => void;

  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;

  helpPanelOpen: boolean;
  setHelpPanelOpen: (open: boolean) => void;
};

export const useUiStore = create<UiState>((set) => ({
  activeWorkspace: "variables",
  setActiveWorkspace: (activeWorkspace) => set({ activeWorkspace }),

  unsaved: { variables: false, snippets: false, prompts: false },
  setUnsaved: (workspace, value) =>
    set((state) => {
      const current = state.unsaved?.[workspace] ?? false;
      if (current === value) return state;
      return { unsaved: { ...state.unsaved, [workspace]: value } };
    }),
  saveHandlers: {},
  registerSaveHandler: (workspace, handler) =>
    set((state) => ({
      saveHandlers: { ...state.saveHandlers, [workspace]: handler },
    })),

  commandPaletteOpen: false,
  setCommandPaletteOpen: (commandPaletteOpen) => set({ commandPaletteOpen }),

  helpPanelOpen: false,
  setHelpPanelOpen: (helpPanelOpen) => set({ helpPanelOpen }),
}));

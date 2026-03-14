import type { Prompt } from "@/types/prompt";

export interface PromptCreateInput {
  name: string;
  tags: string[];
  blocks: Prompt["blocks"];
}

export interface PromptUpdateInput {
  id: string;
  name?: string;
  tags?: string[];
  blocks?: Prompt["blocks"];
}

export interface PromptStore {
  list(): Promise<Prompt[]>;
  getById(id: string): Promise<Prompt | undefined>;
  create(input: PromptCreateInput): Promise<Prompt>;
  update(input: PromptUpdateInput): Promise<Prompt | undefined>;
  delete(id: string): Promise<boolean>;
  clear(): Promise<void>;
}

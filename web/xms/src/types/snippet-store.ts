import type { Snippet } from "@/types/snippet";

export interface SnippetCreateInput {
  name: string;
  body: string;
  tags: string[];
}

export interface SnippetUpdateInput {
  id: string;
  name?: string;
  body?: string;
  tags?: string[];
}

export interface SnippetStore {
  list(): Promise<Snippet[]>;
  getById(id: string): Promise<Snippet | undefined>;
  create(input: SnippetCreateInput): Promise<Snippet>;
  update(input: SnippetUpdateInput): Promise<Snippet | undefined>;
  delete(id: string): Promise<boolean>;
  clear(): Promise<void>;
}

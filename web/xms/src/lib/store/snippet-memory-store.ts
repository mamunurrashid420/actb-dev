import type { Snippet } from "@/types/snippet";
import type {
  SnippetCreateInput,
  SnippetStore,
  SnippetUpdateInput,
} from "@/types/snippet-store";
import { generateId } from "@/lib/utils";

export class SnippetMemoryStore implements SnippetStore {
  private readonly store = new Map<string, Snippet>();

  async list(): Promise<Snippet[]> {
    return Array.from(this.store.values());
  }

  async getById(id: string): Promise<Snippet | undefined> {
    return this.store.get(id);
  }

  async create(input: SnippetCreateInput): Promise<Snippet> {
    const now = new Date().toISOString();
    const wordCount = input.body.trim().split(/\s+/).filter(Boolean).length;
    const entity: Snippet = {
      id: generateId(),
      name: input.name,
      body: input.body,
      tags: input.tags,
      wordCount,
      usedInPrompts: 0,
      createdAt: now,
      updatedAt: now,
    };
    this.store.set(entity.id, entity);
    return entity;
  }

  async update(input: SnippetUpdateInput): Promise<Snippet | undefined> {
    const existing = this.store.get(input.id);
    if (!existing) return undefined;
    const body = input.body ?? existing.body;
    const updated: Snippet = {
      ...existing,
      ...(input.name !== undefined ? { name: input.name } : {}),
      ...(input.body !== undefined ? { body } : {}),
      ...(input.tags !== undefined ? { tags: input.tags } : {}),
      wordCount: body.trim().split(/\s+/).filter(Boolean).length,
      updatedAt: new Date().toISOString(),
    };
    this.store.set(updated.id, updated);
    return updated;
  }

  async delete(id: string): Promise<boolean> {
    return this.store.delete(id);
  }

  async clear(): Promise<void> {
    this.store.clear();
  }
}

export const snippetMemoryStore = new SnippetMemoryStore();

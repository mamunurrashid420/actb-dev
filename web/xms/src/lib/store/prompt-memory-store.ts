import type { Prompt } from "@/types/prompt";
import type {
  PromptCreateInput,
  PromptStore,
  PromptUpdateInput,
} from "@/types/prompt-store";
import { generateId } from "@/lib/utils";

export class PromptMemoryStore implements PromptStore {
  private readonly store = new Map<string, Prompt>();

  async list(): Promise<Prompt[]> {
    return Array.from(this.store.values());
  }

  async getById(id: string): Promise<Prompt | undefined> {
    return this.store.get(id);
  }

  async create(input: PromptCreateInput): Promise<Prompt> {
    const now = new Date().toISOString();
    const entity: Prompt = {
      id: generateId(),
      name: input.name,
      tags: input.tags,
      blocks: input.blocks,
      createdAt: now,
      updatedAt: now,
    };
    this.store.set(entity.id, entity);
    return entity;
  }

  async update(input: PromptUpdateInput): Promise<Prompt | undefined> {
    const existing = this.store.get(input.id);
    if (!existing) return undefined;
    const updated: Prompt = {
      ...existing,
      ...(input.name !== undefined ? { name: input.name } : {}),
      ...(input.tags !== undefined ? { tags: input.tags } : {}),
      ...(input.blocks !== undefined ? { blocks: input.blocks } : {}),
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

export const promptMemoryStore = new PromptMemoryStore();

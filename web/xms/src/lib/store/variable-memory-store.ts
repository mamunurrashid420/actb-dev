import type { Variable } from "@/types/variable";
import type {
  VariableCreateInput,
  VariableStore,
  VariableUpdateInput,
} from "@/types/variable-store";
import { generateId } from "@/lib/utils";

export class VariableMemoryStore implements VariableStore {
  private readonly store = new Map<string, Variable>();

  async list(): Promise<Variable[]> {
    return Array.from(this.store.values());
  }

  async getById(id: string): Promise<Variable | undefined> {
    return this.store.get(id);
  }

  async create(input: VariableCreateInput): Promise<Variable> {
    const now = new Date().toISOString();
    const v: Variable = {
      id: generateId(),
      name: input.name,
      type: input.type,
      defaultValue: input.defaultValue,
      description: input.description,
      tags: input.tags,
      createdAt: now,
      updatedAt: now,
    };
    this.store.set(v.id, v);
    return v;
  }

  async update(input: VariableUpdateInput): Promise<Variable | undefined> {
    const existing = this.store.get(input.id);
    if (!existing) return undefined;
    const updated: Variable = {
      ...existing,
      ...(input.name !== undefined ? { name: input.name } : {}),
      ...(input.type !== undefined ? { type: input.type } : {}),
      ...(input.defaultValue !== undefined ? { defaultValue: input.defaultValue } : {}),
      ...(input.description !== undefined ? { description: input.description } : {}),
      ...(input.tags !== undefined ? { tags: input.tags } : {}),
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

export const variableMemoryStore = new VariableMemoryStore();

import { getAdminSupabase } from "@/lib/supabase";
import type { Prompt } from "@/types/prompt";
import type {
  PromptCreateInput,
  PromptStore,
  PromptUpdateInput,
} from "@/types/prompt-store";

type DbPromptRow = {
  id: string;
  name: string;
  tags: string[];
  blocks: unknown;
  created_at: string;
  updated_at: string;
};

function mapRowToPrompt(row: DbPromptRow): Prompt {
  return {
    id: row.id,
    name: row.name,
    tags: row.tags,
    blocks: row.blocks as Prompt["blocks"],
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export class PromptSupabaseStore implements PromptStore {
  async list(): Promise<Prompt[]> {
    const supabase = getAdminSupabase();
    const { data, error } = await supabase
      .from("prompts")
      .select("id,name,tags,blocks,created_at,updated_at")
      .order("created_at", { ascending: true });
    if (error) throw error;
    return (data as DbPromptRow[]).map(mapRowToPrompt);
  }

  async getById(id: string): Promise<Prompt | undefined> {
    const supabase = getAdminSupabase();
    const { data, error } = await supabase
      .from("prompts")
      .select("id,name,tags,blocks,created_at,updated_at")
      .eq("id", id)
      .maybeSingle();
    if (error) throw error;
    if (!data) return undefined;
    return mapRowToPrompt(data as DbPromptRow);
  }

  async create(input: PromptCreateInput): Promise<Prompt> {
    const supabase = getAdminSupabase();
    const insertPayload = {
      name: input.name,
      tags: input.tags,
      blocks: input.blocks as unknown,
    };
    const { data, error } = await supabase
      .from("prompts")
      .insert(insertPayload)
      .select("id,name,tags,blocks,created_at,updated_at")
      .single();
    if (error) throw error;
    return mapRowToPrompt(data as DbPromptRow);
  }

  async update(input: PromptUpdateInput): Promise<Prompt | undefined> {
    const supabase = getAdminSupabase();
    const updates: Partial<DbPromptRow> = {};
    if (input.name !== undefined) updates.name = input.name;
    if (input.tags !== undefined) updates.tags = input.tags;
    if (input.blocks !== undefined)
      (updates as { blocks: unknown }).blocks = input.blocks as unknown;

    const { data, error } = await supabase
      .from("prompts")
      .update(updates)
      .eq("id", input.id)
      .select("id,name,tags,blocks,created_at,updated_at")
      .maybeSingle();
    if (error) throw error;
    if (!data) return undefined;
    return mapRowToPrompt(data as DbPromptRow);
  }

  async delete(id: string): Promise<boolean> {
    const supabase = getAdminSupabase();
    const { error, count } = await supabase
      .from("prompts")
      .delete({ count: "exact" })
      .eq("id", id);
    if (error) throw error;
    return (count ?? 0) > 0;
  }

  async clear(): Promise<void> {
    const supabase = getAdminSupabase();
    const { error } = await supabase
      .from("prompts")
      .delete()
      .gt("created_at", "1970-01-01");
    if (error) throw error;
  }
}

export const promptSupabaseStore = new PromptSupabaseStore();

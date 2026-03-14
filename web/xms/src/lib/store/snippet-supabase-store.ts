import { getAdminSupabase } from "@/lib/supabase";
import type { Snippet } from "@/types/snippet";
import type {
  SnippetCreateInput,
  SnippetStore,
  SnippetUpdateInput,
} from "@/types/snippet-store";

type DbSnippetRow = {
  id: string;
  name: string;
  body: string;
  tags: string[];
  word_count: number;
  used_in_prompts: number;
  created_at: string;
  updated_at: string;
};

function mapRowToSnippet(row: DbSnippetRow): Snippet {
  return {
    id: row.id,
    name: row.name,
    body: row.body,
    tags: row.tags,
    wordCount: row.word_count,
    usedInPrompts: row.used_in_prompts,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export class SnippetSupabaseStore implements SnippetStore {
  async list(): Promise<Snippet[]> {
    const supabase = getAdminSupabase();
    const { data, error } = await supabase
      .from("snippets")
      .select("id,name,body,tags,word_count,used_in_prompts,created_at,updated_at")
      .order("created_at", { ascending: true });
    if (error) throw error;
    return (data as DbSnippetRow[]).map(mapRowToSnippet);
  }

  async getById(id: string): Promise<Snippet | undefined> {
    const supabase = getAdminSupabase();
    const { data, error } = await supabase
      .from("snippets")
      .select("id,name,body,tags,word_count,used_in_prompts,created_at,updated_at")
      .eq("id", id)
      .maybeSingle();
    if (error) throw error;
    if (!data) return undefined;
    return mapRowToSnippet(data as DbSnippetRow);
  }

  async create(input: SnippetCreateInput): Promise<Snippet> {
    const supabase = getAdminSupabase();
    const wordCount = input.body.trim().split(/\s+/).filter(Boolean).length;
    const insertPayload = {
      name: input.name,
      body: input.body,
      tags: input.tags,
      word_count: wordCount,
      used_in_prompts: 0,
    };
    const { data, error } = await supabase
      .from("snippets")
      .insert(insertPayload)
      .select("id,name,body,tags,word_count,used_in_prompts,created_at,updated_at")
      .single();
    if (error) throw error;
    return mapRowToSnippet(data as DbSnippetRow);
  }

  async update(input: SnippetUpdateInput): Promise<Snippet | undefined> {
    const supabase = getAdminSupabase();
    const updates: Partial<DbSnippetRow> = {};
    let recomputeWordCount = false;
    if (input.name !== undefined) updates.name = input.name;
    if (input.body !== undefined) {
      updates.body = input.body;
      recomputeWordCount = true;
    }
    if (input.tags !== undefined) updates.tags = input.tags;

    if (recomputeWordCount) {
      const body = input.body ?? "";
      updates.word_count = body.trim().split(/\s+/).filter(Boolean).length;
    }

    const { data, error } = await supabase
      .from("snippets")
      .update(updates)
      .eq("id", input.id)
      .select("id,name,body,tags,word_count,used_in_prompts,created_at,updated_at")
      .maybeSingle();
    if (error) throw error;
    if (!data) return undefined;
    return mapRowToSnippet(data as DbSnippetRow);
  }

  async delete(id: string): Promise<boolean> {
    const supabase = getAdminSupabase();
    const { error, count } = await supabase
      .from("snippets")
      .delete({ count: "exact" })
      .eq("id", id);
    if (error) throw error;
    return (count ?? 0) > 0;
  }

  async clear(): Promise<void> {
    const supabase = getAdminSupabase();
    const { error } = await supabase
      .from("snippets")
      .delete()
      .gt("created_at", "1970-01-01");
    if (error) throw error;
  }
}

export const snippetSupabaseStore = new SnippetSupabaseStore();

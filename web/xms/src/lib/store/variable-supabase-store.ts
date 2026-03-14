import { getAdminSupabase } from "@/lib/supabase";
import type { Variable } from "@/types/variable";
import type {
  VariableCreateInput,
  VariableStore,
  VariableUpdateInput,
} from "@/types/variable-store";

type DbVariableRow = {
  id: string;
  name: string;
  type: Variable["type"];
  default_value: unknown;
  description: string;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
};

function mapRowToVariable(row: DbVariableRow): Variable {
  return {
    id: row.id,
    name: row.name,
    type: row.type,
    defaultValue: row.default_value as Variable["defaultValue"],
    description: row.description,
    tags: row.tags ?? undefined,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export class VariableSupabaseStore implements VariableStore {
  async list(): Promise<Variable[]> {
    const supabase = getAdminSupabase();
    const { data, error } = await supabase
      .from("variables")
      .select("id,name,type,default_value,description,tags,created_at,updated_at")
      .order("created_at", { ascending: true });
    if (error) throw error;
    return (data as DbVariableRow[]).map(mapRowToVariable);
  }

  async getById(id: string): Promise<Variable | undefined> {
    const supabase = getAdminSupabase();
    const { data, error } = await supabase
      .from("variables")
      .select("id,name,type,default_value,description,tags,created_at,updated_at")
      .eq("id", id)
      .maybeSingle();
    if (error) throw error;
    if (!data) return undefined;
    return mapRowToVariable(data as DbVariableRow);
  }

  async create(input: VariableCreateInput): Promise<Variable> {
    const supabase = getAdminSupabase();
    const insertPayload = {
      name: input.name,
      type: input.type,
      default_value: input.defaultValue as unknown,
      description: input.description,
      tags: input.tags ?? null,
    };
    const { data, error } = await supabase
      .from("variables")
      .insert(insertPayload)
      .select("id,name,type,default_value,description,tags,created_at,updated_at")
      .single();
    if (error) throw error;
    return mapRowToVariable(data as DbVariableRow);
  }

  async update(input: VariableUpdateInput): Promise<Variable | undefined> {
    const supabase = getAdminSupabase();
    const updates: Partial<DbVariableRow> = {};
    if (input.name !== undefined) updates.name = input.name;
    if (input.type !== undefined) updates.type = input.type;
    if (input.defaultValue !== undefined)
      updates.default_value = input.defaultValue as unknown;
    if (input.description !== undefined) updates.description = input.description;
    if (input.tags !== undefined) updates.tags = input.tags ?? null;

    const { data, error } = await supabase
      .from("variables")
      .update(updates)
      .eq("id", input.id)
      .select("id,name,type,default_value,description,tags,created_at,updated_at")
      .maybeSingle();
    if (error) throw error;
    if (!data) return undefined;
    return mapRowToVariable(data as DbVariableRow);
  }

  async delete(id: string): Promise<boolean> {
    const supabase = getAdminSupabase();
    const { error, count } = await supabase
      .from("variables")
      .delete({ count: "exact" })
      .eq("id", id);
    if (error) throw error;
    return (count ?? 0) > 0;
  }

  async clear(): Promise<void> {
    const supabase = getAdminSupabase();
    const { error } = await supabase
      .from("variables")
      .delete()
      .gt("created_at", "1970-01-01");
    if (error) throw error;
  }
}

export const variableSupabaseStore = new VariableSupabaseStore();

import type { Variable } from "@/types/variable";

export interface VariableCreateInput {
  name: string;
  type: Variable["type"];
  defaultValue: Variable["defaultValue"];
  description: string;
  tags?: string[];
}

export interface VariableUpdateInput {
  id: string;
  name?: string;
  type?: Variable["type"];
  defaultValue?: Variable["defaultValue"];
  description?: string;
  tags?: string[];
}

export interface VariableStore {
  list(): Promise<Variable[]>;
  getById(id: string): Promise<Variable | undefined>;
  create(input: VariableCreateInput): Promise<Variable>;
  update(input: VariableUpdateInput): Promise<Variable | undefined>;
  delete(id: string): Promise<boolean>;
  clear(): Promise<void>;
}

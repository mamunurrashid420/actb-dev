import type { BaseEntity } from "./common";

export type VariableType =
  | "text"
  | "enum"
  | "boolean"
  | "number"
  | "JSON"
  | "multiline";

export interface Variable extends BaseEntity {
  name: string;
  type: VariableType;
  defaultValue: string | number | boolean;
  description: string;
  tags?: string[];
  createdAt: string;
  updatedAt: string;
}

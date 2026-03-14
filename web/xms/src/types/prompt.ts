import type { BaseEntity } from "./common";

export type PromptBlock =
  | { type: "snippet"; snippetId: string }
  | { type: "text"; text: string };

export interface Prompt extends BaseEntity {
  name: string;
  tags: string[];
  blocks: PromptBlock[];
}

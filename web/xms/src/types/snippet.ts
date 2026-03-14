import type { BaseEntity } from "./common";

export interface Snippet extends BaseEntity {
  name: string;
  body: string;
  tags: string[];
  wordCount: number;
  usedInPrompts: number;
}

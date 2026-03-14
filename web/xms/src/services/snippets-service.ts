import { APIClient } from "@/lib/api-client";
import type { Snippet } from "@/types/snippet";

export class SnippetsService {
  private readonly client: APIClient;

  constructor(basePath: string = "/snippets") {
    this.client = new APIClient(basePath);
  }

  public getAll(): Promise<Snippet[]> {
    return this.client.get<Snippet[]>("");
  }

  public getById(id: string): Promise<Snippet> {
    return this.client.get<Snippet>(`?id=${encodeURIComponent(id)}`);
  }

  public create(
    input: Omit<
      Snippet,
      "id" | "createdAt" | "updatedAt" | "wordCount" | "usedInPrompts"
    >,
  ): Promise<Snippet> {
    return this.client.post<Snippet, typeof input>(input);
  }

  public update(
    input: Partial<
      Omit<Snippet, "createdAt" | "updatedAt" | "wordCount" | "usedInPrompts">
    > & { id: string },
  ): Promise<Snippet> {
    return this.client.put<Snippet, typeof input>(input);
  }

  public delete(id: string): Promise<{ ok: boolean }> {
    return this.client.delete<{ ok: boolean }>(`?id=${encodeURIComponent(id)}`);
  }
}

export const snippetsService = new SnippetsService();

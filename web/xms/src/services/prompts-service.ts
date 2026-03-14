import { APIClient } from "@/lib/api-client";
import type { Prompt } from "@/types/prompt";

export class PromptsService {
  private readonly client: APIClient;

  constructor(basePath: string = "/prompts") {
    this.client = new APIClient(basePath);
  }

  public getAll(): Promise<Prompt[]> {
    return this.client.get<Prompt[]>("");
  }

  public getById(id: string): Promise<Prompt> {
    return this.client.get<Prompt>(`?id=${encodeURIComponent(id)}`);
  }

  public create(
    input: Omit<Prompt, "id" | "createdAt" | "updatedAt">,
  ): Promise<Prompt> {
    return this.client.post<Prompt, typeof input>(input);
  }

  public update(
    input: Partial<Omit<Prompt, "createdAt" | "updatedAt">> & { id: string },
  ): Promise<Prompt> {
    return this.client.put<Prompt, typeof input>(input);
  }

  public delete(id: string): Promise<{ ok: boolean }> {
    return this.client.delete<{ ok: boolean }>(`?id=${encodeURIComponent(id)}`);
  }
}

export const promptsService = new PromptsService();

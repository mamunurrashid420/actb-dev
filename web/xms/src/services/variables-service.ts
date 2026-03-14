import { APIClient } from "@/lib/api-client";
import type { Variable } from "@/types/variable";

export class VariablesService {
  private readonly client: APIClient;

  constructor(basePath: string = "/variables") {
    this.client = new APIClient(basePath);
  }

  public getAll(): Promise<Variable[]> {
    return this.client.get<Variable[]>("");
  }

  public getById(id: string): Promise<Variable> {
    const query = `?id=${encodeURIComponent(id)}`;
    return this.client.get<Variable>(query);
  }

  public create(
    variable: Omit<Variable, "id" | "createdAt" | "updatedAt">,
  ): Promise<Variable> {
    return this.client.post<Variable, Omit<Variable, "id" | "createdAt" | "updatedAt">>(
      variable,
    );
  }

  public update(
    variable: Partial<Omit<Variable, "createdAt" | "updatedAt">> & {
      id: string;
    },
  ): Promise<Variable> {
    return this.client.put<
      Variable,
      Partial<Omit<Variable, "createdAt" | "updatedAt">> & { id: string }
    >(variable);
  }

  public delete(id: string): Promise<{ ok: boolean }> {
    const query = `?id=${encodeURIComponent(id)}`;
    return this.client.delete<{ ok: boolean }>(query);
  }
}

export const variablesService = new VariablesService();

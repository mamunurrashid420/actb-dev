/**
 * API Client for communicating with the Python FastAPI backend.
 *
 * This client handles authentication by attaching the Supabase JWT token
 * to all requests.
 */

import { getBrowserSupabase } from "@/lib/supabase/client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface APIError {
  detail: string;
  status: number;
}

export class APIClient {
  private basePath: string;

  constructor(basePath: string) {
    this.basePath = basePath;
  }

  private async getAuthHeaders(): Promise<HeadersInit> {
    const supabase = getBrowserSupabase();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    if (session?.access_token) {
      headers["Authorization"] = `Bearer ${session.access_token}`;
    }

    return headers;
  }

  private async request<T>(
    method: string,
    path: string = "",
    body?: unknown
  ): Promise<T> {
    const url = `${API_BASE_URL}${this.basePath}${path}`;
    const headers = await this.getAuthHeaders();

    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error: APIError = {
        detail: "Request failed",
        status: response.status,
      };
      try {
        const data = await response.json();
        error.detail = data.detail || data.error || "Request failed";
      } catch {
        // Ignore JSON parse errors
      }
      throw error;
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  public async get<T>(path: string = ""): Promise<T> {
    return this.request<T>("GET", path);
  }

  public async post<T, B = unknown>(body: B, path: string = ""): Promise<T> {
    return this.request<T>("POST", path, body);
  }

  public async put<T, B = unknown>(body: B, path: string = ""): Promise<T> {
    return this.request<T>("PUT", path, body);
  }

  public async delete<T>(path: string = ""): Promise<T> {
    return this.request<T>("DELETE", path);
  }
}

// Pre-configured clients for each entity
export const usersApi = new APIClient("/users");
export const tenantsApi = new APIClient("/tenants");
export const conversationsApi = new APIClient("/conversations");
export const promptsApi = new APIClient("/prompts");
export const snippetsApi = new APIClient("/snippets");
export const variablesApi = new APIClient("/variables");

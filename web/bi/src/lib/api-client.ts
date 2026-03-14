/**
 * API Client for communicating with the Python FastAPI backend.
 *
 * Attaches the access token stored in cookies for browser requests.
 */

import { API_BASE_URL } from "@/lib/auth/constants";
import { getBrowserAccessToken } from "@/lib/auth/browser";

export interface APIError {
  detail: string;
  status: number;
}

export class APIClientError extends Error implements APIError {
  detail: string;
  status: number;

  constructor(detail: string, status: number) {
    super(detail);
    this.name = "APIClientError";
    this.detail = detail;
    this.status = status;
  }
}

export class APIClient {
  private basePath: string;

  constructor(basePath: string) {
    this.basePath = basePath;
  }

  private getAuthHeaders(): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    const token = getBrowserAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    return headers;
  }

  private async request<T>(
    method: string,
    path: string = "",
    body?: unknown,
  ): Promise<T> {
    const url = `${API_BASE_URL}${this.basePath}${path}`;
    const headers = this.getAuthHeaders();

    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      let detail = "Request failed";
      try {
        const data = await response.json();
        detail = data.detail || data.error || detail;
      } catch {
        // Ignore JSON parse errors
      }
      throw new APIClientError(detail, response.status);
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
export const rolesApi = new APIClient("/roles");
export const permissionsApi = new APIClient("/permissions");

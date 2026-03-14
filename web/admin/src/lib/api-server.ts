import { API_BASE_URL } from "@/lib/auth/constants";
import { getAccessToken } from "@/lib/auth/session";

export interface APIError extends Error {
  status: number;
  detail: string;
}

async function buildError(response: Response): Promise<APIError> {
  const error = new Error("Request failed") as APIError;
  error.status = response.status;
  error.detail = "Request failed";
  try {
    const data = await response.json();
    error.detail = data.detail || data.error || error.detail;
  } catch {
    // ignore
  }
  return error;
}

export async function apiServerRequest<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const token = await getAccessToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    throw await buildError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

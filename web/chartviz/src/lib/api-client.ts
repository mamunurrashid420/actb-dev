/**
 * API Client for the playground viz_designer endpoint.
 *
 * No authentication required (playground-only endpoint).
 */

// ---------------------------------------------------------------------------
// Request / Response types (mirrors Pydantic schemas in
// service/src/app/api/playground/viz_designer/schema.py)
// ---------------------------------------------------------------------------

export interface VisualizationCreateRequest {
  nlp_query: string;
  output_schema: Record<string, unknown>;
  materialized_data: Record<string, unknown>[];
  conversation_id?: string | null;
  model?: string | null;
  tenant_id?: string;
  user_id?: string;
}

export interface VisualizationCreateResponse {
  chart_id: string;
  data_slice_id: string;
  conversation_id: string;
  chart_spec: Record<string, unknown>;
  data: Record<string, unknown>;
  highlights: Record<string, unknown>[];
  insights: Record<string, unknown>[];
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

const DEFAULT_API_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  return (
    (typeof window !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
    DEFAULT_API_URL
  );
}

export async function createVisualization(
  request: VisualizationCreateRequest,
  apiBaseUrl?: string,
): Promise<VisualizationCreateResponse> {
  const base = apiBaseUrl ?? getApiBaseUrl();
  const url = `${base}/playground/viz_designer/create`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let detail = "Request failed";
    try {
      const data = await response.json();
      detail = data.detail ?? data.error ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new Error(`API ${response.status}: ${detail}`);
  }

  return response.json();
}

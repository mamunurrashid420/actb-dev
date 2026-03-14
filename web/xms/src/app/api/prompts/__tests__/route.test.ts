/**
 * Unit tests for in-memory prompts CRUD API
 */

// Mock next/server to provide NextResponse.json
jest.mock("next/server", () => {
  const NextResponse = {
    json: (data: unknown, init?: ResponseInit) =>
      new Response(JSON.stringify(data), {
        status: init?.status ?? 200,
        headers: {
          "content-type": "application/json",
          ...(init?.headers || {}),
        },
      }),
  };
  return { NextResponse };
});

import { GET, POST, PUT, DELETE, __promptsStore } from "../route";
import type { NextRequest } from "next/server";
import type { Prompt } from "@/types/prompt";

type MockedRequest = {
  url: string;
  method?: string;
  json: () => Promise<unknown>;
};

function makeReq(url: string, method: string = "GET", body?: unknown): NextRequest {
  const req: MockedRequest = { url, method, json: async () => body };
  return req as unknown as NextRequest;
}

beforeEach(() => {
  __promptsStore.clear();
});

interface DeleteResponseBody {
  ok: boolean;
}

describe("/api/prompts CRUD", () => {
  it("creates a prompt and lists it", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/prompts", "POST", {
        name: "P1",
        tags: ["t"],
        blocks: [{ type: "text", text: "hello" }],
      }),
    );
    expect(resCreate.status).toBe(201);
    const created = (await resCreate.json()) as Prompt;
    expect(created.id).toBeTruthy();
    expect(created.name).toBe("P1");

    const resList = await GET(makeReq("http://localhost/api/prompts"));
    expect(resList.status).toBe(200);
    const list = (await resList.json()) as Prompt[];
    expect(list.find((p) => p.id === created.id)).toBeTruthy();
  });

  it("reads a prompt by id", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/prompts", "POST", {
        name: "A",
        tags: [],
        blocks: [],
      }),
    );
    const created = (await resCreate.json()) as Prompt;

    const resGet = await GET(makeReq(`http://localhost/api/prompts?id=${created.id}`));
    expect(resGet.status).toBe(200);
    const got = (await resGet.json()) as Prompt;
    expect(got.id).toBe(created.id);
  });

  it("updates a prompt", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/prompts", "POST", {
        name: "K",
        tags: [],
        blocks: [],
      }),
    );
    const created = (await resCreate.json()) as Prompt;

    const resUpdate = await PUT(
      makeReq("http://localhost/api/prompts", "PUT", {
        id: created.id,
        name: "K2",
      }),
    );
    expect(resUpdate.status).toBe(200);
    const updated = (await resUpdate.json()) as Prompt;
    expect(updated.name).toBe("K2");
    expect(new Date(updated.updatedAt!).getTime()).toBeGreaterThanOrEqual(
      new Date(created.updatedAt!).getTime(),
    );
  });

  it("deletes a prompt", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/prompts", "POST", {
        name: "T",
        tags: [],
        blocks: [],
      }),
    );
    const created = (await resCreate.json()) as Prompt;

    const resDel = await DELETE(
      makeReq(`http://localhost/api/prompts?id=${created.id}`, "DELETE"),
    );
    expect(resDel.status).toBe(200);
    const delBody = (await resDel.json()) as DeleteResponseBody;
    expect(delBody.ok).toBe(true);

    const resGet = await GET(makeReq(`http://localhost/api/prompts?id=${created.id}`));
    expect(resGet.status).toBe(404);
  });

  it("handles bad requests and not-found cases", async () => {
    const resBadCreate = await POST(
      makeReq("http://localhost/api/prompts", "POST", {}),
    );
    expect(resBadCreate.status).toBe(400);

    const resUpdateMissing = await PUT(
      makeReq("http://localhost/api/prompts", "PUT", { id: "nope", name: "x" }),
    );
    expect(resUpdateMissing.status).toBe(404);

    const resDelMissingId = await DELETE(
      makeReq("http://localhost/api/prompts", "DELETE"),
    );
    expect(resDelMissingId.status).toBe(400);
  });
});

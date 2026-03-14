/**
 * Unit tests for in-memory snippets CRUD API
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

import { GET, POST, PUT, DELETE, __snippetsStore } from "../route";
import type { NextRequest } from "next/server";
import type { Snippet } from "@/types/snippet";

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
  __snippetsStore.clear();
});

interface DeleteResponseBody {
  ok: boolean;
}

describe("/api/snippets CRUD", () => {
  it("creates a snippet and lists it", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/snippets", "POST", {
        name: "Welcome",
        body: "Hello @name!",
        tags: ["email"],
      }),
    );
    expect(resCreate.status).toBe(201);
    const created = (await resCreate.json()) as Snippet;
    expect(created.id).toBeTruthy();
    expect(created.name).toBe("Welcome");
    expect(created.body).toBe("Hello @name!");
    expect(created.tags).toEqual(["email"]);
    expect(created.wordCount).toBe(2);

    const resList = await GET(makeReq("http://localhost/api/snippets"));
    expect(resList.status).toBe(200);
    const list = (await resList.json()) as Snippet[];
    expect(list.find((s) => s.id === created.id)).toBeTruthy();
  });

  it("reads a snippet by id", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/snippets", "POST", {
        name: "Greeting",
        body: "Hi there",
        tags: [],
      }),
    );
    const created = (await resCreate.json()) as Snippet;

    const resGet = await GET(makeReq(`http://localhost/api/snippets?id=${created.id}`));
    expect(resGet.status).toBe(200);
    const got = (await resGet.json()) as Snippet;
    expect(got.id).toBe(created.id);
    expect(got.name).toBe("Greeting");
  });

  it("updates a snippet", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/snippets", "POST", {
        name: "Original",
        body: "Original body",
        tags: [],
      }),
    );
    const created = (await resCreate.json()) as Snippet;

    const resUpdate = await PUT(
      makeReq("http://localhost/api/snippets", "PUT", {
        id: created.id,
        name: "Updated",
        body: "Updated body text here",
      }),
    );
    expect(resUpdate.status).toBe(200);
    const updated = (await resUpdate.json()) as Snippet;
    expect(updated.name).toBe("Updated");
    expect(updated.body).toBe("Updated body text here");
    expect(updated.wordCount).toBe(4);
    expect(new Date(updated.updatedAt!).getTime()).toBeGreaterThanOrEqual(
      new Date(created.updatedAt!).getTime(),
    );
  });

  it("deletes a snippet", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/snippets", "POST", {
        name: "ToDelete",
        body: "temp",
        tags: [],
      }),
    );
    const created = (await resCreate.json()) as Snippet;

    const resDel = await DELETE(
      makeReq(`http://localhost/api/snippets?id=${created.id}`, "DELETE"),
    );
    expect(resDel.status).toBe(200);
    const delBody = (await resDel.json()) as DeleteResponseBody;
    expect(delBody.ok).toBe(true);

    const resGet = await GET(makeReq(`http://localhost/api/snippets?id=${created.id}`));
    expect(resGet.status).toBe(404);
  });

  it("handles bad requests and not-found cases", async () => {
    const resBadCreate = await POST(
      makeReq("http://localhost/api/snippets", "POST", {}),
    );
    expect(resBadCreate.status).toBe(400);

    const resUpdateMissing = await PUT(
      makeReq("http://localhost/api/snippets", "PUT", { id: "nope", name: "x" }),
    );
    expect(resUpdateMissing.status).toBe(404);

    const resDelMissingId = await DELETE(
      makeReq("http://localhost/api/snippets", "DELETE"),
    );
    expect(resDelMissingId.status).toBe(400);

    const resGetMissing = await GET(
      makeReq("http://localhost/api/snippets?id=nonexistent"),
    );
    expect(resGetMissing.status).toBe(404);
  });
});

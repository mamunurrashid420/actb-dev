/**
 * Unit tests for in-memory variables CRUD API
 */

// Mock next/server to avoid ESM/runtime coupling and provide NextResponse.json
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

import { GET, POST, PUT, DELETE, __variablesStore } from "../route";

import type { NextRequest } from "next/server";

type MockedRequest = {
  url: string;
  method?: string;
  json: () => Promise<unknown>;
};

function makeReq(url: string, method: string = "GET", body?: unknown): NextRequest {
  const req: MockedRequest = {
    url,
    method,
    json: async () => body,
  };
  return req as unknown as NextRequest;
}

beforeEach(() => {
  __variablesStore.clear();
});

import type { Variable } from "@/types/variable";

interface DeleteResponseBody {
  ok: boolean;
}

describe("/api/variables CRUD", () => {
  it("creates a variable and lists it", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/variables", "POST", {
        name: "FOO",
        type: "text",
        defaultValue: "bar",
        description: "Foo bar var",
      }),
    );
    expect(resCreate.status).toBe(201);
    const created = (await resCreate.json()) as Variable;
    expect(created.id).toBeTruthy();
    expect(created.name).toBe("FOO");
    expect(created.type).toBe("text");
    expect(created.defaultValue).toBe("bar");
    expect(created.description).toBe("Foo bar var");

    const resList = await GET(makeReq("http://localhost/api/variables"));
    expect(resList.status).toBe(200);
    const list = (await resList.json()) as Variable[];
    expect(Array.isArray(list)).toBe(true);
    expect(list.length).toBe(1);
    expect(list[0].id).toBe(created.id);
  });

  it("reads a variable by id", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/variables", "POST", {
        name: "A",
        type: "text",
        defaultValue: "1",
        description: "A var",
      }),
    );
    const created = (await resCreate.json()) as Variable;

    const resGet = await GET(
      makeReq(`http://localhost/api/variables?id=${created.id}`),
    );
    expect(resGet.status).toBe(200);
    const got = (await resGet.json()) as Variable;
    expect(got.id).toBe(created.id);
    expect(got.name).toBe("A");
    expect(got.defaultValue).toBe("1");
  });

  it("updates a variable", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/variables", "POST", {
        name: "K",
        type: "text",
        defaultValue: "old",
        description: "K var",
      }),
    );
    const created = (await resCreate.json()) as Variable;

    const resUpdate = await PUT(
      makeReq("http://localhost/api/variables", "PUT", {
        id: created.id,
        defaultValue: "new",
      }),
    );
    expect(resUpdate.status).toBe(200);
    const updated = (await resUpdate.json()) as Variable;
    expect(updated.id).toBe(created.id);
    expect(updated.name).toBe("K");
    expect(updated.defaultValue).toBe("new");
    expect(new Date(updated.updatedAt!).getTime()).toBeGreaterThanOrEqual(
      new Date(created.updatedAt!).getTime(),
    );
  });

  it("deletes a variable", async () => {
    const resCreate = await POST(
      makeReq("http://localhost/api/variables", "POST", {
        name: "T",
        type: "text",
        defaultValue: "tmp",
        description: "T var",
      }),
    );
    const created = (await resCreate.json()) as Variable;

    const resDel = await DELETE(
      makeReq(`http://localhost/api/variables?id=${created.id}`, "DELETE"),
    );
    expect(resDel.status).toBe(200);
    const delBody = (await resDel.json()) as DeleteResponseBody;
    expect(delBody.ok).toBe(true);

    const resGet = await GET(
      makeReq(`http://localhost/api/variables?id=${created.id}`),
    );
    expect(resGet.status).toBe(404);
  });

  it("handles bad requests and not-found cases", async () => {
    const resBadCreate = await POST(
      makeReq("http://localhost/api/variables", "POST", {}),
    );
    expect(resBadCreate.status).toBe(400);

    const resUpdateMissing = await PUT(
      makeReq("http://localhost/api/variables", "PUT", {
        id: "nope",
        value: "x",
      }),
    );
    expect(resUpdateMissing.status).toBe(404);

    const resDelMissingId = await DELETE(
      makeReq("http://localhost/api/variables", "DELETE"),
    );
    expect(resDelMissingId.status).toBe(400);
  });

  it("creates JSON and multiline variables", async () => {
    const resJson = await POST(
      makeReq("http://localhost/api/variables", "POST", {
        name: "cfg",
        type: "JSON",
        defaultValue: '{"a":1}',
        description: "json",
      }),
    );
    expect(resJson.status).toBe(201);
    const vjson = (await resJson.json()) as Variable;
    expect(vjson.type).toBe("JSON");
    expect(vjson.defaultValue).toBe('{"a":1}');

    const resMulti = await POST(
      makeReq("http://localhost/api/variables", "POST", {
        name: "para",
        type: "multiline",
        defaultValue: "line1\nline2",
        description: "ml",
      }),
    );
    expect(resMulti.status).toBe(201);
    const vm = (await resMulti.json()) as Variable;
    expect(vm.type).toBe("multiline");
    expect(vm.defaultValue).toBe("line1\nline2");
  });
});

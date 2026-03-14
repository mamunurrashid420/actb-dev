import type { Snippet } from "@/types/snippet";

// Mock the APIClient module before any imports that use it
jest.mock("@/lib/api-client", () => {
  const mockGet = jest.fn();
  const mockPost = jest.fn();
  const mockPut = jest.fn();
  const mockDelete = jest.fn();

  return {
    APIClient: jest.fn().mockImplementation(() => ({
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
    })),
    __mocks: { mockGet, mockPost, mockPut, mockDelete },
  };
});

// Import after mock is set up
import { SnippetsService } from "@/services/snippets-service";
import { APIClient, __mocks } from "@/lib/api-client";

const { mockGet, mockPost, mockPut, mockDelete } = __mocks as {
  mockGet: jest.Mock;
  mockPost: jest.Mock;
  mockPut: jest.Mock;
  mockDelete: jest.Mock;
};

describe("SnippetsService", () => {
  let service: SnippetsService;

  beforeEach(() => {
    jest.clearAllMocks();
    service = new SnippetsService("/snippets");
  });

  const sample = (overrides: Partial<Snippet> = {}): Snippet => ({
    id: "s1",
    name: "Welcome",
    body: "Hello @name",
    tags: ["email"],
    wordCount: 2,
    usedInPrompts: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  });

  it("getAll returns snippets", async () => {
    const data = [sample(), sample({ id: "s2" })];
    mockGet.mockResolvedValueOnce(data);
    const res = await service.getAll();
    expect(mockGet).toHaveBeenCalledWith("");
    expect(res).toEqual(data);
  });

  it("getById queries with id param", async () => {
    const s = sample();
    mockGet.mockResolvedValueOnce(s);
    const res = await service.getById("s1");
    expect(mockGet).toHaveBeenCalledWith("?id=s1");
    expect(res).toEqual(s);
  });

  it("create posts payload and returns created entity", async () => {
    const input = { name: "Welcome", body: "Hi", tags: [] as string[] };
    const created = sample({ id: "s-new", ...input });
    mockPost.mockResolvedValueOnce(created);
    const res = await service.create(input);
    expect(mockPost).toHaveBeenCalledWith(input);
    expect(res).toEqual(created);
  });

  it("update puts payload and returns updated entity", async () => {
    const update = { id: "s1", name: "Welcome 2" };
    const updated = sample({ ...update });
    mockPut.mockResolvedValueOnce(updated);
    const res = await service.update(update);
    expect(mockPut).toHaveBeenCalledWith(update);
    expect(res).toEqual(updated);
  });

  it("delete removes entity and returns ok", async () => {
    const ok = { ok: true };
    mockDelete.mockResolvedValueOnce(ok);
    const res = await service.delete("s1");
    expect(mockDelete).toHaveBeenCalledWith("?id=s1");
    expect(res).toEqual(ok);
  });
});

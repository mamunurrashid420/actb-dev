import type { Prompt } from "@/types/prompt";

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
import { PromptsService } from "@/services/prompts-service";
import { APIClient, __mocks } from "@/lib/api-client";

const { mockGet, mockPost, mockPut, mockDelete } = __mocks as {
  mockGet: jest.Mock;
  mockPost: jest.Mock;
  mockPut: jest.Mock;
  mockDelete: jest.Mock;
};

describe("PromptsService", () => {
  let service: PromptsService;

  beforeEach(() => {
    jest.clearAllMocks();
    service = new PromptsService("/prompts");
  });

  const sample = (overrides: Partial<Prompt> = {}): Prompt => ({
    id: "p1",
    name: "Welcome Flow",
    tags: ["email"],
    blocks: [
      { type: "snippet", snippetId: "s1" },
      { type: "text", text: "\n\nThanks!" },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  });

  it("getAll returns prompts", async () => {
    const data = [sample(), sample({ id: "p2" })];
    mockGet.mockResolvedValueOnce(data);
    const res = await service.getAll();
    expect(mockGet).toHaveBeenCalledWith("");
    expect(res).toEqual(data);
  });

  it("getById queries with id param", async () => {
    const p = sample();
    mockGet.mockResolvedValueOnce(p);
    const res = await service.getById("p1");
    expect(mockGet).toHaveBeenCalledWith("?id=p1");
    expect(res).toEqual(p);
  });

  it("create posts payload and returns created entity", async () => {
    const input = {
      name: "Welcome Flow",
      tags: [],
      blocks: [] as Prompt["blocks"],
    };
    const created = sample({ id: "p-new", ...input });
    mockPost.mockResolvedValueOnce(created);
    const res = await service.create(input);
    expect(mockPost).toHaveBeenCalledWith(input);
    expect(res).toEqual(created);
  });

  it("update puts payload and returns updated entity", async () => {
    const update = { id: "p1", name: "Welcome Flow v2" };
    const updated = sample({ ...update });
    mockPut.mockResolvedValueOnce(updated);
    const res = await service.update(update);
    expect(mockPut).toHaveBeenCalledWith(update);
    expect(res).toEqual(updated);
  });

  it("delete removes entity and returns ok", async () => {
    const ok = { ok: true };
    mockDelete.mockResolvedValueOnce(ok);
    const res = await service.delete("p1");
    expect(mockDelete).toHaveBeenCalledWith("?id=p1");
    expect(res).toEqual(ok);
  });
});

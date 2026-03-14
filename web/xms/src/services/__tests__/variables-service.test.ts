import type { Variable } from "@/types/variable";

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
import { VariablesService } from "@/services/variables-service";
import { APIClient, __mocks } from "@/lib/api-client";

const { mockGet, mockPost, mockPut, mockDelete } = __mocks as {
  mockGet: jest.Mock;
  mockPost: jest.Mock;
  mockPut: jest.Mock;
  mockDelete: jest.Mock;
};

describe("VariablesService", () => {
  let service: VariablesService;

  beforeEach(() => {
    jest.clearAllMocks();
    service = new VariablesService("/variables");
  });

  const sampleVar = (overrides: Partial<Variable> = {}): Variable => ({
    id: "id1",
    name: "foo",
    type: "text",
    defaultValue: "bar",
    description: "desc",
    tags: ["t1"],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  });

  it("getAll returns variables", async () => {
    const data = [sampleVar(), sampleVar({ id: "id2" })];
    mockGet.mockResolvedValueOnce(data);
    const res = await service.getAll();
    expect(mockGet).toHaveBeenCalledWith("");
    expect(res).toEqual(data);
  });

  it("getById queries with id param", async () => {
    const v = sampleVar();
    mockGet.mockResolvedValueOnce(v);
    const res = await service.getById("id1");
    expect(mockGet).toHaveBeenCalledWith("?id=id1");
    expect(res).toEqual(v);
  });

  it("create posts payload and returns created entity", async () => {
    const input = {
      name: "foo",
      type: "text" as const,
      defaultValue: "bar",
      description: "desc",
      tags: ["t1"],
    };
    const created = sampleVar({ id: "id-new", ...input });
    mockPost.mockResolvedValueOnce(created);
    const res = await service.create(input);
    expect(mockPost).toHaveBeenCalledWith(input);
    expect(res).toEqual(created);
  });

  it("update puts payload and returns updated entity", async () => {
    const update = { id: "id1", name: "foo2" };
    const updated = sampleVar({ ...update });
    mockPut.mockResolvedValueOnce(updated);
    const res = await service.update(update);
    expect(mockPut).toHaveBeenCalledWith(update);
    expect(res).toEqual(updated);
  });

  it("delete removes entity and returns ok", async () => {
    const ok = { ok: true };
    mockDelete.mockResolvedValueOnce(ok);
    const res = await service.delete("id1");
    expect(mockDelete).toHaveBeenCalledWith("?id=id1");
    expect(res).toEqual(ok);
  });
});

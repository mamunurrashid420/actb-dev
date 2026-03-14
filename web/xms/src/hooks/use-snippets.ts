import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { snippetsService } from "@/services/snippets-service";
import type { Snippet } from "@/types/snippet";

const keys = {
  all: ["snippets"] as const,
  byId: (id: string) => ["snippets", id] as const,
};

export function useSnippets() {
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: keys.all,
    queryFn: () => snippetsService.getAll(),
  });

  const createMutation = useMutation({
    mutationFn: (
      input: Omit<
        Snippet,
        "id" | "createdAt" | "updatedAt" | "wordCount" | "usedInPrompts"
      >,
    ) => snippetsService.create(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all }),
  });

  const updateMutation = useMutation({
    mutationFn: (
      input: Partial<
        Omit<Snippet, "createdAt" | "updatedAt" | "wordCount" | "usedInPrompts">
      > & { id: string },
    ) => snippetsService.update(input),
    onSuccess: (data) => {
      qc.setQueryData(keys.byId(data.id), data);
      qc.invalidateQueries({ queryKey: keys.all });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => snippetsService.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all }),
  });

  return {
    listQuery,
    createSnippet: createMutation.mutateAsync,
    updateSnippet: updateMutation.mutateAsync,
    deleteSnippet: deleteMutation.mutateAsync,
  };
}

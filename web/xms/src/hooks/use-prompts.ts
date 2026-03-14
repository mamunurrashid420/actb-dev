import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { promptsService } from "@/services/prompts-service";
import type { Prompt } from "@/types/prompt";

const queryKeys = {
  all: ["prompts"] as const,
  byId: (id: string) => ["prompts", id] as const,
};

export function usePrompts() {
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: queryKeys.all,
    queryFn: () => promptsService.getAll(),
  });

  const createMutation = useMutation({
    mutationFn: (input: Omit<Prompt, "id" | "createdAt" | "updatedAt">) =>
      promptsService.create(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.all }),
  });

  const updateMutation = useMutation({
    mutationFn: (
      input: Partial<Omit<Prompt, "createdAt" | "updatedAt">> & { id: string },
    ) => promptsService.update(input),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.byId(data.id), data);
      qc.invalidateQueries({ queryKey: queryKeys.all });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => promptsService.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.all }),
  });

  return {
    listQuery,
    createPrompt: createMutation.mutateAsync,
    updatePrompt: updateMutation.mutateAsync,
    deletePrompt: deleteMutation.mutateAsync,
  };
}

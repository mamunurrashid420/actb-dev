import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { variablesService } from "@/services/variables-service";
import type { Variable } from "@/types/variable";

const queryKeys = {
  all: ["variables"] as const,
  byId: (id: string) => ["variables", id] as const,
};

export function useVariables() {
  const qc = useQueryClient();

  const variablesQuery = useQuery({
    queryKey: queryKeys.all,
    queryFn: () => variablesService.getAll(),
  });

  const createMutation = useMutation({
    mutationFn: (input: Omit<Variable, "id" | "createdAt" | "updatedAt">) =>
      variablesService.create(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.all });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (
      input: Partial<Omit<Variable, "createdAt" | "updatedAt">> & { id: string },
    ) => variablesService.update(input),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.byId(data.id), data);
      qc.invalidateQueries({ queryKey: queryKeys.all });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => variablesService.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.all });
    },
  });

  return {
    variablesQuery,
    createVariable: createMutation.mutateAsync,
    updateVariable: updateMutation.mutateAsync,
    deleteVariable: deleteMutation.mutateAsync,
  };
}

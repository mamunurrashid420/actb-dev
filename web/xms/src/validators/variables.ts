import { z } from "zod";

export const variableTypeEnum = z.enum(
  ["text", "enum", "boolean", "number", "JSON", "multiline"],
  {
    required_error: "type is required",
  },
);

export const createVariableSchema = z.object({
  name: z.string().trim().min(1, "name is required"),
  type: variableTypeEnum,
  defaultValue: z.union([z.string(), z.number(), z.boolean()], {
    required_error: "defaultValue is required",
  }),
  description: z.string().trim().min(1, "description is required"),
  tags: z.array(z.string().trim()).optional(),
});

export const updateVariableSchema = createVariableSchema.partial().extend({
  id: z.string().trim().min(1, "id is required"),
});

export type CreateVariableInput = z.infer<typeof createVariableSchema>;
export type UpdateVariableInput = z.infer<typeof updateVariableSchema>;

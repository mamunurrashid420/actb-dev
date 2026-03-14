import { z } from "zod";

const promptBlockSchema = z.union([
  z.object({ type: z.literal("snippet"), snippetId: z.string().trim().min(1) }),
  z.object({ type: z.literal("text"), text: z.string() }),
]);

export const createPromptSchema = z.object({
  name: z.string().trim().min(1, "name is required"),
  tags: z.array(z.string().trim()).default([]),
  blocks: z.array(promptBlockSchema).default([]),
});

export const updatePromptSchema = z
  .object({
    id: z.string().trim().min(1, "id is required"),
    name: z.string().trim().min(1).optional(),
    tags: z.array(z.string().trim()).optional(),
    blocks: z.array(promptBlockSchema).optional(),
  })
  .strict();

export type CreatePromptInput = z.infer<typeof createPromptSchema>;
export type UpdatePromptInput = z.infer<typeof updatePromptSchema>;

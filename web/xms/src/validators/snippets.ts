import { z } from "zod";

export const createSnippetSchema = z.object({
  name: z.string().trim().min(1, "name is required"),
  body: z.string(),
  tags: z.array(z.string().trim().min(1)).default([]),
});

export const updateSnippetSchema = z
  .object({
    id: z.string().trim().min(1, "id is required"),
    name: z.string().trim().min(1).optional(),
    body: z.string().optional(),
    tags: z.array(z.string().trim().min(1)).optional(),
  })
  .strict();

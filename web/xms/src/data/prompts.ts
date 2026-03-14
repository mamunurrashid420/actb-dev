import type { Prompt } from "@/types/prompt";

export const mockPrompts: Prompt[] = [
  {
    id: "1",
    name: "Customer Onboarding Email",
    tags: ["email", "onboarding", "customer"],
    blocks: [
      { type: "snippet", snippetId: "1" },
      {
        type: "text",
        text: "\n\nNext steps:\n1. Complete your profile\n2. Explore our features\n3. Contact support if needed",
      },
      { type: "snippet", snippetId: "2" },
    ],
    createdAt: "2024-01-10",
    updatedAt: "2024-01-15",
  },
  {
    id: "2",
    name: "Support Ticket Response",
    tags: ["support", "response"],
    blocks: [
      { type: "snippet", snippetId: "3" },
      {
        type: "text",
        text: "\n\nIn the meantime, you can check our FAQ or knowledge base for common solutions.",
      },
    ],
    createdAt: "2024-01-09",
    updatedAt: "2024-01-14",
  },
];

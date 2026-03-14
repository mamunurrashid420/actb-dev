import type { Snippet } from "@/types/snippet";

export const mockSnippets: Snippet[] = [
  {
    id: "1",
    name: "Welcome Email",
    body: "Hi @customer_name,\n\nWelcome to our platform! We're excited to have you on board.\n\nYour account type: @is_premium_user\nTotal orders: @order_count\n\nBest regards,\nThe Team",
    tags: ["email", "welcome", "customer"],
    updatedAt: "2024-01-15",
    createdAt: "2024-01-10",
    wordCount: 28,
    usedInPrompts: 3,
  },
  {
    id: "2",
    name: "Product Recommendation",
    body: "Based on your interest in @product_category, we think you'll love these new arrivals:\n\n- Premium headphones\n- Smart watches\n- Wireless chargers\n\nShop now and get 20% off!",
    tags: ["product", "recommendation", "marketing"],
    updatedAt: "2024-01-14",
    createdAt: "2024-01-09",
    wordCount: 32,
    usedInPrompts: 1,
  },
  {
    id: "3",
    name: "Support Response",
    body: "Hello @customer_name,\n\nThank you for contacting our support team. We've received your inquiry and will respond within 24 hours.\n\nTicket ID: #12345\nPriority: Normal",
    tags: ["support", "response", "customer"],
    updatedAt: "2024-01-13",
    createdAt: "2024-01-08",
    wordCount: 25,
    usedInPrompts: 5,
  },
];

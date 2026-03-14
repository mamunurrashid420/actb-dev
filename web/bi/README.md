# Project Understanding and Plan

This document outlines the understanding of the project requirements, the proposed plan for implementation, and the current status.

## Project Requirements (Updated: Nov 7, 2025)

The user requires the following:

1.  **Login Screen**:
    *   Create a login screen similar to "ATP" (further clarification may be needed if "ATP" refers to a specific, non-standard design).
    *   Implement Supabase login.
    *   Add Google login.
    *   Add LinkedIn login.
    *   Include a '?' icon on the login page to allow direct access to dashboards using dummy accounts for each role (Admin, Creator, Viewer).

2.  **Roles**:
    *   Admin: Full access.
    *   Creator: Can create/edit dashboards and send shareable links to Viewers.
    *   Viewer: Read-only access to dashboards, can share links with other Viewers.

3.  **Supabase Integration**: The project uses Supabase as the database.

4.  **Plot Library**:
    *   Utilize the `visx` library for plots.
    *   Adhere to Edward Tufte's principles for data visualization.

5.  **Shareable Dashboard Links**:
    *   Dashboards should have shareable links.
    *   Creators can send these links to Viewers.
    *   Viewers can share these links with other Viewers.
    *   Links should allow public access without authentication.

6.  **Challenge No. 1: ConversationalChart Object (Visualization Unit)**:
    *   A component combining a chart and a chat.
    *   Must fit in small dimensions (e.g., within a dashboard).
    *   Ability to hide the conversation and context, displaying only the chart.
    *   Designed to house 3-4 units within a larger dashboard.
    *   Version tracking for the combined unit.
    *   Maintain a 1:1.6 (golden) ratio between height and width when both conversation and caption/summary are hidden.
    *   Caption can only be hidden after the conversation is hidden.

7.  **Challenge No. 2: LLM for Plot Decision / Factory Pattern**:
    *   **Future Goal**: Use an LLM to dynamically select the best plot type based on data.
    *   **Current Implementation**: Build a "factory pattern" that takes a `[plot config]` input and outputs the actual plot.
    *   Use fake data from a `/data/` directory.
    *   Define the best format for the "backend API" to return data for plotting.
    *   The `plot config` will be a JSON object (e.g., `{ "type": "pie chart", "data_shape": [3, 2], "data records": 1000 }`), with "type" corresponding to a `visx` object name.

8.  **Interactive Conversational Chat**:
    *   Improve interactivity of the chat experience.
    *   Enhance JSON structure for chat messages to include interactive elements and actions.
    *   Implement actions within the chat (e.g., clicking on a chart in chat) to display corresponding dashboards.
    *   Allow users to "pin" dashboard data from within the chat.

## Documentation

- [Permissions & Roles Guide](docs/permissions-and-roles.md) — explains how to manage permissions/roles in the admin UI and how CASL abilities are wired on the frontend.

## Current Plan

```mermaid
graph TD
    A[User Request: Expanded Scope] --> B{Information Gathering & Clarification};
    B --> C{Define Roles};
    C --> D{Clarify Routing Strategy};
    D --> E[Detailed Plan];
    E --> F[User Approval];
    F --> G[Switch to Code Mode];

    subgraph Information Gathering
        B --> B1[Review src/middleware.ts];
        B --> B2[Review src/middleware/auth-middleware.ts];
        B --> B3[Review Supabase client files];
        B --> B4[Review Supabase migrations/SQL for chat schema];
        B --> B5[Asked about specific roles and access levels, defined as Admin, Creator, Viewer];
        B --> B6[Asked about role-based routing implementation, confirmed all roles access /dashboard with adapted UI/functionality];
        B --> B7[Received new requirements for login, shareable dashboards, ConversationalChart, and plot factory];
        B --> B8[Received new requirements for interactive chat, displaying dashboards from chat, and pinning dashboard data];
    end

    subgraph Detailed Plan Steps
        E --> E1[Implement Supabase, Google, LinkedIn Login];
        E --> E2[Create 'user_roles' table & RLS];
        E --> E3[Implement role assignment logic];
        E --> E4[Enhance auth-middleware for roles];
        E --> E5[Implement role-based authorization in /dashboard];
        E --> E6[Create dummy user accounts & login UI];
        E --> E7[Modify conversations table with 'is_public'];
        E --> E8[Adjust RLS for public conversations];
        E --> E9[Create new 'dashboards' table with 'is_public' & RLS];
        E --> E10[Create API endpoint for public dashboard links];
        E --> E11[Implement UI for generating/sharing public dashboard links];
        E --> E12[Investigate chat message content storage (TEXT vs JSONB)];
        E --> E13[Design & Implement ConversationalChart component];
        E --> E14[Implement plot factory pattern with visx];
        E --> E15[Define backend API format for plots];
        E --> E16[Create fake data for plots];
        E --> E17[Enhance chat JSON for interactivity];
        E --> E18[Implement chat-to-dashboard actions];
        E --> E19[Implement dashboard data pinning];
        E --> E20[Migrate from next lint to ESLint CLI];
    end
```

## Detailed Todo List

### Phase 1: Setup and Core Features

#### Authentication and User Management
- [ ] Implement backend login via Python APIs.
- [ ] Add Google login.
- [ ] Add LinkedIn login.
- [ ] Create a `user_roles` table with `user_id`, `role` (ENUM: 'Admin', 'Creator', 'Viewer').
- [ ] Ensure only admins can modify roles via backend authorization.
- [ ] Implement logic to assign roles to users upon registration or by an admin.
- [ ] Enhance `src/middleware/auth-middleware.ts` to fetch user roles from backend APIs.
- [ ] Implement role-based authorization checks within the `/dashboard` route to adapt UI/functionality based on the user's role.
- [ ] Redirect unauthorized users from `/dashboard` if they don't have any of the specified roles, or to an unauthorized page if they try to access functionality beyond their role.
- [ ] Create dummy user accounts for each role (Admin, Creator, Viewer).
- [ ] Implement a UI element (e.g., a '?' icon) on the login page to allow direct access to dashboards using these dummy accounts.

#### Shareable Links (Dashboards & Chats)
- [ ] Adjust RLS policies for the `conversations` table to allow public access to conversations where `is_public` is true, even for unauthenticated users.
- [ ] Create a `dashboards` table, including `user_id` (Creator), `title`, and `is_public` (boolean, default false).
- [ ] Set up RLS for the `dashboards` table, allowing Creators to manage their own, and public access to `is_public = true` dashboards.
- [ ] Create a new API endpoint (e.g., `src/app/api/public-dashboard/[dashboard_id]/route.ts`) to serve public dashboard content without authentication.
- [ ] Create a new API endpoint (e.g., `src/app/api/public-chat/[conversation_id]/route.ts`) to serve public chat conversations without authentication.
- [ ] Ensure sensitive data is not exposed through public dashboard/chat links by carefully crafting the API response.
- [ ] Implement UI for generating and sharing public dashboard links (e.g., a button on the dashboard interface to make a dashboard public and copy the link).
- [ ] Implement UI for generating and sharing public chat links (e.g., a button on the chat interface to make a conversation public and copy the link).

#### Development Environment Setup
- [-] Migrate from `next lint` to ESLint CLI to resolve linting issues.

### Phase 2: Chat and Visualization Enhancements

#### Chat Data Storage Refactor
- [-] Investigate chat message content storage (TEXT vs. JSONB) and clarify user's preference. (Blocked: User is reviewing data validity)
- [ ] Enhance `ChatMessage` and `ChatContent` types in `src/types/chat/index.ts` to support interactive elements (e.g., `dashboard_action` type, `pin_data` type).

#### Visualization Unit (ConversationalChart)
- [ ] Design the `ConversationalChart` component combining chat and chart.
- [ ] Implement responsive design for `ConversationalChart` to fit small dimensions.
- [ ] Implement conditional rendering logic to hide conversation and context, displaying only the chart.
- [ ] Implement layout for multiple `ConversationalChart` units within a larger dashboard.
- [ ] Design and implement version tracking for `ConversationalChart` units.
- [ ] Ensure `ConversationalChart` maintains a 1:1.6 golden ratio when conversation and caption/summary are hidden.
- [ ] Implement logic to only allow hiding caption after conversation is hidden.

#### Dynamic Plotting with visx (Factory Pattern)
- [ ] Design and implement a "factory pattern" for dynamic plot rendering using `visx`.
- [ ] Define the `plot config` JSON structure (e.g., `{ "type": "pie chart", "data_shape": [3, 2], "data records": 1000, ... }`).
- [ ] Create fake dataset files in a `/data/` directory for various plot types.
- [ ] Define the optimal backend API format for returning plot data.
- [ ] Implement the plot factory to take `plot config` and fetch data (from fake data for now) to render the `visx` plot.

#### Interactive Chat Features
- [ ] Implement chat actions to display dashboards based on charts shown in the chat.
- [ ] Implement functionality for users to "pin" dashboard data from within the chat.

## Current Implementation Status

1.  **Initial Information Gathering**: Completed.
2.  **Role Definition**: Defined as Admin, Creator, Viewer.
3.  **Routing Strategy**: Confirmed all roles access `/dashboard` with adapted UI/functionality.
4.  **`is_public` column in `conversations` table**: Added in the database.
5.  **Chat Data Storage**: Under discussion with the user regarding `TEXT` vs. `JSONB` for `messages.content`. User is reviewing data validity.
6.  **New Requirements Incorporated**: Expanded scope for login, shareable dashboards, ConversationalChart, plot factory, and interactive chat features have been added to the plan.
7.  **Linting Issue**: Currently investigating and working on migrating from `next lint` to ESLint CLI.

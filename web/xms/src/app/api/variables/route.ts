/**
 * @deprecated These routes are deprecated and will be removed.
 * Use the Python FastAPI service at /variables instead.
 * See: service/src/app/api/variables/
 */
import { NextRequest, NextResponse } from "next/server";
// Variable type available via shared module if needed
import { createVariableSchema, updateVariableSchema } from "@/validators/variables";
// id generation handled by store
import { variableSupabaseStore } from "@/lib/store/variable-supabase-store";
import { variableMemoryStore } from "@/lib/store/variable-memory-store";

// Types and validation moved to shared modules

// Store abstraction
const isTest = process.env.NODE_ENV === "test";
const variablesStore = isTest ? variableMemoryStore : variableSupabaseStore;

// generateId moved to shared utils

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");

  if (id) {
    const found = await variablesStore.getById(id);
    if (!found) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json(found, { status: 200 });
  }

  const all = await variablesStore.list();
  return NextResponse.json(all, { status: 200 });
}

export async function POST(req: NextRequest) {
  try {
    const json = await req.json();
    const parsed = createVariableSchema.safeParse(json);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
    }

    const variable = await variablesStore.create({
      name: parsed.data.name,
      type: parsed.data.type,
      defaultValue: parsed.data.defaultValue,
      description: parsed.data.description,
      tags: parsed.data.tags,
    });
    return NextResponse.json(variable, { status: 201 });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

export async function PUT(req: NextRequest) {
  try {
    const json = await req.json();
    const parsed = updateVariableSchema.safeParse(json);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
    }

    const { id } = parsed.data;
    const existing = await variablesStore.getById(id);
    if (!existing) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    const updated = await variablesStore.update({
      id,
      name: parsed.data.name,
      type: parsed.data.type,
      defaultValue: parsed.data.defaultValue,
      description: parsed.data.description,
      tags: parsed.data.tags,
    });
    return NextResponse.json(updated, { status: 200 });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const id = searchParams.get("id");
    if (!id) {
      return NextResponse.json({ error: "'id' is required" }, { status: 400 });
    }
    const existed = await variablesStore.delete(id);
    if (!existed) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ ok: true }, { status: 200 });
  } catch {
    return NextResponse.json({ error: "Bad Request" }, { status: 400 });
  }
}

// Export store for tests
export const __variablesStore = variablesStore;

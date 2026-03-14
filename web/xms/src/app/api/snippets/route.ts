/**
 * @deprecated These routes are deprecated and will be removed.
 * Use the Python FastAPI service at /snippets instead.
 * See: service/src/app/api/snippets/
 */
import { NextRequest, NextResponse } from "next/server";
import { snippetMemoryStore } from "@/lib/store/snippet-memory-store";
import { snippetSupabaseStore } from "@/lib/store/snippet-supabase-store";
import { createSnippetSchema, updateSnippetSchema } from "@/validators/snippets";

const isTest = process.env.NODE_ENV === "test";
const snippetsStore = isTest ? snippetMemoryStore : snippetSupabaseStore;

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (id) {
    const found = await snippetsStore.getById(id);
    if (!found) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json(found, { status: 200 });
  }
  return NextResponse.json(await snippetsStore.list(), { status: 200 });
}

export async function POST(req: NextRequest) {
  try {
    const json = await req.json();
    const parsed = createSnippetSchema.safeParse(json);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
    }
    const created = await snippetsStore.create({
      name: parsed.data.name,
      body: parsed.data.body,
      tags: parsed.data.tags,
    });
    return NextResponse.json(created, { status: 201 });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

export async function PUT(req: NextRequest) {
  try {
    const json = await req.json();
    const parsed = updateSnippetSchema.safeParse(json);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
    }
    const updated = await snippetsStore.update({
      id: parsed.data.id,
      name: parsed.data.name,
      body: parsed.data.body,
      tags: parsed.data.tags,
    });
    if (!updated) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json(updated, { status: 200 });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const id = searchParams.get("id");
    if (!id) return NextResponse.json({ error: "'id' is required" }, { status: 400 });
    const ok = await snippetsStore.delete(id);
    if (!ok) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json({ ok: true }, { status: 200 });
  } catch {
    return NextResponse.json({ error: "Bad Request" }, { status: 400 });
  }
}

// Export store for tests
export const __snippetsStore = snippetsStore;

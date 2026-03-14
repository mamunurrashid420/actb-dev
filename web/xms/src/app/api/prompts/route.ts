/**
 * @deprecated These routes are deprecated and will be removed.
 * Use the Python FastAPI service at /prompts instead.
 * See: service/src/app/api/prompts/
 */
import { NextRequest, NextResponse } from "next/server";
import { promptMemoryStore } from "@/lib/store/prompt-memory-store";
import { promptSupabaseStore } from "@/lib/store/prompt-supabase-store";
import { createPromptSchema, updatePromptSchema } from "@/validators/prompts";

const isTest = process.env.NODE_ENV === "test";
const promptsStore = isTest ? promptMemoryStore : promptSupabaseStore;

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (id) {
    const found = await promptsStore.getById(id);
    if (!found) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json(found, { status: 200 });
  }
  return NextResponse.json(await promptsStore.list(), { status: 200 });
}

export async function POST(req: NextRequest) {
  try {
    const json = await req.json();
    const parsed = createPromptSchema.safeParse(json);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
    }
    const created = await promptsStore.create({
      name: parsed.data.name,
      tags: parsed.data.tags,
      blocks: parsed.data.blocks,
    });
    return NextResponse.json(created, { status: 201 });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}

export async function PUT(req: NextRequest) {
  try {
    const json = await req.json();
    const parsed = updatePromptSchema.safeParse(json);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
    }
    const updated = await promptsStore.update({
      id: parsed.data.id,
      name: parsed.data.name,
      tags: parsed.data.tags,
      blocks: parsed.data.blocks,
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
    const ok = await promptsStore.delete(id);
    if (!ok) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json({ ok: true }, { status: 200 });
  } catch {
    return NextResponse.json({ error: "Bad Request" }, { status: 400 });
  }
}

export const __promptsStore = promptsStore;

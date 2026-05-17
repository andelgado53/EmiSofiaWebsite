import { revalidatePath } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const secret = body.secret;

  if (secret !== process.env.REVALIDATE_SECRET) {
    return NextResponse.json(
      { message: "Invalid secret" },
      { status: 401 }
    );
  }

  revalidatePath("/notes");
  revalidatePath("/notes/[id]", "page");

  return NextResponse.json({ revalidated: true });
}

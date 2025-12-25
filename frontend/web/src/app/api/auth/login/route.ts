import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createSessionToken, getCookieName } from "@/lib/auth/session";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as
    | { email?: string; password?: string }
    | null;

  const email = (body?.email || "").trim().toLowerCase();
  const password = body?.password || "";
  if (!email || !password) {
    return NextResponse.json({ error: "Missing credentials" }, { status: 400 });
  }

  const role = email.includes("admin") ? "admin" : "user";
  const { token, payload } = createSessionToken({ email, role }, 8 * 60 * 60);

  const jar = await cookies();
  jar.set({
    name: getCookieName(),
    value: token,
    httpOnly: true,
    sameSite: "lax",
    secure: false,
    path: "/",
  });

  return NextResponse.json({ email: payload.email, role: payload.role, exp: payload.exp });
}


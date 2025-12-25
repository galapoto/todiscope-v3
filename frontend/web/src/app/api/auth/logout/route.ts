import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getCookieName } from "@/lib/auth/session";

export async function POST() {
  const jar = await cookies();
  jar.set({
    name: getCookieName(),
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: false,
    path: "/",
    maxAge: 0,
  });
  return NextResponse.json({ ok: true });
}


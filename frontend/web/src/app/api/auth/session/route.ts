import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getCookieName, verifySessionToken } from "@/lib/auth/session";

export async function GET() {
  const jar = await cookies();
  const token = jar.get(getCookieName())?.value;
  if (!token) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  const verified = verifySessionToken(token);
  if (!verified.ok || !verified.payload) {
    jar.set({
      name: getCookieName(),
      value: "",
      httpOnly: true,
      sameSite: "lax",
      secure: false,
      path: "/",
      maxAge: 0,
    });
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  return NextResponse.json({
    authenticated: true,
    email: verified.payload.email,
    role: verified.payload.role,
    exp: verified.payload.exp,
  });
}


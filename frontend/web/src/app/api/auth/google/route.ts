import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createSessionToken, getCookieName } from "@/lib/auth/session";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const email = (url.searchParams.get("email") || "google.user@todiscope.local")
    .trim()
    .toLowerCase();

  const role = email.includes("admin") ? "admin" : "user";
  const { token } = createSessionToken({ email, role }, 8 * 60 * 60);

  const jar = await cookies();
  jar.set({
    name: getCookieName(),
    value: token,
    httpOnly: true,
    sameSite: "lax",
    secure: false,
    path: "/",
  });

  return NextResponse.redirect(new URL("/dashboard", request.url));
}


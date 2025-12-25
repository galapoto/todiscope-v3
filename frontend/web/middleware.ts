import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = new Set<string>([
  "/login",
  "/api/auth/login",
  "/api/auth/logout",
  "/api/auth/session",
  "/api/auth/google",
]);

function isPublicPath(pathname: string) {
  if (PUBLIC_PATHS.has(pathname)) return true;
  if (pathname.startsWith("/_next")) return true;
  if (pathname.startsWith("/favicon")) return true;
  return false;
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const session = request.cookies.get("todiscope_session")?.value;

  if (pathname === "/login" && session) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  if (!session) {
    const next = `${pathname}${search ?? ""}`;
    const url = new URL("/login", request.url);
    url.searchParams.set("next", next);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
};


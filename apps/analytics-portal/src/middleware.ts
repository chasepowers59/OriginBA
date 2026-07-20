import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_DISABLED = process.env.NEXT_PUBLIC_PORTAL_AUTH_DISABLED === "true";

export function middleware(request: NextRequest) {
  if (AUTH_DISABLED) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;
  if (pathname.startsWith("/login") || pathname.startsWith("/change-password")) {
    return NextResponse.next();
  }

  if (!request.cookies.get("portal_session") && !request.cookies.get("portal_access_token")) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|brand-icon.svg).*)"],
};

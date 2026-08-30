import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_DISABLED = process.env.NEXT_PUBLIC_PORTAL_AUTH_DISABLED === "true";

// First-path segments that are real app surfaces, never tenant slugs. Anything else at
// the URL root (e.g. /ellensburg) is treated as a multi-tenant login entry point. Keep
// this in sync when a new top-level route is added.
const APP_ROUTES = new Set([
  "",
  "build",
  "reports",
  "dashboards",
  "dashboard",
  "database",
  "data-quality",
  "settings",
  "explore",
  "workstream",
  "login",
  "change-password",
]);

function isAuthed(request: NextRequest): boolean {
  return Boolean(
    request.cookies.get("portal_session") || request.cookies.get("portal_access_token"),
  );
}

export function middleware(request: NextRequest) {
  if (AUTH_DISABLED) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;
  if (pathname.startsWith("/login") || pathname.startsWith("/change-password")) {
    return NextResponse.next();
  }

  // Multi-tenant entry: a bare /<slug> that is not an app route. The login page resolves
  // and validates the slug; an unknown slug simply falls back to the root login form.
  const segments = pathname.split("/").filter(Boolean);
  const firstSegment = segments[0] ?? "";
  const isTenantLanding =
    segments.length === 1 &&
    !APP_ROUTES.has(firstSegment) &&
    !firstSegment.startsWith("_next") &&
    !firstSegment.startsWith("api") &&
    !firstSegment.includes(".");

  if (isTenantLanding) {
    const url = request.nextUrl.clone();
    if (isAuthed(request)) {
      // Already signed in — the tenant landing is just an entry point.
      url.pathname = "/";
      url.search = "";
      return NextResponse.redirect(url);
    }
    url.pathname = "/login";
    url.search = "";
    url.searchParams.set("tenant", firstSegment);
    return NextResponse.redirect(url);
  }

  if (!isAuthed(request)) {
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

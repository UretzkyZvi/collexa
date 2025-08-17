import { NextRequest, NextResponse } from "next/server";

// Public paths that don't require auth
const PUBLIC_PATHS = [
  "/health",
  "/handler", // Stack Auth pages
  "/api", // Next API routes
  "/onboarding", // onboarding has its own gating
];

function isPublicPath(pathname: string) {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow public paths
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  // Read Stack cookie to check if user is signed in.
  // With tokenStore: "nextjs-cookie", the cookie name is managed by @stackframe/stack
  // We simply check for presence of any stack auth cookie prefix "stack_".
  const hasStackCookie = req.cookies.getAll().some((c) => c.name.startsWith("stack_"));

  if (!hasStackCookie) {
    // Redirect to sign-in, preserving return URL
    const url = req.nextUrl.clone();
    url.pathname = "/handler/sign-in";
    url.searchParams.set("redirect_url", req.nextUrl.pathname + req.nextUrl.search);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|assets/).*)",
  ],
};


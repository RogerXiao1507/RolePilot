import { NextRequest, NextResponse } from "next/server";

import { auth0 } from "@/lib/auth0";

export async function proxy(request: NextRequest) {
  const authResponse = await auth0.middleware(request);
  const path = request.nextUrl.pathname;

  if (
    path === "/login" ||
    path.startsWith("/auth/") ||
    path.startsWith("/api/backend/")
  ) {
    return authResponse;
  }

  const session = await auth0.getSession(request);
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    await auth0.getAccessToken(request, authResponse);
  } catch {
    return NextResponse.redirect(new URL("/auth/logout", request.url));
  }

  return authResponse;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};

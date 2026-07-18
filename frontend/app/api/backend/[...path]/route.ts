import { NextRequest, NextResponse } from "next/server";

import { auth0 } from "@/lib/auth0";

const BACKEND_API_URL = (
  process.env.BACKEND_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

const RESPONSE_HEADERS = [
  "content-type",
  "content-disposition",
  "content-length",
  "x-request-id",
] as const;

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function forward(request: NextRequest, context: RouteContext) {
  const session = await auth0.getSession();
  if (!session) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  let token: string;
  try {
    ({ token } = await auth0.getAccessToken());
  } catch {
    return NextResponse.json(
      { detail: "Your session expired. Please sign in again." },
      { status: 401 }
    );
  }

  const { path } = await context.params;
  const safePath = path.map(encodeURIComponent).join("/");
  const target = `${BACKEND_API_URL}/${safePath}${request.nextUrl.search}`;
  const headers = new Headers({ Authorization: `Bearer ${token}` });

  const contentType = request.headers.get("content-type");
  const accept = request.headers.get("accept");
  if (contentType) headers.set("content-type", contentType);
  if (accept) headers.set("accept", accept);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const response = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    cache: "no-store",
    redirect: "manual",
  });

  const responseHeaders = new Headers();
  for (const headerName of RESPONSE_HEADERS) {
    const value = response.headers.get(headerName);
    if (value) responseHeaders.set(headerName, value);
  }

  return new NextResponse(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const PUT = forward;
export const DELETE = forward;

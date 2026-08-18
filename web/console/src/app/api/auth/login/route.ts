import { NextRequest, NextResponse } from "next/server";

import { sealLoginTransaction } from "@/lib/auth-session";
import { loadConsoleEnvironment } from "@/lib/environment";
import { beginAuthorization } from "@/lib/oidc-client";

export const dynamic = "force-dynamic";

function returnPath(request: NextRequest): string {
  const value = request.nextUrl.searchParams.get("return_to") ?? "/";
  if (!value.startsWith("/") || value.startsWith("//") || value.length > 2048) {
    return "/";
  }
  return value;
}

export async function GET(request: NextRequest) {
  const config = loadConsoleEnvironment();
  if (config.authMode !== "oidc") {
    return NextResponse.redirect(new URL("/", request.url));
  }
  try {
    const started = await beginAuthorization(config, returnPath(request));
    const response = NextResponse.redirect(started.redirectUrl);
    response.cookies.set(
      config.transactionCookieName,
      sealLoginTransaction(started.transaction, config.sessionEncryptionKey),
      {
        httpOnly: true,
        secure: config.secureCookies,
        sameSite: "lax",
        path: "/",
        maxAge: 600,
        priority: "high",
      },
    );
    response.headers.set("cache-control", "no-store");
    return response;
  } catch {
    return NextResponse.redirect(
      new URL("/login?reason=identity_provider_unavailable", request.url),
    );
  }
}

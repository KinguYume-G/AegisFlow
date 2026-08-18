import { NextRequest, NextResponse } from "next/server";

import { safeReturnPath, sealLoginTransaction } from "@/lib/auth-session";
import { loadConsoleEnvironment } from "@/lib/environment";
import { beginAuthorization } from "@/lib/oidc-client";

export const dynamic = "force-dynamic";

function returnPath(request: NextRequest): string {
  return safeReturnPath(request.nextUrl.searchParams.get("return_to"));
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

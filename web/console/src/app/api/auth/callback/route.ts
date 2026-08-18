import { NextRequest, NextResponse } from "next/server";

import { openLoginTransaction } from "@/lib/auth-session";
import { exchangeProviderAccessToken } from "@/lib/core-auth-client";
import { loadConsoleEnvironment } from "@/lib/environment";
import { finishAuthorization } from "@/lib/oidc-client";

export const dynamic = "force-dynamic";

function clearTransaction(response: NextResponse, name: string) {
  response.cookies.set(name, "", { maxAge: 0, path: "/" });
}

function failed(request: NextRequest, transactionCookieName: string) {
  const response = NextResponse.redirect(
    new URL("/login?reason=oidc_callback_failed", request.url),
  );
  clearTransaction(response, transactionCookieName);
  response.headers.set("cache-control", "no-store");
  return response;
}

export async function GET(request: NextRequest) {
  const config = loadConsoleEnvironment();
  if (config.authMode !== "oidc") {
    return NextResponse.redirect(new URL("/", request.url));
  }
  try {
    const sealed = request.cookies.get(config.transactionCookieName)?.value;
    if (!sealed) return failed(request, config.transactionCookieName);
    const transaction = openLoginTransaction(sealed, config.sessionEncryptionKey);
    const accessToken = await finishAuthorization(
      config,
      new URL(request.url),
      transaction,
    );
    const created = await exchangeProviderAccessToken(config, accessToken);
    const maxAge = Math.max(
      1,
      Math.min(3600, Math.floor(Date.parse(created.expires_at) / 1000 - Date.now() / 1000)),
    );
    const response = NextResponse.redirect(
      new URL(transaction.returnPath, config.consoleUrl),
    );
    clearTransaction(response, config.transactionCookieName);
    response.cookies.set(config.sessionCookieName, created.session_token, {
      httpOnly: true,
      secure: config.secureCookies,
      sameSite: "strict",
      path: "/",
      maxAge,
      priority: "high",
    });
    response.headers.set("cache-control", "no-store");
    return response;
  } catch {
    return failed(request, config.transactionCookieName);
  }
}

import { NextResponse } from "next/server";

import {
  AuthenticationExchangeError,
  revokeCoreSession,
} from "@/lib/core-auth-client";
import { loadConsoleEnvironment } from "@/lib/environment";
import {
  assertTrustedMutation,
  MutationGuardError,
} from "@/lib/mutation-guard";

export async function POST(request: Request) {
  const config = loadConsoleEnvironment();
  if (config.authMode !== "oidc") {
    return NextResponse.json({ error: { code: "oidc_not_enabled" } }, { status: 409 });
  }
  try {
    assertTrustedMutation(request, config);
    const cookie = request.headers
      .get("cookie")
      ?.split(";")
      .map((value) => value.trim())
      .find((value) => value.startsWith(`${config.sessionCookieName}=`));
    const sessionToken = cookie
      ? decodeURIComponent(cookie.slice(config.sessionCookieName.length + 1))
      : null;
    if (sessionToken) await revokeCoreSession(config, sessionToken);
    const response = NextResponse.json({ signed_out: true });
    response.cookies.set(config.sessionCookieName, "", { maxAge: 0, path: "/" });
    response.headers.set("cache-control", "no-store");
    return response;
  } catch (error) {
    const code =
      error instanceof AuthenticationExchangeError
        ? error.code
        : error instanceof MutationGuardError
          ? error.code
          : "logout_failed";
    const status = error instanceof AuthenticationExchangeError ? 503 : 403;
    return NextResponse.json(
      { error: { code } },
      { status, headers: { "cache-control": "no-store" } },
    );
  }
}

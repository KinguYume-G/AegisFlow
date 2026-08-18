import "server-only";

import { z } from "zod";

import type { OidcConsoleEnvironment } from "./environment";

const exchangeSchema = z
  .object({
    session_token: z.string().regex(/^afs_cs_[A-Za-z0-9_-]{43}$/),
    expires_at: z.string().datetime({ offset: true }),
    actor_reference: z.string().min(1).max(512),
  })
  .strict();

export class AuthenticationExchangeError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "AuthenticationExchangeError";
  }
}

function errorCode(value: unknown, fallback = "session_exchange_failed"): string {
  if (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof value.error === "object" &&
    value.error !== null &&
    "code" in value.error &&
    typeof value.error.code === "string"
  ) {
    return value.error.code.slice(0, 128);
  }
  return fallback;
}

export async function exchangeProviderAccessToken(
  config: OidcConsoleEnvironment,
  accessToken: string,
) {
  let response: Response;
  try {
    response = await fetch(`${config.coreUrl}/v1/auth/sessions`, {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: `Bearer ${accessToken}`,
      },
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    throw new AuthenticationExchangeError("core_unavailable");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new AuthenticationExchangeError(errorCode(body));
  const parsed = exchangeSchema.safeParse(body);
  if (!parsed.success) {
    throw new AuthenticationExchangeError("session_exchange_contract_invalid");
  }
  return parsed.data;
}

export async function revokeCoreSession(
  config: OidcConsoleEnvironment,
  sessionToken: string,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${config.coreUrl}/v1/auth/session`, {
      method: "DELETE",
      cache: "no-store",
      headers: { authorization: `AegisSession ${sessionToken}` },
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new AuthenticationExchangeError("core_unavailable");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new AuthenticationExchangeError(
      errorCode(body, "session_revocation_failed"),
    );
  }
}

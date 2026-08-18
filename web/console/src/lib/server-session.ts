import "server-only";

import { cookies } from "next/headers";

import { createCsrfToken } from "./auth-session";
import type { OidcConsoleEnvironment } from "./environment";

const OPAQUE_SESSION = /^afs_cs_[A-Za-z0-9_-]{43}$/;

export async function readConsoleSessionToken(
  config: OidcConsoleEnvironment,
): Promise<string | null> {
  const value = (await cookies()).get(config.sessionCookieName)?.value ?? null;
  return value && OPAQUE_SESSION.test(value) ? value : null;
}

export async function requireConsoleSessionToken(
  config: OidcConsoleEnvironment,
): Promise<string> {
  const token = await readConsoleSessionToken(config);
  if (!token) throw new Error("authentication_required");
  return token;
}

export async function csrfForCurrentSession(
  config: OidcConsoleEnvironment,
): Promise<string> {
  return createCsrfToken(
    await requireConsoleSessionToken(config),
    config.sessionEncryptionKey,
  );
}

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import {
  revokeCoreSession,
} from "./core-auth-client";
import type { OidcConsoleEnvironment } from "./environment";

const config = {
  authMode: "oidc",
  coreUrl: "https://core.example",
  consoleUrl: "https://console.example",
  callbackUrl: "https://console.example/api/auth/callback",
  issuer: "https://idp.example",
  discoveryUrl: "https://idp.example/.well-known/openid-configuration",
  clientId: "console",
  clientSecret: "not-a-real-client-secret",
  scope: "openid",
  sessionEncryptionKey: "A".repeat(43),
  sessionCookieName: "__Host-aegisflow_session",
  transactionCookieName: "__Host-aegisflow_login",
  secureCookies: true,
} satisfies OidcConsoleEnvironment;

describe("Core session revocation", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("fails closed when Core rejects revocation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: "session_revoke_failed" } }), {
          status: 503,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(revokeCoreSession(config, `afs_cs_${"S".repeat(43)}`)).rejects
      .toMatchObject({
        name: "AuthenticationExchangeError",
        code: "session_revoke_failed",
      });
  });

  it("fails closed when Core cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    await expect(revokeCoreSession(config, `afs_cs_${"S".repeat(43)}`)).rejects
      .toMatchObject({ code: "core_unavailable" });
  });
});

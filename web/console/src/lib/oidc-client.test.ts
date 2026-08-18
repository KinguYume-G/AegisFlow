import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("openid-client", () => ({
  Configuration: class Configuration {},
  allowInsecureRequests: vi.fn(),
  randomPKCECodeVerifier: () => "verifier",
  calculatePKCECodeChallenge: async () => "challenge",
  randomState: () => "state",
  randomNonce: () => "nonce",
  buildAuthorizationUrl: () => new URL("https://idp.example/authorize"),
}));

import { beginAuthorization } from "./oidc-client";
import type { OidcConsoleEnvironment } from "./environment";

function environment(suffix: string): OidcConsoleEnvironment {
  const issuer = `https://idp-${suffix}.example`;
  return {
    authMode: "oidc",
    coreUrl: "https://core.example",
    consoleUrl: "https://console.example",
    callbackUrl: "https://console.example/api/auth/callback",
    issuer,
    discoveryUrl: `${issuer}/.well-known/openid-configuration`,
    clientId: "console",
    clientSecret: "not-a-real-client-secret",
    scope: "openid",
    sessionEncryptionKey: "A".repeat(43),
    sessionCookieName: "__Host-aegisflow_session",
    transactionCookieName: "__Host-aegisflow_login",
    secureCookies: true,
  };
}

describe("OIDC discovery cache", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("evicts a rejected discovery promise so a transient outage can recover", async () => {
    const config = environment("transient");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("", { status: 503 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ issuer: config.issuer }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(beginAuthorization(config, "/")).rejects.toThrow(
      "oidc_discovery_unavailable",
    );
    await expect(beginAuthorization(config, "/runs")).resolves.toMatchObject({
      transaction: { returnPath: "/runs" },
    });
    await beginAuthorization(config, "/approvals");

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

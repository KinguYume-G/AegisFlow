import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/core-auth-client", () => {
  class AuthenticationExchangeError extends Error {
    constructor(public readonly code: string) {
      super(code);
    }
  }
  return {
    AuthenticationExchangeError,
    revokeCoreSession: vi
      .fn()
      .mockRejectedValue(new AuthenticationExchangeError("core_unavailable")),
  };
});
vi.mock("@/lib/environment", () => ({
  loadConsoleEnvironment: () => ({
    authMode: "oidc",
    sessionCookieName: "aegisflow_session",
  }),
}));
vi.mock("@/lib/mutation-guard", () => ({ assertTrustedMutation: vi.fn() }));

import { POST } from "./route";

describe("OIDC logout", () => {
  it("retains the browser session cookie when Core revocation fails", async () => {
    const response = await POST(
      new Request("http://localhost/api/auth/logout", {
        method: "POST",
        headers: { cookie: `aegisflow_session=afs_cs_${"S".repeat(43)}` },
      }),
    );

    expect(response.status).toBe(503);
    expect(response.headers.get("set-cookie")).toBeNull();
    await expect(response.json()).resolves.toEqual({
      error: { code: "core_unavailable" },
    });
  });
});

import { describe, expect, it } from "vitest";

import { loadConsoleEnvironment, publicConsoleContext } from "./environment";

const base = {
  AEGISFLOW_AUTH_MODE: "local_mvp",
  AEGISFLOW_CORE_URL: "http://core:8000",
  AEGISFLOW_CONSOLE_PERSONA: "developer",
  AEGISFLOW_LOCAL_TOKEN: "developer-token-long-enough",
  AEGISFLOW_REVIEWER_CONSOLE_URL: "http://localhost:3001",
};

const oidc = {
  AEGISFLOW_AUTH_MODE: "oidc",
  AEGISFLOW_CORE_URL: "http://core:8000",
  AEGISFLOW_CONSOLE_URL: "https://console.aegisflow.example",
  AEGISFLOW_OIDC_ISSUER: "https://identity.aegisflow.example/realms/aegisflow",
  AEGISFLOW_OIDC_CLIENT_ID: "aegisflow-console",
  AEGISFLOW_OIDC_CLIENT_SECRET: "server-side-client-secret",
  AEGISFLOW_SESSION_ENCRYPTION_KEY: "A".repeat(43),
};

describe("console environment", () => {
  it("selects only the token for the configured server persona", () => {
    const config = loadConsoleEnvironment(base);

    expect(config.authMode).toBe("local_mvp");
    if (config.authMode !== "local_mvp") throw new Error("expected_local_mvp");
    expect(config.persona).toBe("developer");
    expect(config.token).toBe("developer-token-long-enough");
    expect(config.coreUrl).toBe("http://core:8000");
  });

  it("rejects unsupported personas and non-http Core URLs", () => {
    expect(() =>
      loadConsoleEnvironment({ ...base, AEGISFLOW_CONSOLE_PERSONA: "admin" }),
    ).toThrow("console_persona_invalid");
    expect(() =>
      loadConsoleEnvironment({ ...base, AEGISFLOW_CORE_URL: "file:///etc/passwd" }),
    ).toThrow("core_url_invalid");
  });

  it("creates a browser-safe context without the server token", () => {
    const context = publicConsoleContext(loadConsoleEnvironment(base));
    const serialized = JSON.stringify(context);

    expect(context.persona).toBe("developer");
    expect(serialized).not.toContain("token-long-enough");
  });

  it("accepts a complete OIDC server profile without local persona credentials", () => {
    const config = loadConsoleEnvironment(oidc);

    expect(config.authMode).toBe("oidc");
    if (config.authMode !== "oidc") throw new Error("expected_oidc");
    expect(config.callbackUrl).toBe(
      "https://console.aegisflow.example/api/auth/callback",
    );
    expect(config.discoveryUrl).toBe(
      "https://identity.aegisflow.example/realms/aegisflow/.well-known/openid-configuration",
    );
    expect(config.secureCookies).toBe(true);
    expect(JSON.stringify(publicConsoleContext(config))).not.toContain("client-secret");
    expect(JSON.stringify(publicConsoleContext(config))).not.toContain("AAAA");
  });

  it("rejects partial OIDC, insecure public URLs, and mixed local credentials", () => {
    expect(() =>
      loadConsoleEnvironment({ ...oidc, AEGISFLOW_OIDC_CLIENT_SECRET: undefined }),
    ).toThrow("console_environment_invalid");
    expect(() =>
      loadConsoleEnvironment({ ...oidc, AEGISFLOW_CONSOLE_URL: "http://console.example" }),
    ).toThrow("console_url_insecure");
    expect(() =>
      loadConsoleEnvironment({ ...oidc, AEGISFLOW_LOCAL_TOKEN: "should-not-be-present" }),
    ).toThrow("oidc_local_identity_conflict");
  });
});

import { describe, expect, it } from "vitest";

import { loadConsoleEnvironment, publicConsoleContext } from "./environment";

const base = {
  AEGISFLOW_CORE_URL: "http://core:8000",
  AEGISFLOW_CONSOLE_PERSONA: "developer",
  AEGISFLOW_LOCAL_TOKEN: "developer-token-long-enough",
  AEGISFLOW_REVIEWER_CONSOLE_URL: "http://localhost:3001",
};

describe("console environment", () => {
  it("selects only the token for the configured server persona", () => {
    const config = loadConsoleEnvironment(base);

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
});

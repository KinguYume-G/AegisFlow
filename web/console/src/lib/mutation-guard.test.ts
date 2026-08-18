import { describe, expect, it } from "vitest";

import { assertTrustedMutation } from "./mutation-guard";
import { createCsrfToken } from "./auth-session";

function request(headers: Record<string, string>) {
  return new Request("http://localhost:3000/api/runs", {
    method: "POST",
    headers,
    body: "{}",
  });
}

describe("BFF mutation guard", () => {
  it("accepts same-origin browser JSON", () => {
    expect(() =>
      assertTrustedMutation(
        request({
          origin: "http://localhost:3000",
          "content-type": "application/json",
          "sec-fetch-site": "same-origin",
        }),
      ),
    ).not.toThrow();
  });

  it("uses the browser-facing Host when the application runs behind a container proxy", () => {
    expect(() =>
      assertTrustedMutation(
        request({
          origin: "http://127.0.0.1:3000",
          host: "127.0.0.1:3000",
          "content-type": "application/json",
          "sec-fetch-site": "same-origin",
        }),
      ),
    ).not.toThrow();
  });

  it("rejects cross-site, missing origin, and non-JSON mutations", () => {
    expect(() =>
      assertTrustedMutation(
        request({
          origin: "https://evil.example",
          "content-type": "application/json",
          "sec-fetch-site": "cross-site",
        }),
      ),
    ).toThrow("cross_site_mutation_denied");
    expect(() =>
      assertTrustedMutation(
        request({ "content-type": "application/json", "sec-fetch-site": "same-origin" }),
      ),
    ).toThrow("origin_required");
    expect(() =>
      assertTrustedMutation(
        request({
          origin: "http://localhost:3000",
          "content-type": "text/plain",
          "sec-fetch-site": "same-origin",
        }),
      ),
    ).toThrow("json_content_type_required");
  });

  it("requires a CSRF value bound to the opaque OIDC session", () => {
    const session = `afs_cs_${"S".repeat(43)}`;
    const key = "A".repeat(43);
    const config = {
      authMode: "oidc" as const,
      sessionEncryptionKey: key,
      sessionCookieName: "aegisflow_session",
    };
    const trusted = {
      origin: "http://localhost:3000",
      "content-type": "application/json",
      "sec-fetch-site": "same-origin",
      cookie: `aegisflow_session=${session}`,
      "x-aegisflow-csrf": createCsrfToken(session, key),
    };

    expect(() => assertTrustedMutation(request(trusted), config)).not.toThrow();
    expect(() =>
      assertTrustedMutation(request({ ...trusted, "x-aegisflow-csrf": "forged" }), config),
    ).toThrow("csrf_validation_failed");
    expect(() =>
      assertTrustedMutation(request({ ...trusted, cookie: "" }), config),
    ).toThrow("authentication_required");
  });
});

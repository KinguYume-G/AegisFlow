import { describe, expect, it } from "vitest";

import {
  createCsrfToken,
  openLoginTransaction,
  sealLoginTransaction,
  verifyCsrfToken,
} from "./auth-session";

const key = "A".repeat(43);

describe("server-only authentication envelopes", () => {
  it("encrypts and authenticates a bounded, expiring login transaction", () => {
    const transaction = {
      state: "state-value",
      nonce: "nonce-value",
      codeVerifier: "verifier-value",
      returnPath: "/runs/new",
      expiresAt: 2_000,
    };
    const sealed = sealLoginTransaction(transaction, key);

    expect(sealed).not.toContain("verifier-value");
    expect(openLoginTransaction(sealed, key, 1_999)).toEqual(transaction);
    expect(() => openLoginTransaction(sealed, key, 2_001)).toThrow(
      "login_transaction_expired",
    );
  });

  it("rejects tampering and unsafe return paths", () => {
    const sealed = sealLoginTransaction(
      {
        state: "state",
        nonce: "nonce",
        codeVerifier: "verifier",
        returnPath: "/",
        expiresAt: 2_000,
      },
      key,
    );

    const parts = sealed.split(".");
    const payload = parts[2] ?? "";
    parts[2] = `${payload.startsWith("x") ? "y" : "x"}${payload.slice(1)}`;
    expect(() => openLoginTransaction(parts.join("."), key, 1_000)).toThrow(
      "login_transaction_invalid",
    );
    expect(() =>
      sealLoginTransaction(
        {
          state: "state",
          nonce: "nonce",
          codeVerifier: "verifier",
          returnPath: "https://evil.example",
          expiresAt: 2_000,
        },
        key,
      ),
    ).toThrow("return_path_invalid");
  });

  it("derives a session-bound CSRF value and compares it safely", () => {
    const session = `afs_cs_${"S".repeat(43)}`;
    const csrf = createCsrfToken(session, key);

    expect(csrf).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(verifyCsrfToken(csrf, session, key)).toBe(true);
    expect(verifyCsrfToken(`${csrf.slice(0, -1)}x`, session, key)).toBe(false);
    expect(verifyCsrfToken(csrf, `afs_cs_${"T".repeat(43)}`, key)).toBe(false);
  });
});

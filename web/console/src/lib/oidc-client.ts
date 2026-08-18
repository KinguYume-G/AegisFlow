import "server-only";

import * as client from "openid-client";

import type { LoginTransaction } from "./auth-session";
import type { OidcConsoleEnvironment } from "./environment";

let cached:
  | { fingerprint: string; value: Promise<client.Configuration> }
  | undefined;

function configuration(config: OidcConsoleEnvironment) {
  const fingerprint = `${config.issuer}\0${config.discoveryUrl}\0${config.clientId}`;
  if (cached?.fingerprint === fingerprint) return cached.value;
  const value = loadConfiguration(config);
  cached = { fingerprint, value };
  return value;
}

async function loadConfiguration(config: OidcConsoleEnvironment) {
  const response = await fetch(config.discoveryUrl, {
    headers: { accept: "application/json" },
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
  });
  if (!response.ok) throw new Error("oidc_discovery_unavailable");
  const body = await response.text();
  if (body.length > 1_048_576) throw new Error("oidc_discovery_too_large");
  const metadata = JSON.parse(body) as client.ServerMetadata;
  if (metadata.issuer !== config.issuer) throw new Error("oidc_issuer_mismatch");
  const discovered = new client.Configuration(
    metadata,
    config.clientId,
    config.clientSecret,
  );
  if (new URL(config.issuer).protocol === "http:") {
    client.allowInsecureRequests(discovered);
  }
  return discovered;
}

export async function beginAuthorization(
  config: OidcConsoleEnvironment,
  returnPath: string,
): Promise<{ redirectUrl: URL; transaction: LoginTransaction }> {
  const discovered = await configuration(config);
  const codeVerifier = client.randomPKCECodeVerifier();
  const codeChallenge = await client.calculatePKCECodeChallenge(codeVerifier);
  const state = client.randomState();
  const nonce = client.randomNonce();
  const redirectUrl = client.buildAuthorizationUrl(discovered, {
    redirect_uri: config.callbackUrl,
    scope: config.scope,
    response_type: "code",
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
    state,
    nonce,
  });
  return {
    redirectUrl,
    transaction: {
      state,
      nonce,
      codeVerifier,
      returnPath,
      expiresAt: Math.floor(Date.now() / 1000) + 600,
    },
  };
}

export async function finishAuthorization(
  config: OidcConsoleEnvironment,
  currentUrl: URL,
  transaction: LoginTransaction,
): Promise<string> {
  const discovered = await configuration(config);
  const tokens = await client.authorizationCodeGrant(discovered, currentUrl, {
    pkceCodeVerifier: transaction.codeVerifier,
    expectedState: transaction.state,
    expectedNonce: transaction.nonce,
  });
  if (!tokens.access_token || tokens.access_token.length > 16_384) {
    throw new Error("oidc_access_token_invalid");
  }
  return tokens.access_token;
}

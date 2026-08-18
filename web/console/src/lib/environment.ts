import { z } from "zod";

export type ConsolePersona = "developer" | "reviewer";

interface ConsoleEnvironmentBase {
  coreUrl: string;
}

export interface LocalConsoleEnvironment extends ConsoleEnvironmentBase {
  authMode: "local_mvp";
  persona: ConsolePersona;
  token: string;
  developerConsoleUrl: string;
  reviewerConsoleUrl: string;
}

export interface OidcConsoleEnvironment extends ConsoleEnvironmentBase {
  authMode: "oidc";
  consoleUrl: string;
  callbackUrl: string;
  issuer: string;
  discoveryUrl: string;
  clientId: string;
  clientSecret: string;
  scope: string;
  sessionEncryptionKey: string;
  sessionCookieName: string;
  transactionCookieName: string;
  secureCookies: boolean;
}

export type ConsoleEnvironment = LocalConsoleEnvironment | OidcConsoleEnvironment;

const baseSchema = z.object({
  AEGISFLOW_AUTH_MODE: z.enum(["local_mvp", "oidc"]),
  AEGISFLOW_CORE_URL: z.string().url(),
});

const localSchema = baseSchema
  .extend({
    AEGISFLOW_AUTH_MODE: z.literal("local_mvp"),
    AEGISFLOW_CONSOLE_PERSONA: z.enum(["developer", "reviewer"]),
    AEGISFLOW_LOCAL_TOKEN: z.string().min(16).max(256),
    AEGISFLOW_DEVELOPER_CONSOLE_URL: z
      .string()
      .url()
      .default("http://localhost:3000"),
    AEGISFLOW_REVIEWER_CONSOLE_URL: z
      .string()
      .url()
      .default("http://localhost:3001"),
  })
  .passthrough();

const oidcSchema = baseSchema
  .extend({
    AEGISFLOW_AUTH_MODE: z.literal("oidc"),
    AEGISFLOW_CONSOLE_URL: z.string().url(),
    AEGISFLOW_OIDC_ISSUER: z.string().url(),
    AEGISFLOW_OIDC_DISCOVERY_URL: z.string().url().optional(),
    AEGISFLOW_OIDC_CLIENT_ID: z.string().min(1).max(255),
    AEGISFLOW_OIDC_CLIENT_SECRET: z.string().min(16).max(4096),
    AEGISFLOW_OIDC_SCOPE: z.string().default("openid profile email"),
    AEGISFLOW_SESSION_ENCRYPTION_KEY: z
      .string()
      .regex(/^[A-Za-z0-9_-]{43}$/),
    AEGISFLOW_LOCAL_TOKEN: z.string().optional(),
    AEGISFLOW_CONSOLE_PERSONA: z.string().optional(),
  })
  .passthrough();

function validatedHttpUrl(value: string, code: string): string {
  const url = new URL(value);
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error(code);
  }
  return url.toString().replace(/\/$/, "");
}

function loadLocalEnvironment(
  source: Record<string, string | undefined>,
): LocalConsoleEnvironment {
  const result = localSchema.safeParse(source);
  if (!result.success) {
    const personaIssue = result.error.issues.some(
      (issue) => issue.path[0] === "AEGISFLOW_CONSOLE_PERSONA",
    );
    throw new Error(personaIssue ? "console_persona_invalid" : "console_environment_invalid");
  }
  const values = result.data;
  return {
    authMode: "local_mvp",
    coreUrl: validatedHttpUrl(values.AEGISFLOW_CORE_URL, "core_url_invalid"),
    persona: values.AEGISFLOW_CONSOLE_PERSONA,
    token: values.AEGISFLOW_LOCAL_TOKEN,
    developerConsoleUrl: validatedHttpUrl(
      values.AEGISFLOW_DEVELOPER_CONSOLE_URL,
      "developer_console_url_invalid",
    ),
    reviewerConsoleUrl: validatedHttpUrl(
      values.AEGISFLOW_REVIEWER_CONSOLE_URL,
      "reviewer_console_url_invalid",
    ),
  };
}

function loadOidcEnvironment(
  source: Record<string, string | undefined>,
): OidcConsoleEnvironment {
  const result = oidcSchema.safeParse(source);
  if (!result.success) throw new Error("console_environment_invalid");
  const values = result.data;
  if (values.AEGISFLOW_LOCAL_TOKEN || values.AEGISFLOW_CONSOLE_PERSONA) {
    throw new Error("oidc_local_identity_conflict");
  }
  const consoleUrl = validatedHttpUrl(
    values.AEGISFLOW_CONSOLE_URL,
    "console_url_invalid",
  );
  const parsedConsoleUrl = new URL(consoleUrl);
  const isLoopback = ["localhost", "127.0.0.1", "[::1]"].includes(
    parsedConsoleUrl.hostname,
  );
  if (parsedConsoleUrl.protocol !== "https:" && !isLoopback) {
    throw new Error("console_url_insecure");
  }
  const issuer = validatedHttpUrl(
    values.AEGISFLOW_OIDC_ISSUER,
    "oidc_issuer_invalid",
  );
  const issuerUrl = new URL(issuer);
  const insecureIssuerIsLocal = ["localhost", "127.0.0.1", "[::1]"].includes(
    issuerUrl.hostname,
  );
  if (issuerUrl.protocol !== "https:" && !insecureIssuerIsLocal) {
    throw new Error("oidc_issuer_insecure");
  }
  const discoveryUrl = validatedHttpUrl(
    values.AEGISFLOW_OIDC_DISCOVERY_URL ??
      `${issuer}/.well-known/openid-configuration`,
    "oidc_discovery_url_invalid",
  );
  const discoveryEndpoint = new URL(discoveryUrl);
  if (
    discoveryEndpoint.protocol !== "https:" &&
    !(
      insecureIssuerIsLocal &&
      ["localhost", "127.0.0.1", "host.docker.internal", "keycloak"].includes(
        discoveryEndpoint.hostname,
      )
    )
  ) {
    throw new Error("oidc_discovery_url_insecure");
  }
  const secureCookies = parsedConsoleUrl.protocol === "https:";
  return {
    authMode: "oidc",
    coreUrl: validatedHttpUrl(values.AEGISFLOW_CORE_URL, "core_url_invalid"),
    consoleUrl,
    callbackUrl: `${consoleUrl}/api/auth/callback`,
    issuer,
    discoveryUrl,
    clientId: values.AEGISFLOW_OIDC_CLIENT_ID,
    clientSecret: values.AEGISFLOW_OIDC_CLIENT_SECRET,
    scope: values.AEGISFLOW_OIDC_SCOPE,
    sessionEncryptionKey: values.AEGISFLOW_SESSION_ENCRYPTION_KEY,
    sessionCookieName: secureCookies
      ? "__Host-aegisflow_session"
      : "aegisflow_session",
    transactionCookieName: secureCookies
      ? "__Host-aegisflow_login"
      : "aegisflow_login",
    secureCookies,
  };
}

export function loadConsoleEnvironment(
  source: Record<string, string | undefined> = process.env,
): ConsoleEnvironment {
  if (source.AEGISFLOW_AUTH_MODE === "oidc") return loadOidcEnvironment(source);
  return loadLocalEnvironment(source);
}

export function publicConsoleContext(config: ConsoleEnvironment) {
  if (config.authMode === "oidc") return { authMode: "oidc" as const };
  return {
    authMode: "local_mvp" as const,
    persona: config.persona,
    developerConsoleUrl: config.developerConsoleUrl,
    reviewerConsoleUrl: config.reviewerConsoleUrl,
  };
}

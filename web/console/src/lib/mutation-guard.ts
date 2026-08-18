import { verifyCsrfToken } from "./auth-session";

export class MutationGuardError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "MutationGuardError";
  }
}

interface OidcMutationConfig {
  authMode: "oidc";
  sessionEncryptionKey: string;
  sessionCookieName: string;
}

interface LocalMutationConfig {
  authMode: "local_mvp";
}

function requestCookie(request: Request, name: string): string | null {
  const matches = (request.headers.get("cookie") ?? "")
    .split(";")
    .map((entry) => entry.trim())
    .filter((entry) => entry.startsWith(`${name}=`));
  if (matches.length !== 1) return null;
  const value = matches[0]?.slice(name.length + 1) ?? "";
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

export function assertTrustedMutation(
  request: Request,
  config?: OidcMutationConfig | LocalMutationConfig,
): void {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0]?.trim();
  if (contentType !== "application/json") {
    throw new MutationGuardError("json_content_type_required");
  }

  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite && fetchSite !== "same-origin") {
    throw new MutationGuardError("cross_site_mutation_denied");
  }

  const origin = request.headers.get("origin");
  if (!origin) {
    throw new MutationGuardError("origin_required");
  }
  const requestUrl = new URL(request.url);
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",", 1)[0]?.trim();
  const forwardedProtocol = request.headers.get("x-forwarded-proto")?.split(",", 1)[0]?.trim();
  const host = forwardedHost || request.headers.get("host") || requestUrl.host;
  const protocol = forwardedProtocol || requestUrl.protocol.replace(":", "");
  if (origin !== `${protocol}://${host}`) {
    throw new MutationGuardError("cross_site_mutation_denied");
  }

  if (config?.authMode === "oidc") {
    const session = requestCookie(request, config.sessionCookieName);
    if (!session) throw new MutationGuardError("authentication_required");
    const csrf = request.headers.get("x-aegisflow-csrf") ?? "";
    if (!verifyCsrfToken(csrf, session, config.sessionEncryptionKey)) {
      throw new MutationGuardError("csrf_validation_failed");
    }
  }
}

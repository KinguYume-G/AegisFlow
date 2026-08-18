export class MutationGuardError extends Error {
  constructor(public readonly code: string) {
    super(code);
    this.name = "MutationGuardError";
  }
}

export function assertTrustedMutation(request: Request): void {
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
}

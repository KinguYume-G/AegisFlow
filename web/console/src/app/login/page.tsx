import Link from "next/link";
import { redirect } from "next/navigation";

import { loadConsoleEnvironment } from "@/lib/environment";

const allowedReasons = new Set([
  "authentication_required",
  "identity_provider_unavailable",
  "oidc_callback_failed",
  "session_expired",
  "signed_out",
]);

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ reason?: string; return_to?: string }>;
}) {
  const config = loadConsoleEnvironment();
  if (config.authMode !== "oidc") redirect("/");
  const query = await searchParams;
  const reason = allowedReasons.has(query.reason ?? "") ? query.reason : undefined;
  const returnTo =
    query.return_to?.startsWith("/") && !query.return_to.startsWith("//")
      ? query.return_to
      : "/";
  return (
    <div className="page-shell narrow-page">
      <section className="panel login-panel" aria-labelledby="login-title">
        <p className="eyebrow">Credential handoff</p>
        <h1 id="login-title">Sign in to AegisFlow</h1>
        <p>
          Authentication happens at the configured identity provider. AegisFlow receives a
          short-lived verified identity and stores only a revocable opaque session digest.
        </p>
        {reason && (
          <div className="notice notice--neutral" role="status">
            {reason === "signed_out"
              ? "Your AegisFlow session has been revoked."
              : "A valid sign-in is required. No requested side effect was retried."}
          </div>
        )}
        <dl className="scope-grid">
          <div><dt>Identity access</dt><dd>OpenID profile only</dd></div>
          <div><dt>Authority</dt><dd>Database tenant roles only</dd></div>
          <div className="scope-grid__wide"><dt>Agent boundary</dt><dd>Agents never receive your password or provider token</dd></div>
        </dl>
        <Link
          autoFocus
          className="button button--primary button--large"
          href={`/api/auth/login?return_to=${encodeURIComponent(returnTo)}`}
        >
          Continue to identity provider
        </Link>
      </section>
    </div>
  );
}

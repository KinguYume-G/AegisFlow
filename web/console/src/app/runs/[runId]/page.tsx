import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { z } from "zod";

import { RunLiveView } from "@/components/run-live-view";
import {
  CoreApiError,
  getConsoleCsrf,
  getRun,
  getSession,
} from "@/lib/core-client";
import { loadConsoleEnvironment } from "@/lib/environment";

export const metadata: Metadata = { title: "Run detail" };
const runIdSchema = z.string().uuid();

export default async function RunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const parsed = runIdSchema.safeParse(runId);
  if (!parsed.success) notFound();
  let loaded: Awaited<ReturnType<typeof Promise.all<[
    ReturnType<typeof getRun>,
    ReturnType<typeof getSession>,
    ReturnType<typeof getConsoleCsrf>,
  ]>>>;
  try {
    loaded = await Promise.all([
      getRun(parsed.data),
      getSession(),
      getConsoleCsrf(),
    ]);
  } catch (error) {
    if (error instanceof CoreApiError && error.status === 404) notFound();
    if (error instanceof CoreApiError && error.status === 401) {
      redirect(
        `/login?reason=authentication_required&return_to=${encodeURIComponent(`/runs/${runId}`)}`,
      );
    }
    const failureCode = error instanceof CoreApiError ? error.code : "run_unavailable";
    return <RunFailure code={failureCode} />;
  }
  const [detail, session, csrf] = loaded;
  const tenant = session.tenants.find(
    (candidate) => candidate.tenant_id === detail.summary.tenant_id,
  );
  if (!tenant) notFound();
  const config = loadConsoleEnvironment();
  return (
    <RunLiveView
      initial={detail}
      capabilities={tenant.capabilities}
      csrf={csrf}
      reviewerConsoleUrl={
        config.authMode === "local_mvp" ? config.reviewerConsoleUrl : undefined
      }
    />
  );
}

function RunFailure({ code }: { code: string }) {
  return (
    <div className="page-shell">
      <div className="connection-error">
        <span>Run unavailable</span><h1>Could not load confirmed Run state</h1>
        <p>Refresh after the Core service is healthy.</p><code>{code}</code>
      </div>
    </div>
  );
}

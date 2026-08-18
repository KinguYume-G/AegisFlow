import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { z } from "zod";

import { RunLiveView } from "@/components/run-live-view";
import { CoreApiError, getRun } from "@/lib/core-client";
import { loadConsoleEnvironment, publicConsoleContext } from "@/lib/environment";

export const metadata: Metadata = { title: "Run detail" };
const runIdSchema = z.string().uuid();

export default async function RunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const parsed = runIdSchema.safeParse(runId);
  if (!parsed.success) notFound();
  let detail: Awaited<ReturnType<typeof getRun>> | null = null;
  let context: ReturnType<typeof publicConsoleContext> | null = null;
  let failureCode = "run_unavailable";
  try {
    [detail, context] = await Promise.all([
      getRun(parsed.data),
      Promise.resolve(publicConsoleContext(loadConsoleEnvironment())),
    ]);
  } catch (error) {
    if (error instanceof CoreApiError && error.status === 404) notFound();
    failureCode = error instanceof CoreApiError ? error.code : failureCode;
  }
  if (!detail || !context) {
    return <div className="page-shell"><div className="connection-error"><span>Run unavailable</span><h1>Could not load confirmed Run state</h1><p>Refresh after the Core service is healthy.</p><code>{failureCode}</code></div></div>;
  }
  return <RunLiveView initial={detail} persona={context.persona} reviewerConsoleUrl={context.reviewerConsoleUrl} />;
}

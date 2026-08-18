"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ApprovalPanel } from "./approval-panel";
import { ClarificationPanel } from "./clarification-panel";
import { RunTimeline } from "./run-timeline";
import { StatusPill } from "./status-pill";
import type { RunDetail } from "@/lib/contracts";
import { formatCost, formatDate, formatDuration, formatTokenCount, shortId } from "@/lib/format";

interface RunLiveViewProps {
  initial: RunDetail;
  capabilities: string[];
  csrf: string | null;
  reviewerConsoleUrl?: string;
}

const TERMINAL = new Set(["completed", "failed", "rejected", "cancelled"]);

function errorCode(payload: unknown): string {
  if (
    typeof payload === "object" && payload !== null && "error" in payload &&
    typeof payload.error === "object" && payload.error !== null && "code" in payload.error &&
    typeof payload.error.code === "string"
  ) return payload.error.code;
  return "request_failed";
}

export function RunLiveView({ initial, capabilities, csrf, reviewerConsoleUrl }: RunLiveViewProps) {
  const [detail, setDetail] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const runId = detail.summary.run_id;
  const canClarify = capabilities.includes("run:execute");
  const canDecide = capabilities.includes("approval:decide");

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(`/api/runs/${encodeURIComponent(runId)}`, {
        cache: "no-store",
      });
      const payload: unknown = await response.json();
      if (!response.ok) throw new Error(errorCode(payload));
      setDetail(payload as RunDetail);
      setStale(false);
    } catch {
      setStale(true);
    }
  }, [runId]);

  useEffect(() => {
    if (TERMINAL.has(detail.summary.status)) return;
    const timer = window.setInterval(refresh, 2500);
    return () => window.clearInterval(timer);
  }, [detail.summary.status, refresh]);

  const totals = useMemo(() => {
    let input = 0;
    let output = 0;
    let cost = 0;
    let measuredTokens = false;
    let measuredCost = false;
    for (const trace of detail.traces) {
      const inputValue = trace.token_usage.input_tokens.value;
      const outputValue = trace.token_usage.output_tokens.value;
      const costValue = trace.cost_usage.amount;
      if (inputValue != null) { input += inputValue; measuredTokens = true; }
      if (outputValue != null) { output += outputValue; measuredTokens = true; }
      if (costValue != null) { cost += costValue; measuredCost = true; }
    }
    return { input: measuredTokens ? input : null, output: measuredTokens ? output : null, cost: measuredCost ? cost : null };
  }, [detail.traces]);

  async function mutate(path: string, body: unknown, success: string) {
    setBusy(true);
    setNotice(null);
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(csrf ? { "x-aegisflow-csrf": csrf } : {}),
        },
        body: JSON.stringify(body),
      });
      const payload: unknown = await response.json();
      if (!response.ok) throw new Error(errorCode(payload));
      setNotice(success);
      await refresh();
    } catch (cause) {
      setNotice(`Action failed: ${cause instanceof Error ? cause.message : "request_failed"}`);
    } finally {
      setBusy(false);
    }
  }

  const pending = detail.pending_action;
  const repository = `${detail.request.repository.owner}/${detail.request.repository.name}`;

  return (
    <div className="page-shell run-page">
      <div className="run-breadcrumb"><Link href="/">Runs</Link><span>/</span><span>{shortId(runId)}</span></div>
      <section className="run-hero">
        <div className="run-hero__main">
          <div className="run-title-line"><StatusPill status={detail.summary.status} /><span className="mono">RUN-{shortId(runId).toUpperCase()}</span></div>
          <h1>{detail.summary.title}</h1>
          <p>{repository} <span>·</span> {detail.request.repository.base_ref} <span>·</span> created {formatDate(detail.summary.created_at)}</p>
        </div>
        <div className="run-hero__authority">
          <small>Active authority</small><b>{canDecide ? "Human Reviewer" : "Developer"}</b>
          <span>{canDecide ? "May decide exact approvals" : "May create and clarify Runs"}</span>
        </div>
      </section>

      {stale && <div className="notice notice--warning" role="status">Live refresh is temporarily unavailable. Displaying the last confirmed state.</div>}
      {notice && <div className={`notice ${notice.startsWith("Action failed") ? "notice--error" : "notice--success"}`} role="status">{notice}</div>}
      {detail.summary.status === "completed" && (
        <div className="completion-banner"><span>✓</span><div><b>Governed Run completed</b><p>Evidence and a dry-run Draft PR candidate were recorded. No GitHub repository was changed.</p></div></div>
      )}

      <section className="run-layout">
        <div className="run-primary">
          <div className="panel timeline-panel">
            <div className="panel-heading"><div><p className="eyebrow">Durable execution</p><h2>Run lifecycle</h2></div><span>{detail.steps.filter((step) => step.status === "completed").length} / 10 complete</span></div>
            <RunTimeline steps={detail.steps} runStatus={detail.summary.status} />
          </div>

          {pending?.kind === "clarification" && (
            <ClarificationPanel
              canClarify={canClarify}
              questions={pending.questions}
              submitting={busy}
              onSubmit={(answers) => mutate(
                `/api/runs/${runId}/clarifications/${pending.request_id}`,
                { answers },
                "Clarification accepted. Temporal will resume the same Run.",
              )}
            />
          )}
          {pending?.kind === "approval" && (
            <>
              <ApprovalPanel
                pending={pending}
                canDecide={canDecide}
                submitting={busy}
                onDecision={(decision, reason) => mutate(
                  `/api/runs/${runId}/approvals/${pending.request_id}`,
                  { decision, ...(reason ? { reason } : {}) },
                  `${decision === "approved" ? "Approval" : "Rejection"} accepted. Temporal will resume the same Run.`,
                )}
              />
              {!canDecide && reviewerConsoleUrl && (
                <a className="reviewer-handoff" href={`${reviewerConsoleUrl}/runs/${runId}`} rel="noreferrer" target="_blank">
                  <span>◇</span><div><b>Independent review required</b><p>Open this exact Run in the isolated Reviewer console.</p></div><strong>Open Reviewer ↗</strong>
                </a>
              )}
            </>
          )}

          <section className="panel evidence-panel" id="evidence">
            <div className="panel-heading"><div><p className="eyebrow">Evidence over claims</p><h2>Artifacts</h2></div><span>{detail.artifacts.length} records</span></div>
            {detail.artifacts.length === 0 ? <p className="empty-copy">Artifacts appear as Agent steps complete.</p> : (
              <div className="artifact-grid">
                {detail.artifacts.map((artifact) => (
                  <details className="artifact-card" key={`${artifact.kind}-${artifact.content_digest}`}>
                    <summary><span>{artifact.kind.replaceAll("_", " ")}</span><code>{artifact.content_digest.slice(0, 10)}</code></summary>
                    <pre>{JSON.stringify(artifact.payload, null, 2)}</pre>
                  </details>
                ))}
              </div>
            )}
          </section>

          <section className="panel trace-panel">
            <div className="panel-heading"><div><p className="eyebrow">Step-level observability</p><h2>Agent traces</h2></div><span>{detail.traces.length} spans</span></div>
            <div className="table-scroll"><table><thead><tr><th>Agent</th><th>Model</th><th>Latency</th><th>Tokens</th><th>Cost</th></tr></thead>
              <tbody>{detail.traces.map((trace) => <tr key={trace.event_id}><td><b>{trace.agent}</b></td><td className="mono">{trace.model}</td><td>{formatDuration(trace.latency_ms)}</td><td>{formatTokenCount(trace.token_usage.total_tokens.value)}</td><td>{formatCost(trace.cost_usage.amount)}</td></tr>)}</tbody>
            </table></div>
            {detail.traces.length === 0 && <p className="empty-copy">No trace evidence has been recorded yet.</p>}
          </section>
        </div>

        <aside className="run-secondary">
          <section className="panel run-metrics">
            <p className="eyebrow">Measured usage</p><h2>Run telemetry</h2>
            <dl><div><dt>Input tokens</dt><dd>{formatTokenCount(detail.evaluation?.input_tokens ?? totals.input)}</dd></div><div><dt>Output tokens</dt><dd>{formatTokenCount(detail.evaluation?.output_tokens ?? totals.output)}</dd></div><div><dt>Model cost</dt><dd>{formatCost(detail.evaluation?.cost_usd ?? totals.cost)}</dd></div><div><dt>Tool success</dt><dd>{detail.evaluation ? `${(detail.evaluation.tool_success_rate * 100).toFixed(0)}%` : "Pending"}</dd></div></dl>
          </section>

          <section className="panel evaluation-card">
            <p className="eyebrow">Evaluation</p>
            {detail.evaluation ? <><div className={`score-ring ${detail.evaluation.task_success ? "score-ring--pass" : "score-ring--fail"}`}><b>{detail.evaluation.task_success ? "PASS" : "FAIL"}</b><span>{detail.evaluation.completed_steps}/{detail.evaluation.total_steps} steps</span></div><p>Outcome: <b>{detail.evaluation.outcome}</b></p></> : <div className="pending-evaluation"><span>◎</span><p>Final evaluation runs after the governed effect completes.</p></div>}
          </section>

          <section className="panel request-card">
            <p className="eyebrow">Immutable request</p><h2>{detail.request.source_type.toUpperCase()}</h2>
            <p className="request-body">{detail.request.body}</p>
            <dl className="compact-list"><div><dt>Base SHA</dt><dd className="mono">{detail.request.repository.base_sha.slice(0, 12)}</dd></div><div><dt>Requested by</dt><dd>{detail.summary.requested_by.split("|").at(-1)}</dd></div></dl>
          </section>

          <section className="panel audit-card">
            <p className="eyebrow">Append-only audit</p><h2>Decisions</h2>
            {detail.approvals.map((approval) => <div className="audit-row" key={approval.approval_id}><span className={`audit-dot audit-dot--${approval.decision}`} /><div><b>Human approval · {approval.decision}</b><small>{approval.decided_by ?? "Pending reviewer"}</small>{approval.action_digest && <code>{approval.action_digest.slice(0, 12)}</code>}</div></div>)}
            {detail.audit.map((event) => <div className="audit-row" key={event.event_id}><span className={`audit-dot audit-dot--${event.decision}`} /><div><b>{event.action} · {event.decision}</b><small>{event.actor}</small></div></div>)}
            {detail.approvals.length + detail.audit.length === 0 && <p className="empty-copy">No governed decision recorded yet.</p>}
          </section>
        </aside>
      </section>
    </div>
  );
}

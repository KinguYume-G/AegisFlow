import Link from "next/link";
import { redirect } from "next/navigation";

import { LogoutButton } from "@/components/logout-button";
import { StatusPill } from "@/components/status-pill";
import { CoreApiError, getDashboardData } from "@/lib/core-client";
import { formatDate, shortId } from "@/lib/format";

export default async function DashboardPage() {
  let loaded: Awaited<ReturnType<typeof getDashboardData>> | null = null;
  let failureCode = "console_unavailable";
  try {
    loaded = await getDashboardData();
  } catch (error) {
    if (error instanceof CoreApiError && error.status === 401) {
      redirect("/login?reason=authentication_required");
    }
    failureCode = error instanceof CoreApiError ? error.code : failureCode;
  }
  if (!loaded) {
    return (
      <div className="page-shell"><div className="connection-error"><span>Disconnected</span><h1>Control plane is not reachable</h1><p>Start the local Compose profile, then refresh this page.</p><code>{failureCode}</code></div></div>
    );
  }

    const { session, tenant, profile, runs, csrf } = loaded;
    const waiting = runs.items.filter((run) => run.status.startsWith("waiting_")).length;
    const active = runs.items.filter((run) => ["pending", "running"].includes(run.status)).length;
    const completed = runs.items.filter((run) => run.status === "completed").length;
    const failed = runs.items.filter((run) => run.status === "failed").length;
    const canCreate = tenant.capabilities.includes("run:execute");

    return (
      <div className="page-shell">
        <section className="hero-panel">
          <div>
            <p className="eyebrow">Control plane / {tenant.slug}</p>
            <h1>Software delivery,<br /><em>under control.</em></h1>
            <p className="hero-copy">Every Agent step is bounded by durable state, deterministic policy, isolated execution and Human authority.</p>
            {canCreate && <Link className="button button--primary button--large" href="/runs/new">＋ Start a Run</Link>}
          </div>
          {csrf && <LogoutButton csrf={csrf} />}
          <div className="architecture-orbit" aria-label="Active local architecture">
            <span className="orbit orbit--one" /><span className="orbit orbit--two" />
            <div className="orbit-core"><b>10</b><small>governed steps</small></div>
            <div className="orbit-node orbit-node--a">Temporal</div>
            <div className="orbit-node orbit-node--b">LangGraph</div>
            <div className="orbit-node orbit-node--c">Sandbox</div>
          </div>
        </section>

        <section className="metric-grid" aria-label="Run status summary">
          <article><span className="metric-icon metric-icon--blue">↻</span><div><small>Active</small><strong>{active}</strong></div><em>Executing now</em></article>
          <article><span className="metric-icon metric-icon--amber">◇</span><div><small>Needs attention</small><strong>{waiting}</strong></div><em>Human checkpoint</em></article>
          <article><span className="metric-icon metric-icon--green">✓</span><div><small>Completed</small><strong>{completed}</strong></div><em>Evidence ready</em></article>
          <article><span className="metric-icon metric-icon--red">!</span><div><small>Failed</small><strong>{failed}</strong></div><em>Review required</em></article>
        </section>

        <section className="content-grid">
          <div className="panel panel--runs">
            <div className="panel-heading"><div><p className="eyebrow">Recent activity</p><h2>Delivery Runs</h2></div><span>{runs.items.length} total</span></div>
            {runs.items.length === 0 ? (
              <div className="empty-state"><span>⌁</span><h3>No Runs yet</h3><p>Create a PRD Run to exercise the governed delivery loop.</p></div>
            ) : (
              <div className="run-list">
                {runs.items.map((run) => (
                  <Link className="run-row" href={`/runs/${run.run_id}`} key={run.run_id}>
                    <span className={`run-row__signal run-row__signal--${run.status}`} />
                    <span className="run-row__main"><b>{run.title}</b><small>{run.source_type.toUpperCase()} · {shortId(run.run_id)} · {formatDate(run.created_at)}</small></span>
                    <StatusPill status={run.status} /><span className="run-row__arrow">→</span>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <aside className="panel governance-panel" id="governance">
            <p className="eyebrow">Runtime posture</p><h2>Governance is active</h2>
            <ul className="posture-list">
              <li><span>Identity</span><b>{session.profile === "local_mvp" ? "Two local actors" : "OIDC"}</b></li>
              <li><span>Model</span><b>{profile.model_mode === "ollama" ? "Local Ollama" : "Disabled"}</b></li>
              <li><span>GitHub effect</span><b>{profile.github_effect_mode === "dry_run" ? "Dry-run only" : "Enabled"}</b></li>
              <li><span>Authority</span><b>Human decides</b></li>
            </ul>
            <div className="governance-rule"><span>Policy #1</span><p>Agents may propose and test. They cannot grant their own authority.</p></div>
          </aside>
        </section>
      </div>
    );
}

"use client";

import { useState } from "react";

import type { PendingApproval } from "@/lib/contracts";

interface ApprovalPanelProps {
  pending: PendingApproval;
  canDecide: boolean;
  onDecision: (decision: "approved" | "rejected", reason?: string) => void | Promise<void>;
  submitting?: boolean;
}

export function ApprovalPanel({ pending, canDecide, onDecision, submitting = false }: ApprovalPanelProps) {
  const [acknowledged, setAcknowledged] = useState(false);
  const [reason, setReason] = useState("");
  const preview = pending.action_preview;

  return (
    <section className="approval-card" aria-labelledby="approval-title">
      <div className="approval-card__heading">
        <div>
          <p className="eyebrow">Human governance checkpoint</p>
          <h2 id="approval-title">Exact action approval</h2>
        </div>
        <span className={`effect-badge effect-badge--${preview.effect_mode}`}>
          {preview.effect_mode === "dry_run" ? "Dry-run · no GitHub write" : "GitHub side effect"}
        </span>
      </div>

      <p className="muted">{pending.reason ?? "A separate reviewer must authorize this action."}</p>

      <dl className="scope-grid">
        <div><dt>Effect</dt><dd>{preview.effect}</dd></div>
        <div><dt>Repository</dt><dd>{preview.repository}</dd></div>
        <div><dt>Base</dt><dd>{preview.base_ref} · {preview.base_sha.slice(0, 10)}</dd></div>
        <div><dt>Risk</dt><dd>{preview.risk}</dd></div>
        <div className="scope-grid__wide"><dt>Branch</dt><dd>{preview.branch_name}</dd></div>
        <div className="scope-grid__wide"><dt>Changed paths</dt><dd>{preview.changed_files.join(", ")}</dd></div>
        <div className="scope-grid__wide"><dt>Action digest</dt><dd className="mono digest">{pending.action_digest}</dd></div>
        <div className="scope-grid__wide"><dt>Content digest</dt><dd className="mono digest">{preview.content_digest}</dd></div>
      </dl>

      {!canDecide ? (
        <div className="notice notice--neutral" role="note">
          Your current tenant role cannot decide this approval. A separate authorized Human must review it.
        </div>
      ) : (
        <div className="decision-area">
          <label className="field">
            <span>Decision note <span className="muted">(optional)</span></span>
            <textarea value={reason} onChange={(event) => setReason(event.target.value)} maxLength={4096} rows={3} />
          </label>
          <label className="acknowledgement">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
            />
            <span>I reviewed the exact action, repository scope, changed paths and digest shown above.</span>
          </label>
          <div className="decision-actions">
            <button
              type="button"
              className="button button--secondary"
              disabled={submitting}
              onClick={() => onDecision("rejected", reason.trim() || undefined)}
            >
              Reject safely
            </button>
            <button
              type="button"
              className="button button--primary"
              disabled={!acknowledged || submitting}
              onClick={() => onDecision("approved", reason.trim() || undefined)}
            >
              Approve exact action
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

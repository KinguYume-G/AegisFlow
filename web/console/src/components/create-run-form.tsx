"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

interface FormState {
  sourceType: "prd" | "issue" | "bug";
  sourceRef: string;
  title: string;
  body: string;
  owner: string;
  repository: string;
  baseRef: string;
  baseSha: string;
}

const initial: FormState = {
  sourceType: "prd",
  sourceRef: "",
  title: "",
  body: "",
  owner: "KinguYume-G",
  repository: "AegisFlow",
  baseRef: "main",
  baseSha: "",
};

export function CreateRunForm({ csrf }: { csrf: string | null }) {
  const router = useRouter();
  const [form, setForm] = useState(initial);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update<Key extends keyof FormState>(key: Key, value: FormState[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/runs", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(csrf ? { "x-aegisflow-csrf": csrf } : {}),
        },
        body: JSON.stringify({
          source_type: form.sourceType,
          source_ref: form.sourceRef.trim() || null,
          title: form.title.trim(),
          body: form.body.trim(),
          repository: {
            owner: form.owner.trim(),
            name: form.repository.trim(),
            base_ref: form.baseRef.trim(),
            base_sha: form.baseSha.trim().toLowerCase(),
          },
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.error?.code ?? "run_creation_failed");
      }
      router.push(`/runs/${encodeURIComponent(payload.summary.run_id)}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "run_creation_failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="run-form" onSubmit={submit}>
      <section className="form-section">
        <div className="section-heading">
          <span className="section-number">01</span>
          <div><h2>Delivery request</h2><p>Describe the outcome and acceptance boundary.</p></div>
        </div>
        <div className="field-grid field-grid--two">
          <label className="field"><span>Source type</span>
            <select value={form.sourceType} onChange={(event) => update("sourceType", event.target.value as FormState["sourceType"])}>
              <option value="prd">PRD</option><option value="issue">GitHub Issue</option><option value="bug">Bug</option>
            </select>
          </label>
          <label className="field"><span>Source reference <i>optional</i></span>
            <input maxLength={2048} value={form.sourceRef} onChange={(event) => update("sourceRef", event.target.value)} placeholder="https://github.com/org/repo/issues/123" />
          </label>
        </div>
        <label className="field"><span>Run title</span>
          <input required minLength={1} maxLength={200} value={form.title} onChange={(event) => update("title", event.target.value)} placeholder="Implement deterministic delivery status" />
        </label>
        <label className="field"><span>Requirements and acceptance criteria</span>
          <textarea required minLength={20} maxLength={50_000} rows={10} value={form.body} onChange={(event) => update("body", event.target.value)} placeholder="Explain the desired behavior, constraints, tests and non-goals…" />
          <small>{form.body.length.toLocaleString()} / 50,000</small>
        </label>
      </section>

      <section className="form-section">
        <div className="section-heading">
          <span className="section-number">02</span>
          <div><h2>Repository scope</h2><p>Bind execution to one exact repository baseline.</p></div>
        </div>
        <div className="field-grid field-grid--two">
          <label className="field"><span>Owner</span><input required pattern="[A-Za-z0-9_.\-]+" maxLength={100} value={form.owner} onChange={(event) => update("owner", event.target.value)} /></label>
          <label className="field"><span>Repository</span><input required pattern="[A-Za-z0-9_.\-]+" maxLength={100} value={form.repository} onChange={(event) => update("repository", event.target.value)} /></label>
          <label className="field"><span>Base ref</span><input required maxLength={255} value={form.baseRef} onChange={(event) => update("baseRef", event.target.value)} /></label>
          <label className="field"><span>Base commit SHA</span><input className="mono" required pattern="[0-9a-fA-F]{40}" minLength={40} maxLength={40} value={form.baseSha} onChange={(event) => update("baseSha", event.target.value)} placeholder="40-character commit SHA" /></label>
        </div>
      </section>

      <div className="effect-preview">
        <span className="effect-preview__icon">⌁</span>
        <div><b>Local governed execution</b><p>Ollama may propose code and the sandbox may test it. The final GitHub effect is a dry-run candidate only.</p></div>
        <span className="effect-badge effect-badge--dry_run">No GitHub write</span>
      </div>
      {error && <div className="notice notice--error" role="alert">Could not create Run: {error}</div>}
      <div className="form-actions">
        <button className="button button--primary button--large" disabled={submitting} type="submit">
          {submitting ? "Creating durable Run…" : "Create governed Run"}
        </button>
      </div>
    </form>
  );
}

"use client";

import { useState, type FormEvent } from "react";

interface ClarificationPanelProps {
  questions: Array<{
    field: string;
    question: string;
    schema_version: number;
  }>;
  canClarify: boolean;
  onSubmit: (answers: Record<string, string>) => void | Promise<void>;
  submitting?: boolean;
}

export function ClarificationPanel({
  questions,
  canClarify,
  onSubmit,
  submitting = false,
}: ClarificationPanelProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(answers);
  }

  return (
    <section className="approval-card" aria-labelledby="clarification-title">
      <p className="eyebrow">Human context checkpoint</p>
      <h2 id="clarification-title">Clarification required</h2>
      <p className="muted">The Agent paused rather than inventing missing delivery requirements.</p>
      {!canClarify ? (
        <div className="notice notice--neutral" role="note">
          Your current tenant role cannot answer this Run&apos;s clarification request.
        </div>
      ) : (
        <form className="clarification-form" onSubmit={submit}>
          {questions.map((item, index) => (
            <label className="field" key={`${item.schema_version}:${item.field}`}>
              <span><b>{index + 1}.</b> {item.question}</span>
              <textarea
                aria-label={item.question}
                required
                minLength={1}
                maxLength={8192}
                rows={3}
                value={answers[item.field] ?? ""}
                onChange={(event) =>
                  setAnswers((current) => ({ ...current, [item.field]: event.target.value }))
                }
              />
            </label>
          ))}
          <button className="button button--primary" disabled={submitting} type="submit">
            {submitting ? "Submitting…" : "Submit answers & resume Run"}
          </button>
        </form>
      )}
    </section>
  );
}

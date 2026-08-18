import type { RunDetail } from "@/lib/contracts";
import { statusLabel } from "@/lib/format";

const CANONICAL_STEPS = [
  ["intake", "Intake"],
  ["clarifier", "Clarifier"],
  ["context", "Context"],
  ["planner", "Planner"],
  ["policy_gate", "Policy gate"],
  ["executor", "Executor"],
  ["reviewer", "Reviewer"],
  ["human_approval", "Human approval"],
  ["draft_pr", "Draft PR candidate"],
  ["evaluation", "Evaluation"],
] as const;

interface RunTimelineProps {
  steps: RunDetail["steps"];
  runStatus: string;
}

export function RunTimeline({ steps, runStatus }: RunTimelineProps) {
  const byName = new Map(steps.map((step) => [step.name, step]));

  return (
    <ol className="run-timeline" aria-label="Run execution timeline">
      {CANONICAL_STEPS.map(([name, label], index) => {
        const step = byName.get(name);
        let status = step?.status ?? "pending";
        if (name === "human_approval" && runStatus === "waiting_approval") status = "waiting";
        if (name === "clarifier" && runStatus === "waiting_clarification") status = "waiting";
        return (
          <li className={`run-step run-step--${status}`} key={name}>
            <span className="step-index" aria-hidden="true">{index + 1}</span>
            <span className="step-copy">
              <strong>{label}</strong>
              <span className="step-status">{statusLabel(status)}</span>
            </span>
            <span className="step-marker" aria-hidden="true" />
          </li>
        );
      })}
    </ol>
  );
}

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApprovalPanel } from "./approval-panel";

const pending = {
  kind: "approval" as const,
  request_id: "11111111-1111-4111-8111-111111111111",
  action_digest: "b".repeat(64),
  reason: "External repository side effect requires a separate reviewer.",
  action_preview: {
    effect: "create_draft_pr_candidate",
    effect_mode: "dry_run" as const,
    repository: "KinguYume-G/AegisFlow",
    base_ref: "main",
    base_sha: "a".repeat(40),
    branch_name: "aegisflow/run-example",
    changed_files: ["app.py"],
    content_digest: "c".repeat(64),
    risk: "high",
  },
};

describe("ApprovalPanel", () => {
  it("keeps the action read-only for the developer actor", () => {
    render(<ApprovalPanel pending={pending} persona="developer" onDecision={vi.fn()} />);

    expect(screen.getByText("KinguYume-G/AegisFlow")).toBeInTheDocument();
    expect(screen.getByText(/dry-run/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });

  it("requires exact-scope acknowledgement before reviewer approval", async () => {
    const user = userEvent.setup();
    const onDecision = vi.fn();
    render(<ApprovalPanel pending={pending} persona="reviewer" onDecision={onDecision} />);

    const approve = screen.getByRole("button", { name: /approve exact action/i });
    expect(approve).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /reviewed the exact action/i }));
    expect(approve).toBeEnabled();
    await user.click(approve);
    expect(onDecision).toHaveBeenCalledWith("approved", undefined);
  });
});

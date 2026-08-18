import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ClarificationPanel } from "./clarification-panel";

describe("ClarificationPanel", () => {
  it("submits answers keyed by the stable backend field", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <ClarificationPanel
        questions={[
          {
            field: "acceptance_criteria",
            question: "What is the expected behavior?",
            schema_version: 1,
          },
        ]}
        canClarify
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText("What is the expected behavior?"), "Return ok.");
    await user.click(screen.getByRole("button", { name: /resume run/i }));
    expect(onSubmit).toHaveBeenCalledWith({ acceptance_criteria: "Return ok." });
  });

  it("is read-only for the reviewer", () => {
    render(
      <ClarificationPanel
        questions={[{ field: "missing", question: "What is missing?", schema_version: 1 }]}
        canClarify={false}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: /resume run/i })).not.toBeInTheDocument();
  });
});

import path from "node:path";

import { expect, test } from "@playwright/test";

test("Developer and Reviewer complete one governed local Run", async ({ browser, page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "full workflow runs once");
  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      browserErrors.push(`${message.location().url || "unknown"}: ${message.text()}`);
    }
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Software delivery, under control." })).toBeVisible();
  await expect(page.getByText("Local MVP connected")).toBeVisible();
  await page.screenshot({ path: path.resolve("test-results/dashboard-desktop.png"), fullPage: true });

  const resumeRunId = process.env.AEGISFLOW_E2E_RUN_ID;
  let runId: string;
  if (resumeRunId) {
    expect(resumeRunId).toMatch(/^[0-9a-f]{8}-[0-9a-f-]{27}$/);
    runId = resumeRunId;
    await page.goto(`/runs/${runId}`);
  } else {
    await page.getByRole("link", { name: "＋ Start a Run" }).click();
    await page.getByLabel("Run title").fill("Browser verified deterministic delivery status");
    await page.getByLabel("Requirements and acceptance criteria").fill(
      "Create app.py with a deterministic delivery_status function returning ok. Add a standard-library unittest that asserts the exact value. Do not add dependencies. Acceptance requires the isolated test command to pass.",
    );
    await page.getByLabel("Base commit SHA").fill("a".repeat(40));
    await page.getByRole("button", { name: "Create governed Run" }).click();
    await expect(page).toHaveURL(/\/runs\/[0-9a-f-]{36}$/);
    runId = page.url().split("/").at(-1)!;
  }

  const approvalHeading = page.getByRole("heading", { name: "Exact action approval" });
  const clarificationHeading = page.getByRole("heading", { name: "Clarification required" });
  const completedStatus = page.getByText("Governed Run completed");
  await expect(approvalHeading.or(clarificationHeading).or(completedStatus)).toBeVisible({
    timeout: 150_000,
  });
  if (await clarificationHeading.isVisible()) {
    const answers = page.locator(".clarification-form textarea");
    const answerCount = await answers.count();
    for (let index = 0; index < answerCount; index += 1) {
      await answers.nth(index).fill(
        "Use Python 3.12 standard library only; app.py is the allowed path; exact output is ok; python -m unittest must pass; no external side effect.",
      );
    }
    await page.getByRole("button", { name: "Submit answers & resume Run" }).click();
    await expect(approvalHeading).toBeVisible({ timeout: 150_000 });
  }

  await expect(page.getByRole("button", { name: "Approve exact action" })).toHaveCount(0);

  const reviewer = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await reviewer.goto(`http://127.0.0.1:3001/runs/${runId}`);
  await expect(reviewer.getByText("Human Reviewer")).toBeVisible();
  const reviewerCompleted = reviewer.getByText("Governed Run completed");
  if (!(await reviewerCompleted.isVisible())) {
    await expect(page.getByText("Dry-run · no GitHub write")).toBeVisible();
    await expect(reviewer.getByRole("heading", { name: "Exact action approval" })).toBeVisible();
    const approve = reviewer.getByRole("button", { name: "Approve exact action" });
    await expect(approve).toBeDisabled();
    await reviewer
      .getByRole("checkbox", {
        name: "I reviewed the exact action, repository scope, changed paths and digest shown above.",
      })
      .check();
    await expect(approve).toBeEnabled();
    await approve.click();
  }
  await expect(reviewerCompleted).toBeVisible({ timeout: 150_000 });
  await expect(reviewer.getByText("10 / 10 complete")).toBeVisible();
  await expect(reviewer.getByText("PASS", { exact: true })).toBeVisible();
  await reviewer.screenshot({ path: path.resolve("test-results/run-completed-desktop.png"), fullPage: true });
  await reviewer.close();

  expect(browserErrors).toEqual([]);
});

test("mobile dashboard is readable without horizontal overflow", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "mobile-only visual check");
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Software delivery, under control." })).toBeVisible();
  const dimensions = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: window.innerWidth }));
  expect(dimensions.width).toBeLessThanOrEqual(dimensions.viewport);
  await page.screenshot({ path: path.resolve("test-results/dashboard-mobile.png"), fullPage: true });
});

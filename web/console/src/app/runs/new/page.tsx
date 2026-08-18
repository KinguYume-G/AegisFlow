import type { Metadata } from "next";

import { CreateRunForm } from "@/components/create-run-form";
import { loadConsoleEnvironment } from "@/lib/environment";

export const metadata: Metadata = { title: "New Run" };

export default function NewRunPage() {
  const config = loadConsoleEnvironment();
  if (config.persona !== "developer") {
    return (
      <div className="page-shell narrow-page">
        <div className="notice notice--neutral"><b>Reviewer console is read-only.</b><br />Create and clarify Runs from the Developer console.</div>
      </div>
    );
  }
  return (
    <div className="page-shell narrow-page">
      <div className="page-heading">
        <div><p className="eyebrow">New durable workflow</p><h1>Launch a delivery Run</h1></div>
        <p>One request becomes a recoverable, traceable ten-step software delivery workflow.</p>
      </div>
      <CreateRunForm />
    </div>
  );
}

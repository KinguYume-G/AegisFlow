import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { CreateRunForm } from "@/components/create-run-form";
import { CoreApiError, getConsoleCsrf, getSession } from "@/lib/core-client";

export const metadata: Metadata = { title: "New Run" };

export default async function NewRunPage() {
  let session: Awaited<ReturnType<typeof getSession>>;
  let csrf: string | null;
  try {
    [session, csrf] = await Promise.all([getSession(), getConsoleCsrf()]);
  } catch (error) {
    if (error instanceof CoreApiError && error.status === 401) {
      redirect("/login?reason=authentication_required&return_to=/runs/new");
    }
    throw error;
  }
  const tenant = session.tenants[0];
  if (!tenant?.capabilities.includes("run:execute")) {
    return (
      <div className="page-shell narrow-page">
        <div className="notice notice--neutral">
          <b>Your tenant role is read-only for Run creation.</b><br />
          Ask a tenant administrator for the Developer capability if this task requires it.
        </div>
      </div>
    );
  }
  return (
    <div className="page-shell narrow-page">
      <div className="page-heading">
        <div><p className="eyebrow">New durable workflow</p><h1>Launch a delivery Run</h1></div>
        <p>One request becomes a recoverable, traceable ten-step software delivery workflow.</p>
      </div>
      <CreateRunForm csrf={csrf} />
    </div>
  );
}

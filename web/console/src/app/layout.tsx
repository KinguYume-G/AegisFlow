import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { BrandMark } from "@/components/brand-mark";
import { loadConsoleEnvironment, publicConsoleContext } from "@/lib/environment";

import "./globals.css";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: { default: "AegisFlow Control Plane", template: "%s · AegisFlow" },
  description: "Governed AI software delivery Runs, evidence and Human approvals.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const context = publicConsoleContext(loadConsoleEnvironment());
  const isDeveloper = context.persona === "developer";
  const counterpartUrl = isDeveloper
    ? context.reviewerConsoleUrl
    : context.developerConsoleUrl;

  return (
    <html lang="en">
      <body>
        <div className="app-frame">
          <aside className="sidebar">
            <Link className="brand" href="/">
              <BrandMark />
              <span><b>AegisFlow</b><small>Agent control plane</small></span>
            </Link>
            <nav aria-label="Primary navigation" className="primary-nav">
              <Link href="/"><span aria-hidden="true">⌁</span> Overview</Link>
              {isDeveloper && <Link href="/runs/new"><span aria-hidden="true">＋</span> New Run</Link>}
              <a href="#governance"><span aria-hidden="true">◇</span> Governance</a>
              <a href="#evidence"><span aria-hidden="true">◎</span> Evidence</a>
            </nav>
            <div className="sidebar-foot">
              <p className="eyebrow">Local identity</p>
              <div className="actor-chip">
                <span className={`actor-dot actor-dot--${context.persona}`} />
                <span><b>{isDeveloper ? "Developer" : "Reviewer"}</b><small>Isolated server persona</small></span>
              </div>
              <a className="counterpart-link" href={counterpartUrl} rel="noreferrer">
                Open {isDeveloper ? "Reviewer" : "Developer"} console ↗
              </a>
            </div>
          </aside>
          <div className="workspace">
            <header className="topbar">
              <div>
                <span className="system-light" /> Local MVP connected
              </div>
              <div className="topbar-meta">
                <span>Ollama</span><span>Temporal</span><span>Dry-run GitHub</span>
              </div>
            </header>
            <main>{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}

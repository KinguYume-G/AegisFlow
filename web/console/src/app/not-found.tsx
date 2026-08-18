import Link from "next/link";

export default function NotFound() {
  return <div className="page-shell"><div className="connection-error"><span>404</span><h1>Run not found</h1><p>The identifier is invalid or not visible to this tenant.</p><Link className="button button--secondary" href="/">Return to Runs</Link></div></div>;
}

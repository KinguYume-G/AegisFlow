import { statusLabel } from "@/lib/format";

export function StatusPill({ status }: { status: string }) {
  return <span className={`status-pill status-pill--${status}`}>{statusLabel(status)}</span>;
}

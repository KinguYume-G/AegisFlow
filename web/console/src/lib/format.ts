const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  running: "Running",
  waiting: "Waiting",
  waiting_clarification: "Waiting for clarification",
  waiting_approval: "Waiting for approval",
  completed: "Completed",
  failed: "Failed",
  rejected: "Rejected",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status.replaceAll("_", " ");
}

export function formatTokenCount(value: number | null | undefined): string {
  return value == null ? "Not measured" : new Intl.NumberFormat("en-US").format(value);
}

export function formatCost(value: number | null | undefined): string {
  return value == null ? "Not measured" : `$${value.toFixed(4)}`;
}

export function formatDuration(value: number | null | undefined): string {
  if (value == null) return "Not measured";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function shortId(value: string): string {
  return value.slice(0, 8);
}

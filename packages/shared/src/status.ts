export const VERIFICATION = ["verified", "partially_verified", "unverified", "failed", "requires_human_review"] as const;
export type Verification = (typeof VERIFICATION)[number];
export const JOB_STATES = ["QUEUED", "RUNNING", "WAITING_FOR_APPROVAL", "COMPLETED", "FAILED", "CANCELLED"] as const;
export type JobState = (typeof JOB_STATES)[number];
export const isTerminal = (s: string) => s === "COMPLETED" || s === "FAILED" || s === "CANCELLED";
/** Format a possibly-unavailable USD amount. Never invents a number. */
export function fmtCost(v: number | null | undefined, unavailable: string): string {
  if (v === null || v === undefined) return unavailable;
  return v < 0.01 ? `$${v.toFixed(6)}` : `$${v.toFixed(4)}`;
}
export function fmtSeconds(v: number | null | undefined, unavailable: string): string {
  return v === null || v === undefined ? unavailable : `${v.toFixed(1)}s`;
}

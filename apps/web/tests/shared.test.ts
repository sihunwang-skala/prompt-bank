import { describe, it, expect } from "vitest";
import { dict, t, detectLang, fmtCost, fmtSeconds, isTerminal } from "@raw/shared";

describe("i18n", () => {
  it("English and Korean have identical keys", () => {
    expect(Object.keys(dict.ko).sort()).toEqual(Object.keys(dict.en).sort());
  });
  it("no empty translations", () => {
    for (const l of ["en", "ko"] as const) for (const [k, v] of Object.entries(dict[l])) expect(v.trim(), `${l}.${k}`).not.toBe("");
  });
  it("switches language and falls back to the key", () => {
    expect(t("en", "navHome")).toBe("Home");
    expect(t("ko", "navHome")).toBe("홈");
    expect(t("ko", "does_not_exist")).toBe("does_not_exist");
  });
  it("detects Korean only for ko locales", () => {
    expect(detectLang("ko-KR")).toBe("ko");
    expect(detectLang("en-US")).toBe("en");
    expect(detectLang(undefined)).toBe("en");
  });
  it("every enum used by the UI has a label in both languages", () => {
    const keys = ["state_QUEUED","state_RUNNING","state_WAITING_FOR_APPROVAL","state_COMPLETED","state_FAILED","state_CANCELLED",
      "v_verified","v_partially_verified","v_unverified","v_failed","v_requires_human_review","stop_all_checks_passed","stop_no_improvement","stop_max_iterations","stop_budget","stop_time_limit","stop_cancelled"];
    for (const k of keys) { expect(dict.en).toHaveProperty(k); expect(dict.ko).toHaveProperty(k); }
  });
});
describe("formatting never invents numbers", () => {
  it("unavailable cost/time", () => {
    expect(fmtCost(null, "n/a")).toBe("n/a");
    expect(fmtCost(undefined, "n/a")).toBe("n/a");
    expect(fmtSeconds(null, "n/a")).toBe("n/a");
    expect(fmtCost(0.12345, "n/a")).toBe("$0.1235");
  });
  it("terminal states", () => {
    expect(isTerminal("COMPLETED")).toBe(true);
    expect(isTerminal("RUNNING")).toBe(false);
  });
});

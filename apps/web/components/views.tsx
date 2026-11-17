"use client";
import { useEffect, useRef, useState } from "react";
import { fmtCost, fmtSeconds, isTerminal } from "@raw/shared";
import { useC } from "./ctx";

const SECTIONS = ["body", "objective", "context", "instructions", "constraints", "output_format", "references", "evaluation_criteria"];
const STAGES = ["generate", "critical_review", "completeness_review", "adversarial_review", "constraint_compliance", "evidence_check", "repair"];
const ROLES = ["mandatory_requirement", "factual_source", "example_output", "visual_inspiration", "background", "negative_example"];
const CHECKS = ["semantic", "required_section", "must_include", "forbidden", "exact_string", "max_chars", "min_chars", "json_keys"];
const MODELS = ["mock-1", "mock-forgetful", "mock-stubborn"];

function useLoad<T>(fn: () => Promise<T>, deps: any[], init: T): [T, () => void, string] {
  const [v, setV] = useState<T>(init); const [err, setErr] = useState(""); const [n, setN] = useState(0);
  useEffect(() => { let on = true; fn().then((x) => on && (setV(x), setErr(""))).catch((e) => on && setErr(e.message)); return () => { on = false; }; }, [...deps, n]);
  return [v, () => setN((x) => x + 1), err];
}
const Err = ({ e }: { e: string }) => (e ? <div className="err" role="alert">{e}</div> : null);

export function VStatus({ v }: { v: string }) {
  const { t } = useC();
  if (!v) return null;
  return <span className={`badge v-${v}`} title={t("v_help")}>{t("v_" + v)}</span>;
}

export function Usage({ job }: { job: any }) {
  const { t } = useC(); const u = job.usage || {}; const e = job.estimate || {}; const na = t("unavailable");
  return (
    <table aria-label="cost and time">
      <tbody>
        <tr><th>{t("model")}</th><td>{job.config?.model}{job.config?.reviewer_model ? ` / ${job.config.reviewer_model}` : ""}</td><th>{t("rounds")}</th><td>{job.rounds?.length ?? 0} / {job.config?.max_iterations}</td></tr>
        <tr><th>{t("estCost")}</th><td>{e.cost_low == null ? na : `${fmtCost(e.cost_low, na)} – ${fmtCost(e.cost_high, na)}`}</td><th>{t("estTime")}</th><td>{e.seconds_low == null ? na : `${e.seconds_low}–${e.seconds_high}s`}</td></tr>
        <tr><th>{t("recorded")}</th><td>{fmtCost(u.cost, na)} <span className="mute">{u.cost_complete === false ? t("costIncomplete") : ""}</span></td><th>{t("elapsed")}</th><td>{fmtSeconds(u.elapsed_seconds, na)}</td></tr>
        <tr><th>{t("maxCost")}</th><td>{job.config?.max_cost ?? "—"}</td><th>{t("budgetLeft")}</th><td>{u.remaining_budget == null ? "—" : fmtCost(u.remaining_budget, na)}</td></tr>
        <tr><th>{t("calls")}</th><td>{u.calls ?? 0}</td><th>{t("retries")}</th><td>{u.retries ?? 0}</td></tr>
      </tbody>
    </table>
  );
}

export function Home({ jobs }: { jobs: any[] }) {
  const { t, api, pid, open, setJobId } = useC();
  const [pk] = useLoad(() => api.packages(pid), [pid], [] as any[]);
  const [pr] = useLoad(() => api.prompts(pid), [pid], [] as any[]);
  const run = jobs.filter((j) => j.state === "QUEUED" || j.state === "RUNNING");
  const J = ({ j }: any) => <tr><td><a href="#" onClick={(e) => { e.preventDefault(); setJobId(j.id); open("job"); }}>{j.id}</a></td><td>{t("state_" + j.state)}</td><td><VStatus v={j.verification_status} /></td><td>{fmtCost(j.usage?.cost, t("unavailable"))}</td></tr>;
  return (
    <>
      <h1>{t("home")}</h1>
      <div className="row"><button className="primary fit" onClick={() => open("compose")}>{t("navCompose")}</button><button className="fit" onClick={() => open("constraints")}>{t("navConstraints")}</button><button className="fit" onClick={() => open("refs")}>{t("navRefs")}</button></div>
      <h2>{t("running")}</h2>{run.length ? <table><tbody>{run.map((j) => <J key={j.id} j={j} />)}</tbody></table> : <p className="mute">{t("none")}</p>}
      <h2>{t("recentTasks")}</h2>{jobs.length ? <table><tbody>{jobs.slice(0, 8).map((j) => <J key={j.id} j={j} />)}</tbody></table> : <p className="mute">{t("none")}</p>}
      <h2>{t("savedPackages")}</h2>{pk.length ? pk.map((p: any) => <div key={p.id} className="box">{p.name} <span className="tag">v{p.version}</span></div>) : <p className="mute">{t("none")}</p>}
      <h2>{t("recentPrompts")}</h2>{pr.slice(0, 5).map((p: any) => <div key={p.id} className="box">{p.title} <span className="tag">v{p.version}</span></div>)}{!pr.length && <p className="mute">{t("none")}</p>}
    </>
  );
}

export function Compose() {
  const { t, api, pid, open, setJobId, seed, me } = useC();
  const [intent, setIntent] = useState(""); const [secs, setSecs] = useState<Record<string, string>>(seed?.sections || {});
  const [title, setTitle] = useState(seed?.title || ""); const [promptId, setPromptId] = useState<string | null>(seed?.id || null);
  const [qs, setQs] = useState<string[]>([]); const [sug, setSug] = useState<string[]>([]); const [tab, setTab] = useState("structured");
  const [cfg, setCfg] = useState<any>({ model: me?.settings?.default_model || "mock-1", review_depth: "standard", max_iterations: 3, max_cost: 0.5, max_seconds: 120, reviewer_model: "" });
  const [refIds, setRefIds] = useState<string[]>([]); const [est, setEst] = useState<any>(null); const [err, setErr] = useState(""); const [msg, setMsg] = useState("");
  const [refs] = useLoad(() => api.refs(pid), [pid], [] as any[]);
  const [cons] = useLoad(() => api.constraints(pid), [pid], { constraints: [] } as any);
  const compiled = SECTIONS.filter((k) => secs[k]?.trim()).map((k) => (k === "body" ? secs[k].trim() : `## ${t("sec_" + k)}\n${secs[k].trim()}`)).join("\n\n");
  const body = () => ({ project_id: pid, ...(promptId ? { prompt_id: promptId } : { task: compiled }), config: { ...cfg, reviewer_model: cfg.reviewer_model || null, max_cost: cfg.max_cost === "" ? null : Number(cfg.max_cost), reference_ids: refIds } });
  useEffect(() => { if (!compiled && !promptId) return setEst(null); const h = setTimeout(() => api.estimate({ ...body(), task: compiled }).then(setEst).catch(() => {}), 300); return () => clearTimeout(h); }, [compiled, cfg, refIds]);
  const build = async () => { setErr(""); try { const r = await api.post("/prompts/build", { intent, model: cfg.model }); setSecs((s) => ({ ...s, ...r.sections })); setQs(r.questions); setSug(r.suggested_references); if (!title) setTitle(intent.slice(0, 60)); } catch (e: any) { setErr(e.message); } };
  const save = async () => { setErr(""); try { const p = promptId ? await api.patch(`/prompts/${promptId}`, { title, sections: secs, change_note: "edited in composer" }) : await api.post(`/projects/${pid}/prompts`, { title: title || "Untitled", sections: secs }); setPromptId(p.id); setMsg(t("promptSaved")); } catch (e: any) { setErr(e.message); } };
  const exec = async () => { setErr(""); try { if (promptId) await save(); const j = await api.run(body()); setJobId(j.id); open("job"); } catch (e: any) { setErr(e.message); } };
  const active = (cons.constraints || []).filter((c: any) => c.status === "active");
  return (
    <>
      <h1>{t("composeTitle")}</h1>
      <label htmlFor="intent">{t("intent")}</label><textarea id="intent" value={intent} onChange={(e) => setIntent(e.target.value)} />
      <p><button onClick={build} disabled={!intent.trim()}>{t("buildPrompt")}</button></p>
      {qs.length > 0 && <div className="box"><b>{t("questions")}</b><ul>{qs.map((q) => <li key={q}>{q}</li>)}</ul></div>}
      {sug.length > 0 && <div className="box"><b>{t("suggestedRefs")}</b><ul>{sug.map((q) => <li key={q}>{q}</li>)}</ul></div>}
      <div className="tabs" role="group"><button aria-pressed={tab === "structured"} onClick={() => setTab("structured")}>{t("structured")}</button><button aria-pressed={tab === "compiled"} onClick={() => setTab("compiled")}>{t("compiled")}</button></div>
      <label htmlFor="ptitle">{t("title")}</label><input id="ptitle" value={title} onChange={(e) => setTitle(e.target.value)} />
      {tab === "structured" ? SECTIONS.filter((k) => k !== "body" || secs.body !== undefined).map((k) => <div key={k}><label htmlFor={"s_" + k}>{t("sec_" + k)}</label><textarea id={"s_" + k} style={k === "body" ? { minHeight: 360, fontFamily: "ui-monospace,Menlo,monospace", fontSize: 13 } : undefined} value={secs[k] || ""} onChange={(e) => setSecs({ ...secs, [k]: e.target.value })} /></div>) : <pre>{compiled || t("none")}</pre>}
      <p><button onClick={save} disabled={!title && !compiled}>{t("savePrompt")}</button> <span className="mute">{msg}</span></p>
      <h2>{t("attachRefs")}</h2>
      {refs.map((r: any) => <label key={r.id} style={{ display: "flex", gap: 8, margin: 0, color: "inherit" }}><input type="checkbox" style={{ width: "auto" }} checked={refIds.includes(r.id)} onChange={(e) => setRefIds(e.target.checked ? [...refIds, r.id] : refIds.filter((x) => x !== r.id))} />{r.name} <span className="tag">{t("r_" + r.role)}</span></label>)}
      {!refs.length && <p className="mute">{t("none")}</p>}
      <h2>{t("activeConstraints")}</h2><p className="mute">{active.map((c: any) => <span key={c.id} className="tag" title={c.content}>{c.content.slice(0, 40)}</span>)}{!active.length && t("none")}</p>
      <h2>{t("validation")}</h2>
      <div className="row">
        <div><label htmlFor="m">{t("model")}</label><select id="m" value={cfg.model} onChange={(e) => setCfg({ ...cfg, model: e.target.value })}>{MODELS.map((m) => <option key={m}>{m}</option>)}<option value="openai:">openai:&lt;id&gt;</option><option value="anthropic:">anthropic:&lt;id&gt;</option></select></div>
        <div><label htmlFor="d">{t("depth")}</label><select id="d" value={cfg.review_depth} onChange={(e) => setCfg({ ...cfg, review_depth: e.target.value })}>{["quick", "standard", "deep"].map((d) => <option key={d} value={d}>{t("depth_" + d)}</option>)}</select></div>
        <div><label htmlFor="mi">{t("maxIter")}</label><input id="mi" type="number" min={1} max={10} value={cfg.max_iterations} onChange={(e) => setCfg({ ...cfg, max_iterations: +e.target.value })} /></div>
        <div><label htmlFor="mc">{t("maxCost")}</label><input id="mc" type="number" step="0.01" min={0} value={cfg.max_cost} onChange={(e) => setCfg({ ...cfg, max_cost: e.target.value })} /></div>
        <div><label htmlFor="ms">{t("maxSeconds")}</label><input id="ms" type="number" min={5} value={cfg.max_seconds} onChange={(e) => setCfg({ ...cfg, max_seconds: +e.target.value })} /></div>
      </div>
      <label htmlFor="rm">{t("reviewer")}</label><input id="rm" value={cfg.reviewer_model} onChange={(e) => setCfg({ ...cfg, reviewer_model: e.target.value })} placeholder="mock-1" />
      <p className="mute">{cfg.model.startsWith("mock-") ? t("mockNotice") : t("externalNotice")}</p>
      {est && <div className="box"><b>{t("estimate")}</b>: {t("estCost")} {est.cost_low == null ? t("unavailable") : `${fmtCost(est.cost_low, "")} – ${fmtCost(est.cost_high, "")}`} · {t("estTime")} {est.seconds_low == null ? t("unavailable") : `${est.seconds_low}–${est.seconds_high}s`} · {t("calls")} {est.calls_min}–{est.calls_max}<div className="mute">{t("costBasis")}: {est.cost_basis}; {est.time_basis}</div></div>}
      <Err e={err} />
      <p><button className="primary" onClick={exec} disabled={!compiled && !promptId}>{t("execute")}</button></p>
    </>
  );
}

export function JobView() {
  const { t, api, jobId, setJobId, open, lang } = useC();
  const [job, setJob] = useState<any>(null); const [err, setErr] = useState("");
  const [mc, setMc] = useState({ mode: "apply_next", content: "", type: "must_include", text: "" });
  useEffect(() => {
    if (!jobId) return; let on = true;
    const tick = () => api.job(jobId).then((j) => { if (on) { setJob(j); if (isTerminal(j.state) || j.state === "WAITING_FOR_APPROVAL") clearInterval(id); } }).catch((e) => on && setErr(e.message));
    tick(); const id = setInterval(tick, 1200); return () => { on = false; clearInterval(id); };
  }, [jobId]);
  if (!jobId) return <p className="mute">{t("none")}</p>;
  if (!job) return <p>{t("loading")} <Err e={err} /></p>;
  const live = !isTerminal(job.state);
  const send = async () => { try { const check = mc.type === "semantic" ? { type: "semantic" } : mc.type.endsWith("chars") ? { type: mc.type, value: +mc.text } : { type: mc.type, text: mc.text }; const r = await api.change(job.id, { mode: mc.mode, constraint: { content: mc.content, severity: "major", check } }); if (r.new_job) setJobId(r.new_job.id); } catch (e: any) { setErr(e.message); } };
  return (
    <>
      <h1>{t("validation")} <span className="mute">{job.id}</span></h1>
      <p><b>{t("state_" + job.state)}</b> {job.stage && <>· {t("stage")}: {job.stage}</>} {job.verification_status && <>· <VStatus v={job.verification_status} /></>} {job.stop_reason && <span className="mute">· {t("stop_" + job.stop_reason)}</span>}</p>
      {live && <><div className="stages" aria-label={t("stage")}>{STAGES.map((s) => <span key={s} className={s === job.stage ? "on" : ""}>{s}</span>)}</div><div className="indet" role="progressbar" aria-label={t("noFakeProgress")} /><p className="mute">{t("noFakeProgress")}</p></>}
      {job.state === "WAITING_FOR_APPROVAL" && <div className="box">{t("needsApproval")}: {job.estimate?.approval_reason} <button className="primary" onClick={() => api.approve(job.id).then(setJob)}>{t("approve")}</button></div>}
      {live && job.state !== "WAITING_FOR_APPROVAL" && <button onClick={() => api.cancel(job.id).then(setJob)}>{t("cancelJob")}</button>}
      {job.error && <Err e={job.error} />}<Err e={err} />
      <Usage job={job} />
      {job.usage?.estimated_usage_calls > 0 && <p className="mute">{t("usageEstimated")}</p>}
      {live && job.state === "RUNNING" && <div className="box"><b>{t("midChange")}</b><p className="mute">{t("midNote")}</p>
        <div className="row"><div><label>{t("content")}</label><input value={mc.content} onChange={(e) => setMc({ ...mc, content: e.target.value })} /></div>
          <div><label>{t("checkType")}</label><select value={mc.type} onChange={(e) => setMc({ ...mc, type: e.target.value })}>{CHECKS.filter((c) => c !== "json_keys").map((c) => <option key={c} value={c}>{t("ct_" + c)}</option>)}</select></div>
          <div><label>{t("checkParam")}</label><input value={mc.text} onChange={(e) => setMc({ ...mc, text: e.target.value })} /></div>
          <div><label>&nbsp;</label><select value={mc.mode} onChange={(e) => setMc({ ...mc, mode: e.target.value })}>{["apply_next", "cancel_restart", "branch"].map((m) => <option key={m} value={m}>{t("mc_" + m)}</option>)}</select></div></div>
        <button onClick={send} disabled={!mc.content}>{t("add")}</button></div>}
      {job.result?.output && <><h2>{t("output")}</h2><pre>{job.result.output}</pre></>}
      {(job.rounds || []).map((r: any) => (
        <details key={r.index} className="box" open={r.index === job.rounds.length}>
          <summary><b>{t("round")} {r.index}</b> · {r.issues.filter((i: any) => i.blocking).length} {t("blocking")} · {fmtCost(r.cost, t("unavailable"))} · {fmtSeconds(r.seconds, "")}</summary>
          <h3>{t("issues")}</h3>{r.issues.length ? <ul>{r.issues.map((i: any, k: number) => <li key={k}><span className={i.blocking ? "fail" : "mute"}>[{i.blocking ? t("blocking") : t("optional")} · {i.severity}]</span> {i.description} <span className="mute">({i.category}{i.source ? ` · ${i.source}` : ""})</span></li>)}</ul> : <p className="mute">{t("none")}</p>}
          {r.repairs.length > 0 && <><h3>{t("repairs")}</h3><ul>{r.repairs.map((x: any, k: number) => <li key={k}>{x.issue}</li>)}</ul></>}
          <h3>{t("compliance")}</h3>{r.compliance.length ? <ul>{r.compliance.map((c: any) => <li key={c.constraint_id}><span className={c.status}>{t(c.status)}</span> · {c.content} <span className="mute">— {c.detail}</span></li>)}</ul> : <p className="mute">{t("none")}</p>}
          {r.stages?.evidence?.status === "claims_not_traceable" && <p className="mute">⚠ {t("missingEvidence")}</p>}
          <details><summary>{t("output")}</summary><pre>{r.output}</pre></details>
        </details>
      ))}
      {job.constraints_applied?.length > 0 && <p className="mute">{t("activeConstraints")}: {job.constraints_applied.length}</p>}
    </>
  );
}

export function Constraints() {
  const { t, api, pid } = useC();
  const [data, reload, err] = useLoad(() => api.constraints(pid), [pid], { constraints: [], resolution: [] } as any);
  const [f, setF] = useState({ content: "", scope: "project", priority: 50, severity: "major", type: "semantic", text: "" });
  const [m, setM] = useState<string>(""); const [vers, setVers] = useState<any>(null);
  const add = async () => { setM(""); try { const check = f.type === "semantic" ? { type: "semantic" } : f.type.endsWith("chars") ? { type: f.type, value: +f.text } : f.type === "json_keys" ? { type: f.type, keys: f.text.split(",").map((x) => x.trim()) } : { type: f.type, text: f.text }; const r = await api.post("/constraints", { content: f.content, scope: f.scope, priority: +f.priority, severity: f.severity, check, project_id: f.scope === "global" ? null : pid }); if (r.conflicts?.length) setM(t("conflictFound") + " " + r.conflicts.map((c: any) => c.reason).join("; ")); setF({ ...f, content: "", text: "" }); reload(); } catch (e: any) { setM(e.message); } };
  const act = async (fn: Promise<any>) => { try { await fn; reload(); } catch (e: any) { setM(e.message); } };
  const over = new Set((data.resolution || []).map((r: any) => r.constraint_id));
  return (
    <>
      <h1>{t("constraintsTitle")}</h1><Err e={err} />
      <div className="box">
        <label htmlFor="cc">{t("content")}</label><input id="cc" value={f.content} onChange={(e) => setF({ ...f, content: e.target.value })} />
        <div className="row">
          <div><label>{t("checkType")}</label><select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}>{CHECKS.map((c) => <option key={c} value={c}>{t("ct_" + c)}</option>)}</select></div>
          {f.type !== "semantic" && <div><label>{t("checkParam")}</label><input value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })} /></div>}
          <div><label>{t("scope")}</label><select value={f.scope} onChange={(e) => setF({ ...f, scope: e.target.value })}>{["global", "project", "task_package", "execution"].map((s) => <option key={s} value={s}>{t("scope_" + s)}</option>)}</select></div>
          <div><label>{t("severity")}</label><select value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })}>{["critical", "major", "minor"].map((s) => <option key={s} value={s}>{t("sev_" + s)}</option>)}</select></div>
          <div><label>{t("priority")}</label><input type="number" min={0} max={100} value={f.priority} onChange={(e) => setF({ ...f, priority: +e.target.value })} /></div>
        </div>
        <p><button className="primary" onClick={add} disabled={!f.content.trim()}>{t("add")}</button></p><Err e={m} />
      </div>
      {data.constraints.map((c: any) => (
        <div key={c.id} className="box">
          <div><b>{c.content}</b></div>
          <div className="mute"><span className={`tag`}>{t("st_" + c.status)}</span><span className="tag">{t("scope_" + c.scope)}</span><span className="tag">P{c.priority}</span><span className="tag">{t("sev_" + c.severity)}</span><span className="tag">{t("ct_" + c.check.type)}{c.check.text || c.check.name ? `: ${c.check.text || c.check.name}` : ""}</span><span className="tag">v{c.version}</span>{over.has(c.id) && <span className="tag">{t("overridden")}</span>}</div>
          <p>
            {c.status === "conflicting" && <><span className="err">{t("conflictFound")}</span><br /><button onClick={() => act(api.post(`/constraints/${c.id}/resolve`, { action: "replace_existing" }))}>{t("resolveReplace")}</button> <button onClick={() => act(api.post(`/constraints/${c.id}/resolve`, { action: "keep_existing" }))}>{t("resolveKeep")}</button> <button onClick={() => act(api.post(`/constraints/${c.id}/resolve`, { action: "keep_both_priority" }))}>{t("resolveBoth")}</button> </>}
            {c.status === "active" && <button onClick={() => act(api.patch(`/constraints/${c.id}`, { status: "disabled", reason: "disabled by user" }))}>{t("disable")}</button>}
            {c.status === "disabled" && <button onClick={() => act(api.patch(`/constraints/${c.id}`, { status: "active", reason: "re-enabled" }))}>{t("enable")}</button>}{" "}
            <button onClick={async () => setVers({ id: c.id, list: await api.get(`/constraints/${c.id}/versions`) })}>{t("versions")}</button>
          </p>
          {vers?.id === c.id && <table><tbody>{vers.list.map((v: any) => <tr key={v.version}><td>v{v.version}</td><td>{v.snapshot.content}</td><td>{t("st_" + v.snapshot.status)}</td><td className="mute">{v.reason}</td></tr>)}</tbody></table>}
        </div>
      ))}
      {!data.constraints.length && <p className="mute">{t("none")}</p>}
    </>
  );
}

export function Library() {
  const { t, api, pid, open, setJobId, lang } = useC();
  const [q, setQ] = useState(""); const [prompts, reload, err] = useLoad(() => api.prompts(pid, q), [pid, q], [] as any[]);
  const [pk, reloadPk] = useLoad(() => api.packages(pid), [pid], [] as any[]);
  const [diff, setDiff] = useState<any>(null); const [msg, setMsg] = useState("");
  const [examples] = useLoad(() => api.get("/examples"), [], [] as any[]);
  const [seg, setSeg] = useState<any>(null); const [rule, setRule] = useState("");
  const openSeg = async (p: any) => { if (seg?.id === p.id) return setSeg(null); setRule(""); setSeg({ id: p.id, list: await api.get(`/prompts/${p.id}/segments`), sel: [] }); };
  const toggle = (sid: string) => setSeg((x: any) => ({ ...x, sel: x.sel.includes(sid) ? x.sel.filter((i: string) => i !== sid) : [...x.sel, sid] }));
  const runSel = async () => { try { const j = await api.run({ project_id: pid, prompt_id: seg.id, segment_ids: seg.sel, config: { model: "mock-1", review_depth: "standard", max_iterations: 3, max_cost: 0.5 } }); setJobId(j.id); open("job"); } catch (e: any) { setMsg(e.message); } };
  const extractSel = async () => { const title = prompt(t("newPromptTitle")); if (!title) return; try { await api.post(`/prompts/${seg.id}/segments/extract`, { segment_ids: seg.sel, title }); reload(); setMsg("✓"); } catch (e: any) { setMsg(e.message); } };
  const strengthen = async () => { try { await api.post(`/prompts/${seg.id}/segments/${seg.sel[0]}/strengthen`, { addition: rule }); setRule(""); reload(); setSeg(null); setMsg("✓"); } catch (e: any) { setMsg(e.message); } };
  const install = async (k: string) => { try { await api.post(`/projects/${pid}/examples/${k}/install`); reload(); setMsg("✓"); } catch (e: any) { setMsg(e.message); } };
  const [name, setName] = useState("");
  const fav = async (p: any) => { await api.patch(`/prompts/${p.id}`, { favorite: !p.favorite }); reload(); };
  const showDiff = async (p: any) => { const d = await api.get(`/prompts/${p.id}`); if (d.version < 2) return setMsg("v1 only"); setDiff({ id: p.id, d: await api.get(`/prompts/${p.id}/diff?a=${d.version - 1}&b=${d.version}`) }); };
  const savePkg = async (p: any) => { try { await api.post("/packages", { project_id: pid, name: name || p.title, prompt_id: p.id, constraint_ids: (await api.constraints(pid)).constraints.filter((c: any) => c.status === "active").map((c: any) => c.id), reference_ids: (await api.refs(pid)).map((r: any) => r.id) }); reloadPk(); setMsg("✓"); } catch (e: any) { setMsg(e.message); } };
  const download = (obj: any, fn: string) => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" })); a.download = fn; a.click(); };
  const importFile = async (e: any, kind: string) => { const f = e.target.files?.[0]; if (!f) return; try { const doc = JSON.parse(await f.text()); await api.post(kind === "pkg" ? `/projects/${pid}/packages/import` : `/projects/${pid}/prompts/import`, doc); reload(); reloadPk(); } catch (x: any) { setMsg(x.message); } };
  return (
    <>
      <h1>{t("libraryTitle")}</h1><Err e={err} />
      <div className="row"><div><input aria-label={t("search")} placeholder={t("search")} value={q} onChange={(e) => setQ(e.target.value)} /></div><div className="fit"><label style={{ margin: 0 }}>{t("import")} <input type="file" accept=".json" onChange={(e) => importFile(e, "prompt")} style={{ width: "auto" }} /></label></div></div>
      <label>{t("packageName")}</label><input value={name} onChange={(e) => setName(e.target.value)} />
      <p className="mute">{t("packageNote")} {msg}</p>
      {examples.length > 0 && <><h2>{t("examplesTitle")}</h2><p className="mute">{t("examplesNote")}</p>{examples.map((e: any) => <div className="box" key={e.key}><b>{e.title[lang]}</b>{e.tags.map((x: string) => <span key={x} className="tag" style={{ marginLeft: 4 }}>{x}</span>)}<p className="mute">{e.about[lang]}</p><button onClick={() => install(e.key)}>{t("installExample")}</button></div>)}</>}
      {prompts.map((p: any) => (
        <div className="box" key={p.id}>
          <b>{p.title}</b> <span className="tag">v{p.version}</span>{p.tags.map((x: string) => <span key={x} className="tag">{x}</span>)}
          <p className="mute">{(p.sections.objective || "").slice(0, 140)}</p>
          <button onClick={() => fav(p)} aria-pressed={p.favorite}>{p.favorite ? "★" : "☆"} {t("favorites")}</button>{" "}
          <button onClick={() => open("compose", p)}>{t("reuse")}</button>{" "}
          <button onClick={() => showDiff(p)}>{t("compare")}</button>{" "}
          <button onClick={() => api.post(`/prompts/${p.id}/duplicate`).then(reload)}>{t("duplicate")}</button>{" "}
          <button onClick={async () => download(await api.get(`/prompts/${p.id}/export`), `${p.title}.prompt.json`)}>{t("export")}</button>{" "}
          <button onClick={() => savePkg(p)}>{t("savePackage")}</button>{" "}
          <button onClick={() => openSeg(p)} aria-expanded={seg?.id === p.id}>{seg?.id === p.id ? t("hideSegments") : t("segments")}</button>
          {seg?.id === p.id && (
            <div className="box" aria-label={t("segments")}>
              <p className="mute">{t("segmentsHint")}</p>
              <div style={{ maxHeight: 320, overflow: "auto" }}>
                {seg.list.map((x: any) => <label key={x.id} style={{ display: "flex", gap: 8, margin: 0, padding: "2px 0", paddingLeft: Math.max(x.level - 1, 0) * 14, color: "inherit", fontSize: 13 }}><input type="checkbox" style={{ width: "auto" }} checked={seg.sel.includes(x.id)} onChange={() => toggle(x.id)} /><span>{x.title} <span className="mute">· {x.chars} {t("chars")}</span></span></label>)}
              </div>
              <p><button className="primary" disabled={!seg.sel.length} onClick={runSel}>{t("runSelected")}</button>{" "}<button disabled={!seg.sel.length} onClick={extractSel}>{t("extractSelected")}</button></p>
              <h3>{t("strengthen")}</h3><p className="mute">{seg.sel.length === 1 ? t("strengthenHint") : t("selectOne")}</p>
              <label htmlFor="rule">{t("addRule")}</label><textarea id="rule" value={rule} onChange={(e) => setRule(e.target.value)} placeholder="- …" />
              <button disabled={seg.sel.length !== 1 || !rule.trim()} onClick={strengthen}>{t("applyRule")}</button>
            </div>
          )}
          {diff?.id === p.id && diff.d.changes.map((c: any) => <div key={c.section}><h3>{t("sec_" + c.section)} ({c.status})</h3><pre>{c.diff}</pre></div>)}
        </div>
      ))}
      {!prompts.length && <p className="mute">{t("none")}</p>}
      <h2>{t("savedPackages")}</h2>
      <label style={{ margin: 0 }}>{t("import")} <input type="file" accept=".json" onChange={(e) => importFile(e, "pkg")} style={{ width: "auto" }} /></label>
      {pk.map((p: any) => <div className="box" key={p.id}><b>{p.name}</b> <span className="tag">v{p.version}</span> <button onClick={() => api.post(`/packages/${p.id}/run`).then((j: any) => { setJobId(j.id); open("job"); })}>{t("runPackage")}</button> <button onClick={() => api.post(`/packages/${p.id}/duplicate`).then(reloadPk)}>{t("duplicate")}</button> <button onClick={async () => download(await api.get(`/packages/${p.id}/export`), `${p.name}.package.json`)}>{t("export")}</button></div>)}
    </>
  );
}

export function Refs() {
  const { t, api, pid } = useC();
  const [refs, reload, err] = useLoad(() => api.refs(pid), [pid], [] as any[]);
  const [role, setRole] = useState("background"); const [url, setUrl] = useState(""); const [over, setOver] = useState(false); const [m, setM] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const up = async (files: FileList | null) => { if (!files) return; setM(""); for (const f of Array.from(files)) { try { await api.upload(pid, f, role); } catch (e: any) { setM(`${f.name}: ${e.message}`); } } reload(); };
  const hasFactual = refs.some((r: any) => r.role === "factual_source");
  return (
    <>
      <h1>{t("refsTitle")}</h1><p className="mute">{t("untrustedNote")}</p><Err e={err} /><Err e={m} />
      <label htmlFor="role">{t("role")} →</label><select id="role" value={role} onChange={(e) => setRole(e.target.value)}>{ROLES.map((r) => <option key={r} value={r}>{t("r_" + r)}</option>)}</select>
      <div className={`drop ${over ? "over" : ""}`} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={(e) => { e.preventDefault(); setOver(false); up(e.dataTransfer.files); }}>
        <button onClick={() => input.current?.click()}>{t("dropHere")}</button><input ref={input} type="file" multiple hidden onChange={(e) => up(e.target.files)} />
        <div className="mute">pdf, txt, md, docx, csv, png/jpg, code</div>
      </div>
      <div className="row" style={{ marginTop: 10 }}><div><input aria-label="URL" placeholder="https://…" value={url} onChange={(e) => setUrl(e.target.value)} /></div><div className="fit"><button onClick={async () => { try { await api.post("/references/url", { project_id: pid, url, role }); setUrl(""); reload(); } catch (e: any) { setM(e.message); } }} disabled={!url}>{t("addUrl")}</button></div></div>
      {!hasFactual && <p className="mute">⚠ {t("missingEvidence")}</p>}
      {refs.map((r: any) => (
        <div className="box" key={r.id}><b>{r.name}</b> {r.extraction !== "ok" && <span className="tag">{t("extraction_unsupported")}</span>}
          <select aria-label={t("role")} value={r.role} onChange={(e) => api.req("PATCH", `/references/${r.id}?role=${e.target.value}`).then(reload)} style={{ width: "auto", marginLeft: 8 }}>{ROLES.map((x) => <option key={x} value={x}>{t("r_" + x)}</option>)}</select>{" "}
          <button onClick={() => api.del(`/references/${r.id}`).then(reload)}>{t("delete")}</button>
          {r.warnings.map((w: string) => <div key={w} className="err">⚠ {w}</div>)}
          {r.preview && <pre>{r.preview}</pre>}
        </div>
      ))}
      {!refs.length && <p className="mute">{t("none")}</p>}
    </>
  );
}

export function HistoryView() {
  const { t, api, pid, lang } = useC();
  const [q, setQ] = useState(""); const [ev, , err] = useLoad(() => api.history(pid, q), [pid, q], [] as any[]);
  const [req, setReq] = useState(""); const [type, setType] = useState(""); const [rep, setRep] = useState<any>(null); const [m, setM] = useState("");
  const gen = async () => { try { setRep(await api.report({ project_id: pid, request: req, type: type || null, lang })); setM(""); } catch (e: any) { setM(e.message); } };
  return (
    <>
      <h1>{t("historyTitle")}</h1><Err e={err} /><Err e={m} />
      <label htmlFor="rq">{t("reportRequest")}</label><input id="rq" value={req} onChange={(e) => setReq(e.target.value)} />
      <div className="row"><div><label>{t("reportType")}</label><select value={type} onChange={(e) => setType(e.target.value)}><option value="">auto</option>{["full", "decisions", "requirements", "validation", "executive"].map((x) => <option key={x} value={x}>{t("rt_" + x)}</option>)}</select></div><div className="fit"><label>&nbsp;</label><button className="primary" onClick={gen}>{t("generate")}</button></div></div>
      {rep && <div className="box"><pre>{rep.markdown}</pre><button onClick={() => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([rep.markdown], { type: "text/markdown" })); a.download = `report-${rep.type}.md`; a.click(); }}>{t("download")}</button></div>}
      <h2>{t("timeline")}</h2><input aria-label={t("search")} placeholder={t("search")} value={q} onChange={(e) => setQ(e.target.value)} />
      <table><tbody>{[...ev].reverse().map((e: any) => <tr key={e.id}><td className="mute">{new Date(e.created_at + (e.created_at.endsWith("Z") ? "" : "Z")).toLocaleString(lang)}</td><td><b>{e.kind}</b></td><td className="mute">{e.entity_id}</td><td className="mute">{JSON.stringify(e.data).slice(0, 120)}</td></tr>)}</tbody></table>
      {!ev.length && <p className="mute">{t("none")}</p>}
    </>
  );
}

export function Settings({ onDeleted }: { onDeleted: () => void }) {
  const { t, api, me, refreshMe } = useC();
  const s = me?.settings || {};
  const set = async (b: any) => { await api.patch("/me/settings", b); refreshMe(); };
  return (
    <>
      <h1>{t("settingsTitle")}</h1>
      <label style={{ display: "flex", gap: 8, color: "inherit" }}><input type="checkbox" style={{ width: "auto" }} checked={!!s.allow_external_providers} onChange={(e) => set({ allow_external_providers: e.target.checked })} />{t("allowExternal")}</label>
      <label htmlFor="dm">{t("defaultModel")}</label><input id="dm" defaultValue={s.default_model} onBlur={(e) => set({ default_model: e.target.value })} />
      <label htmlFor="rt">{t("retention")}</label><input id="rt" type="number" min={1} defaultValue={s.retention_days || 365} onBlur={(e) => set({ retention_days: +e.target.value })} />
      <p className="mute">{t("privacy")}</p><p className="mute">{me?.email}</p>
      <div className="box"><b>{t("license")}</b><p>{t("licenseText")}</p></div>
      <p><button onClick={async () => { if (confirm(t("deleteConfirm"))) { await api.del("/me/data"); onDeleted(); } }} style={{ color: "var(--bad)" }}>{t("deleteAll")}</button></p>
    </>
  );
}

export function Queue({ jobs }: { jobs: any[] }) {
  const { t, setJobId, open, pid } = useC();
  const key = `raw.notes.${pid}`; const [n, setN] = useState("");
  useEffect(() => { try { setN(localStorage.getItem(key) || ""); } catch {} }, [key]);
  return (
    <>
      <h2 style={{ marginTop: 0 }}>{t("whileWorks")}</h2>
      <label htmlFor="notes">{t("notes")}</label>
      <textarea id="notes" style={{ minHeight: 140 }} placeholder={t("notesPlaceholder")} value={n} onChange={(e) => { setN(e.target.value); try { localStorage.setItem(key, e.target.value); } catch {} }} />
      <h3>{t("queue")}</h3>
      {jobs.slice(0, 6).map((j) => <div key={j.id} className="mute"><a href="#" onClick={(e) => { e.preventDefault(); setJobId(j.id); open("job"); }}>{j.id}</a> · {t("state_" + j.state)} {j.verification_status && <VStatus v={j.verification_status} />}</div>)}
      {!jobs.length && <p className="mute">{t("none")}</p>}
    </>
  );
}

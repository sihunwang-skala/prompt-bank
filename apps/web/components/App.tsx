"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Api, LANGS, Lang, detectLang, isTerminal } from "@raw/shared";
import { C, useT } from "./ctx";
import { Home, Compose, JobView, Constraints, Library, Refs, HistoryView, Settings, Queue } from "./views";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const NAV = [["home", "navHome"], ["compose", "navCompose"], ["constraints", "navConstraints"], ["library", "navLibrary"], ["refs", "navRefs"], ["history", "navHistory"], ["settings", "navSettings"]] as const;
const ls = { get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch {} } };

export default function App() {
  const [lang, setLang] = useState<Lang>("en");
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [view, setView] = useState("home");
  const [projects, setProjects] = useState<any[]>([]);
  const [pid, setPid] = useState("");
  const [me, setMe] = useState<any>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [seed, setSeed] = useState<any>(null);
  const [panel, setPanel] = useState(true);
  const [jobs, setJobs] = useState<any[]>([]);
  const t = useT(lang);
  const api = useMemo(() => new Api(API, token), [token]);

  useEffect(() => {
    const l = ls.get("raw.lang") as Lang | null;
    setLang(l === "ko" || l === "en" ? l : detectLang(navigator.language));
    setToken(ls.get("raw.token"));
    setPanel(ls.get("raw.panel") !== "0");
    setReady(true);
  }, []);
  useEffect(() => { document.documentElement.lang = lang; ls.set("raw.lang", lang); }, [lang]);

  const refreshMe = useCallback(() => { api.get("/me").then(setMe).catch(() => { setToken(null); ls.set("raw.token", ""); }); }, [api]);
  useEffect(() => { if (token) { refreshMe(); api.projects().then((p) => { setProjects(p); setPid((x) => x || p[0]?.id || ""); }).catch(() => {}); } }, [token, api, refreshMe]);
  useEffect(() => {
    if (!token || !pid) return;
    let on = true;
    const tick = () => api.jobs(pid).then((j) => on && setJobs(j)).catch(() => {});
    tick(); const id = setInterval(tick, 2000);
    return () => { on = false; clearInterval(id); };
  }, [token, pid, api]);

  if (!ready) return null;
  const langSel = (
    <label style={{ margin: 0, display: "flex", gap: 6, alignItems: "center" }}>
      <span className="mute">{t("language")}</span>
      <select aria-label={t("language")} value={lang} onChange={(e) => setLang(e.target.value as Lang)}>{LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</select>
    </label>
  );
  if (!token) return <Login api={api} t={t} langSel={langSel} onToken={(tk: string) => { ls.set("raw.token", tk); setToken(tk); }} />;

  const open = (v: string, extra?: any) => { setSeed(extra ?? null); setView(v); window.scrollTo(0, 0); };
  const running = jobs.filter((j) => !isTerminal(j.state));
  const ctx = { api, lang, t, pid, me, refreshMe, open, jobId, setJobId, seed };
  return (
    <C.Provider value={ctx}>
      <div className={`shell ${panel ? "" : "noside"}`}>
        <header className="top">
          <span className="brand">{t("appName")}</span>
          <select aria-label={t("project")} value={pid} onChange={(e) => setPid(e.target.value)} style={{ width: "auto" }}>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button onClick={async () => { const n = prompt(t("newProject")); if (n) { const p = await api.createProject(n); setProjects([p, ...projects]); setPid(p.id); } }}>+ {t("newProject")}</button>
          <span className="sp" />
          {langSel}
          <button onClick={() => { ls.set("raw.panel", panel ? "0" : "1"); setPanel(!panel); }}>{panel ? t("collapse") : t("expand")}</button>
          <button onClick={() => { ls.set("raw.token", ""); setToken(null); setProjects([]); setPid(""); }}>{t("signOut")}</button>
        </header>
        <nav className="side" aria-label="Main">{NAV.map(([k, l]) => <button key={k} aria-current={view === k ? "page" : undefined} onClick={() => open(k)}>{t(l)}</button>)}</nav>
        <main>
          {!pid ? <p>{t("newProject")} ↑</p> : view === "home" ? <Home jobs={jobs} /> : view === "compose" ? <Compose /> : view === "job" ? <JobView /> :
            view === "constraints" ? <Constraints /> : view === "library" ? <Library /> : view === "refs" ? <Refs /> : view === "history" ? <HistoryView /> : <Settings onDeleted={() => { ls.set("raw.token", ""); setToken(null); }} />}
        </main>
        {panel && <aside className="panel" aria-label={t("whileWorks")}><Queue jobs={jobs} /></aside>}
        <footer className="queue">
          <span>{t("queue")}: {running.length} {t("running").toLowerCase()}</span>
          {running.slice(0, 3).map((j) => <a key={j.id} href="#" onClick={(e) => { e.preventDefault(); setJobId(j.id); open("job"); }}>{j.id} · {t("state_" + j.state)}{j.stage ? ` · ${j.stage}` : ""}</a>)}
          <span className="sp" style={{ flex: 1 }} />
          <span title={t("licenseText")}>{t("license")}: PolyForm Noncommercial 1.0.0</span>
        </footer>
        <nav className="mobile-nav" aria-label="Mobile">{NAV.filter(([k]) => k !== "refs").map(([k, l]) => <button key={k} aria-current={view === k ? "page" : undefined} onClick={() => open(k)}>{t(l)}</button>)}</nav>
      </div>
    </C.Provider>
  );
}

function Login({ api, t, langSel, onToken }: any) {
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [err, setErr] = useState(""); const [reg, setReg] = useState(false);
  const submit = async (e: any) => {
    e.preventDefault(); setErr("");
    try { const r = await (reg ? api.register(email, pw) : api.login(email, pw)); onToken(r.token); }
    catch (x: any) { setErr(x.message === "Failed to fetch" ? t("apiOffline") : x.message); }
  };
  return (
    <div className="login">
      <div style={{ float: "right" }}>{langSel}</div>
      <h1>{t("appName")}</h1>
      <form onSubmit={submit}>
        <label htmlFor="em">{t("email")}</label><input id="em" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        <label htmlFor="pw">{t("password")}</label><input id="pw" type="password" required minLength={8} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete={reg ? "new-password" : "current-password"} />
        {err && <div className="err" role="alert">{err}</div>}
        <p><button className="primary" type="submit">{reg ? t("register") : t("signIn")}</button>{" "}<button type="button" onClick={() => setReg(!reg)}>{reg ? t("signIn") : t("register")}</button></p>
      </form>
      <p className="mute">{t("licenseText")}</p>
    </div>
  );
}

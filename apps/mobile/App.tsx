// NOT BUILT OR RUN: no iOS/Android toolchain or simulator was exercised for this scaffold.
// It reuses @raw/shared (API client, i18n, status helpers) and uses native bottom-tab navigation.
import { useEffect, useMemo, useState } from "react";
import { SafeAreaView, View, Text, TextInput, Pressable, ScrollView, StyleSheet, Platform, NativeModules, Alert } from "react-native";
import * as SecureStore from "expo-secure-store";
import { Api, Lang, LANGS, t as tr, fmtCost, isTerminal } from "@raw/shared";

const API = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000"; // Android emulator: http://10.0.2.2:8000
type Tab = "tasks" | "constraints" | "settings";

export default function App() {
  const locale = Platform.OS === "ios" ? NativeModules.SettingsManager?.settings?.AppleLocale : NativeModules.I18nManager?.localeIdentifier;
  const [lang, setLang] = useState<Lang>(String(locale ?? "").startsWith("ko") ? "ko" : "en");
  const [token, setToken] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("tasks");
  const api = useMemo(() => new Api(API, token), [token]);
  const t = (k: string) => tr(lang, k);
  useEffect(() => { SecureStore.getItemAsync("token").then((v) => v && setToken(v)); }, []);
  return (
    <SafeAreaView style={s.root}>
      <View style={s.top}>
        <Text style={s.brand}>{t("appName")}</Text>
        <View style={{ flexDirection: "row", gap: 6 }}>{LANGS.map((l) => <Pressable key={l.code} accessibilityRole="button" onPress={() => setLang(l.code)}><Text style={[s.chip, lang === l.code && s.chipOn]}>{l.label}</Text></Pressable>)}</View>
      </View>
      {!token ? <Login api={api} t={t} onToken={async (tk) => { await SecureStore.setItemAsync("token", tk); setToken(tk); }} /> : (
        <>
          <View style={{ flex: 1 }}>{tab === "tasks" ? <Tasks api={api} t={t} /> : tab === "constraints" ? <Constraints api={api} t={t} /> : <Settings t={t} onOut={async () => { await SecureStore.deleteItemAsync("token"); setToken(null); }} />}</View>
          <View style={s.tabs}>{(["tasks", "constraints", "settings"] as Tab[]).map((k) => <Pressable key={k} style={s.tab} onPress={() => setTab(k)} accessibilityRole="tab"><Text style={tab === k ? s.on : undefined}>{t(k === "tasks" ? "navHome" : k === "constraints" ? "navConstraints" : "navSettings")}</Text></Pressable>)}</View>
        </>
      )}
    </SafeAreaView>
  );
}

function Login({ api, t, onToken }: any) {
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [err, setErr] = useState("");
  const go = async (reg: boolean) => { try { onToken((await (reg ? api.register(email, pw) : api.login(email, pw))).token); } catch (e: any) { setErr(e.message); } };
  return (
    <View style={s.pad}>
      <TextInput style={s.in} placeholder={t("email")} autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} />
      <TextInput style={s.in} placeholder={t("password")} secureTextEntry value={pw} onChangeText={setPw} />
      {!!err && <Text style={s.err}>{err}</Text>}
      <Pressable style={s.btn} onPress={() => go(false)}><Text style={s.btnT}>{t("signIn")}</Text></Pressable>
      <Pressable style={s.btn2} onPress={() => go(true)}><Text>{t("register")}</Text></Pressable>
      <Text style={s.mute}>{t("licenseText")}</Text>
    </View>
  );
}

function Tasks({ api, t }: any) {
  const [pid, setPid] = useState(""); const [jobs, setJobs] = useState<any[]>([]); const [task, setTask] = useState("");
  useEffect(() => { api.projects().then(async (p: any[]) => setPid(p[0]?.id ?? (await api.createProject("Mobile")).id)); }, []);
  useEffect(() => { if (!pid) return; const f = () => api.jobs(pid).then(setJobs).catch(() => {}); f(); const i = setInterval(f, 2500); return () => clearInterval(i); }, [pid]);
  const run = async () => { try { await api.run({ project_id: pid, task, config: { model: "mock-1", review_depth: "standard", max_iterations: 3, max_cost: 0.5 } }); setTask(""); } catch (e: any) { Alert.alert(t("error"), e.message); } };
  return (
    <ScrollView contentContainerStyle={s.pad}>
      <TextInput style={[s.in, { minHeight: 80 }]} multiline placeholder={t("intent")} value={task} onChangeText={setTask} />
      <Pressable style={s.btn} onPress={run} disabled={!task.trim()}><Text style={s.btnT}>{t("execute")}</Text></Pressable>
      {jobs.map((j) => (
        <View key={j.id} style={s.card}>
          <Text style={s.bold}>{t("state_" + j.state)}{j.stage && !isTerminal(j.state) ? ` · ${j.stage}` : ""}</Text>
          {!!j.verification_status && <Text>{t("v_" + j.verification_status)}</Text>}
          <Text style={s.mute}>{t("recorded")}: {fmtCost(j.usage?.cost, t("unavailable"))} · {t("calls")}: {j.usage?.calls ?? 0}</Text>
          {!isTerminal(j.state) && <Pressable onPress={() => api.cancel(j.id)}><Text style={s.err}>{t("cancelJob")}</Text></Pressable>}
        </View>
      ))}
    </ScrollView>
  );
}

function Constraints({ api, t }: any) {
  const [list, setList] = useState<any[]>([]); const [txt, setTxt] = useState("");
  const load = () => api.projects().then((p: any[]) => p[0] && api.constraints(p[0].id)).then((r: any) => r && setList(r.constraints));
  useEffect(() => { load(); }, []);
  const add = async () => { const p = (await api.projects())[0]; await api.post("/constraints", { content: txt, project_id: p.id, check: { type: "semantic" } }); setTxt(""); load(); };
  return (
    <ScrollView contentContainerStyle={s.pad}>
      <TextInput style={s.in} placeholder={t("content")} value={txt} onChangeText={setTxt} />
      <Pressable style={s.btn} onPress={add} disabled={!txt.trim()}><Text style={s.btnT}>{t("add")}</Text></Pressable>
      {list.map((c) => <View key={c.id} style={s.card}><Text style={s.bold}>{c.content}</Text><Text style={s.mute}>{t("st_" + c.status)} · P{c.priority} · {t("ct_" + c.check.type)}</Text></View>)}
    </ScrollView>
  );
}

function Settings({ t, onOut }: any) {
  return <View style={s.pad}><Text style={s.bold}>{t("license")}</Text><Text>{t("licenseText")}</Text><Text style={s.mute}>{t("privacy")}</Text><Pressable style={s.btn2} onPress={onOut}><Text>{t("signOut")}</Text></Pressable></View>;
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#fafaf8" }, top: { padding: 12, borderBottomWidth: 1, borderColor: "#e4e3de", gap: 8 }, brand: { fontWeight: "600", fontSize: 16 },
  chip: { borderWidth: 1, borderColor: "#e4e3de", borderRadius: 12, paddingHorizontal: 10, paddingVertical: 3 }, chipOn: { borderColor: "#1f5eff", color: "#1f5eff" },
  pad: { padding: 16, gap: 10 }, in: { borderWidth: 1, borderColor: "#e4e3de", borderRadius: 6, padding: 10, backgroundColor: "#fff" },
  btn: { backgroundColor: "#1f5eff", padding: 12, borderRadius: 6, alignItems: "center" }, btnT: { color: "#fff", fontWeight: "600" }, btn2: { borderWidth: 1, borderColor: "#e4e3de", padding: 12, borderRadius: 6, alignItems: "center" },
  card: { borderWidth: 1, borderColor: "#e4e3de", borderRadius: 8, padding: 12, backgroundColor: "#fff", gap: 2 }, bold: { fontWeight: "600" }, mute: { color: "#6b6b66", fontSize: 12 }, err: { color: "#b3261e" },
  tabs: { flexDirection: "row", borderTopWidth: 1, borderColor: "#e4e3de", backgroundColor: "#fff" }, tab: { flex: 1, padding: 14, alignItems: "center" }, on: { color: "#1f5eff", fontWeight: "600" },
});

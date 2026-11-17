export type Json = any;
export class Api {
  constructor(public base: string, public token: string | null = null) {}
  async req(method: string, path: string, body?: Json, form?: FormData): Promise<Json> {
    const headers: Record<string, string> = {};
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const r = await fetch(this.base + path, { method, headers, body: form ?? (body !== undefined ? JSON.stringify(body) : undefined) });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? r.status));
    return data;
  }
  get = (p: string) => this.req("GET", p);
  post = (p: string, b: Json = {}) => this.req("POST", p, b);
  patch = (p: string, b: Json) => this.req("PATCH", p, b);
  put = (p: string, b: Json) => this.req("PUT", p, b);
  del = (p: string) => this.req("DELETE", p);
  upload = (pid: string, file: Blob & { name?: string }, role: string) => {
    const f = new FormData();
    f.append("file", file as any, (file as any).name ?? "file");
    f.append("role", role);
    return this.req("POST", `/projects/${pid}/references/file`, undefined, f);
  };
  register = (email: string, password: string) => this.post("/auth/register", { email, password });
  login = (email: string, password: string) => this.post("/auth/login", { email, password });
  projects = () => this.get("/projects");
  createProject = (name: string) => this.post("/projects", { name });
  jobs = (pid: string) => this.get(`/jobs?project_id=${pid}`);
  job = (id: string) => this.get(`/jobs/${id}`);
  run = (body: Json) => this.post("/jobs", body);
  estimate = (body: Json) => this.post("/estimate", body);
  cancel = (id: string) => this.post(`/jobs/${id}/cancel`);
  approve = (id: string) => this.post(`/jobs/${id}/approve`);
  change = (id: string, body: Json) => this.post(`/jobs/${id}/change`, body);
  constraints = (pid: string) => this.get(`/constraints?project_id=${pid}`);
  prompts = (pid: string, q = "") => this.get(`/projects/${pid}/prompts?q=${encodeURIComponent(q)}`);
  refs = (pid: string) => this.get(`/projects/${pid}/references`);
  packages = (pid: string) => this.get(`/projects/${pid}/packages`);
  history = (pid: string, q = "") => this.get(`/projects/${pid}/history?q=${encodeURIComponent(q)}`);
  report = (body: Json) => this.post("/reports", body);
}

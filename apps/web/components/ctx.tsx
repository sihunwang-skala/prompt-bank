"use client";
import { createContext, useContext } from "react";
import { Api, Lang, t as tr } from "@raw/shared";

export type Ctx = { api: Api; lang: Lang; t: (k: string) => string; pid: string; me: any; refreshMe: () => void; open: (v: string, extra?: any) => void; jobId: string | null; setJobId: (id: string | null) => void; seed: any; };
export const C = createContext<Ctx>(null as any);
export const useC = () => useContext(C);
export const useT = (lang: Lang) => (k: string) => tr(lang, k);

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import enUS from "../../locales/en-US.json";
import arAE from "../../locales/ar-AE.json";
import frFR from "../../locales/fr-FR.json";
import deDE from "../../locales/de-DE.json";
import hiIN from "../../locales/hi-IN.json";

type Bundle = Record<string, string>;
const bundles: Record<string, Bundle> = { "en-US": enUS, "ar-AE": arAE, "fr-FR": frFR, "de-DE": deDE, "hi-IN": hiIN };
const fallback = "en-US";
const rtl = new Set(["ar", "fa", "ur", "he"]);

type LanguageContextValue = { locale: string; systemDefault: boolean; setLocale: (locale: string) => void; t: (key: string) => string };
const LanguageContext = createContext<LanguageContextValue>({ locale: fallback, systemDefault: true, setLocale: () => undefined, t: (key) => key });

function resolveLocale(value: string): string {
  if (bundles[value]) return value;
  const language = value.split(/[-_]/)[0].toLowerCase();
  return Object.keys(bundles).find((key) => key.split("-")[0] === language) ?? fallback;
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState(fallback);
  const [systemDefault, setSystemDefault] = useState(true);
  const apply = (resolved: string) => {
    setLocaleState(resolved);
    document.documentElement.lang = resolved;
    document.documentElement.dir = rtl.has(resolved.split("-")[0]) ? "rtl" : "ltr";
  };
  const setLocale = (next: string) => {
    if (next === "system") {
      setSystemDefault(true);
      localStorage.removeItem("xtobe-locale");
      invoke<string>("get_system_locale").then((value) => apply(resolveLocale(value))).catch(() => apply(fallback));
      return;
    }
    setSystemDefault(false);
    const resolved = resolveLocale(next);
    apply(resolved);
    localStorage.setItem("xtobe-locale", resolved);
  };
  useEffect(() => {
    const saved = localStorage.getItem("xtobe-locale");
    if (saved) { setSystemDefault(false); apply(saved); }
    else invoke<string>("get_system_locale").then((value) => apply(resolveLocale(value))).catch(() => apply(fallback));
  }, []);
  const value = useMemo(() => ({ locale, systemDefault, setLocale, t: (key: string) => bundles[locale][key] ?? bundles[fallback][key] ?? key }), [locale, systemDefault]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export const useTranslation = () => useContext(LanguageContext);

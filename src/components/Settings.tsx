import { useTranslation } from "./LanguageProvider";

const OPTIONS = [
  ["system", "System default"],
  ["en-US", "English"],
  ["ar-AE", "العربية (Arabic)"],
  ["fr-FR", "Français (French)"],
  ["de-DE", "Deutsch (German)"],
  ["hi-IN", "हिन्दी (Hindi)"],
] as const;

export default function Settings() {
  const { locale, systemDefault, setLocale, t } = useTranslation();
  return (
    <section className="panel col-span-12">
      <div className="panel-title"><span className="text-neon">⚙</span> {t("language")}</div>
      <div className="grid grid-cols-1 md:grid-cols-[minmax(14rem,22rem)_1fr] gap-4 items-center">
        <label className="text-xs text-slate-300">{t("language")}
          <select className="block mt-1 bg-edge border border-edge rounded p-2 w-full" value={systemDefault ? "system" : locale} onChange={(event) => setLocale(event.target.value)}>
            {OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <p className="text-[10px] text-slate-500">Changes apply immediately to the UI, local AI explanations, reports, and notifications. No network translation is used.</p>
      </div>
    </section>
  );
}

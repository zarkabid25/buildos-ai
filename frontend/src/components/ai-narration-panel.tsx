"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

/** Phase 9 (PLAT-048): a small, reusable "Ask AI" panel shared across all
 * three portals' narration features. Always clearly labels its output as
 * an AI-generated suggestion, distinct from the verified data around it,
 * and never renders anything until the person explicitly asks for it. */
export function AiNarrationPanel({
  label = "Ask AI to summarize",
  onGenerate,
  theme = "light",
}: {
  label?: string;
  onGenerate: () => Promise<{ narration: string }>;
  theme?: "light" | "dark";
}) {
  const [narration, setNarration] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    setLoading(true);
    setError(null);
    try {
      const result = await onGenerate();
      setNarration(result.narration);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't generate a summary right now.");
    } finally {
      setLoading(false);
    }
  }

  const isDark = theme === "dark";
  return (
    <div className={`rounded-lg border p-3 ${isDark ? "border-white/10 bg-slate-900/50" : "border-dashed border-gray-300 bg-gray-50"}`}>
      <button
        onClick={handleClick}
        disabled={loading}
        className={`flex items-center gap-1.5 text-xs font-medium disabled:opacity-50 ${isDark ? "text-blue-400 hover:text-blue-300" : "text-blue-600 hover:text-blue-700"}`}
      >
        <Sparkles className="h-3.5 w-3.5" />
        {loading ? "Thinking..." : label}
      </button>
      {error && <p className={`mt-2 text-xs ${isDark ? "text-red-400" : "text-red-600"}`}>{error}</p>}
      {narration && (
        <div className={`mt-2 rounded-md p-2.5 text-xs leading-relaxed ${isDark ? "bg-slate-950 text-slate-300" : "bg-white text-gray-700"}`}>
          <p className={`mb-1 text-[10px] font-semibold uppercase tracking-wide ${isDark ? "text-blue-400" : "text-blue-600"}`}>AI suggestion -- verify before acting</p>
          <p className="whitespace-pre-wrap">{narration}</p>
        </div>
      )}
    </div>
  );
}

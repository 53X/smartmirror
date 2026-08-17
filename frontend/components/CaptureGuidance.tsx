import type { ReactElement } from "react";
import { CAPTURE_RULES } from "@/lib/captureGuidance";

/**
 * Short checklist shown before camera or upload so fewer stills fail preprocess.
 */
export function CaptureGuidance(): ReactElement {
  return (
    <ul className="space-y-1.5 rounded-2xl border border-white/10 bg-zinc-900/80 px-4 py-3 text-sm text-zinc-300">
      {CAPTURE_RULES.map((rule) => (
        <li key={rule} className="flex gap-2">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-200" />
          <span>{rule}</span>
        </li>
      ))}
    </ul>
  );
}

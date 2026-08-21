import type { ReactElement } from "react";
import { CAPTURE_RULES } from "@/lib/captureGuidance";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Short checklist shown before camera or upload so fewer stills fail preprocess.
 */
export function CaptureGuidance(): ReactElement {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Before you capture</CardTitle>
        <CardDescription>A rejected still cannot generate a look.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-3 text-base text-muted-foreground">
          {CAPTURE_RULES.map((rule) => (
            <li key={rule} className="flex gap-3">
              <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" />
              <span>{rule}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

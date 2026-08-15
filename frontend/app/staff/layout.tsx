"use client";

import { StaffAuthProvider } from "@/components/StaffAuthProvider";
import type { ReactNode } from "react";

export default function StaffLayout({ children }: { children: ReactNode }) {
  return <StaffAuthProvider>{children}</StaffAuthProvider>;
}

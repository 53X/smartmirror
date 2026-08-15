"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { DEV_STAFF_TOKEN, isAuthDevBypass } from "@/lib/supabase/browser";

const STAFF_TOKEN_KEY = "smartmirror.staff.token";

interface StaffAuthValue {
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
}

const StaffAuthContext = createContext<StaffAuthValue | null>(null);

export function StaffAuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setToken] = useState<string | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(STAFF_TOKEN_KEY);
    if (stored) {
      setToken(stored);
    }
  }, []);

  const value = useMemo<StaffAuthValue>(
    () => ({
      accessToken,
      setAccessToken: (token) => {
        setToken(token);
        if (typeof window === "undefined") {
          return;
        }
        if (token) {
          window.localStorage.setItem(STAFF_TOKEN_KEY, token);
        } else {
          window.localStorage.removeItem(STAFF_TOKEN_KEY);
        }
      },
    }),
    [accessToken],
  );

  return <StaffAuthContext.Provider value={value}>{children}</StaffAuthContext.Provider>;
}

export function useStaffAuth(): StaffAuthValue {
  const context = useContext(StaffAuthContext);
  if (!context) {
    throw new Error("useStaffAuth must be used within StaffAuthProvider");
  }
  return context;
}

export function useStaffTokenOrBypass(): string | null {
  const { accessToken } = useStaffAuth();
  if (accessToken) {
    return accessToken;
  }
  if (isAuthDevBypass()) {
    return DEV_STAFF_TOKEN;
  }
  return null;
}

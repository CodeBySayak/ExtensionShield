/**
 * ScanModeContext – User vs Dev mode for scanner flows.
 * Persists to localStorage (extensionshield.scanMode). SSR-safe: no window access during server render.
 */
import React, { createContext, useContext, useState, useEffect } from "react";

const STORAGE_KEY = "extensionshield.scanMode";

/** @type {"user" | "dev"} */
const DEFAULT_MODE = "user";

function isValidMode(value) {
  return value === "user" || value === "dev";
}

const ScanModeContext = createContext(null);

export function useScanMode() {
  const context = useContext(ScanModeContext);
  if (!context) {
    throw new Error("useScanMode must be used within a ScanModeProvider");
  }
  return context;
}

export function ScanModeProvider({ children }) {
  const [mode, setModeState] = useState(DEFAULT_MODE);

  // Hydrate from localStorage on mount (SSR-safe: only runs on client)
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (isValidMode(stored)) setModeState(stored);
    } catch (_) {
      // ignore
    }
  }, []);

  // Persist when mode changes
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch (_) {
      // ignore
    }
  }, [mode]);

  const setMode = (next) => {
    if (isValidMode(next)) setModeState(next);
  };

  return (
    <ScanModeContext.Provider value={{ mode, setMode }}>
      {children}
    </ScanModeContext.Provider>
  );
}

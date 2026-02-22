/**
 * ScanModeToggle – Segmented control: User | Dev.
 * Renders next to theme toggle; persists via ScanModeContext.
 */
import React, { useRef, useCallback } from "react";
import { useScanMode } from "../context/ScanModeContext";
import "./ScanModeToggle.scss";

const OPTIONS = [
  { value: "user", label: "User" },
  { value: "dev", label: "Dev" },
];

export default function ScanModeToggle({ className = "", compact = false }) {
  const { mode, setMode } = useScanMode();
  const tabListRef = useRef(null);

  const handleKeyDown = useCallback(
    (e) => {
      const idx = OPTIONS.findIndex((o) => o.value === mode);
      if (e.key === "ArrowLeft" && idx > 0) {
        e.preventDefault();
        setMode(OPTIONS[idx - 1].value);
      } else if (e.key === "ArrowRight" && idx >= 0 && idx < OPTIONS.length - 1) {
        e.preventDefault();
        setMode(OPTIONS[idx + 1].value);
      }
    },
    [mode, setMode]
  );

  return (
    <div
      ref={tabListRef}
      className={`scan-mode-toggle ${compact ? "scan-mode-toggle--compact" : ""} ${className}`.trim()}
      role="tablist"
      aria-label="Scan mode"
    >
      {OPTIONS.map((opt) => {
        const isSelected = mode === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={isSelected}
            aria-label={`${opt.label} mode`}
            title={`${opt.label} mode`}
            tabIndex={isSelected ? 0 : -1}
            className={`scan-mode-toggle__tab ${isSelected ? "scan-mode-toggle__tab--active" : ""}`}
            onClick={() => setMode(opt.value)}
            onKeyDown={handleKeyDown}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

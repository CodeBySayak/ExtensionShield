import React, { useEffect, useMemo, useState } from "react";
import ShieldLogo from "./ShieldLogo";
import "./ScanActivityIndicator.scss";

const DEFAULT_MESSAGES = [
  "Threat analysis in progress",
  "Evidence collection in progress",
  "Policy review in progress",
  "Report generation in progress",
];

const STAGE_MESSAGES = {
  extracting: "Extension extraction in progress",
  security_scan: "Security analysis in progress",
  building_evidence: "Evidence building in progress",
  applying_rules: "Governance checks in progress",
  generating_report: "Report generation in progress",
};

const ScanActivityIndicator = ({
  title = "Scan in progress",
  stage = null,
  messages = DEFAULT_MESSAGES,
  meta = null,
  variant = "page",
  size = null,
  hideText = false,
  className = "",
}) => {
  const resolvedMessages = useMemo(() => {
    const stageMessage = stage ? STAGE_MESSAGES[stage] : null;
    const pool = [stageMessage, ...messages].filter(Boolean);
    return pool.length > 0 ? [...new Set(pool)] : DEFAULT_MESSAGES;
  }, [messages, stage]);

  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    setMessageIndex(0);
  }, [resolvedMessages]);

  useEffect(() => {
    if (resolvedMessages.length <= 1) return undefined;

    const intervalId = window.setInterval(() => {
      setMessageIndex((current) => (current + 1) % resolvedMessages.length);
    }, 2200);

    return () => window.clearInterval(intervalId);
  }, [resolvedMessages]);

  const currentMessage = resolvedMessages[messageIndex] || resolvedMessages[0];
  const resolvedSize =
    size ?? (variant === "button" ? 18 : variant === "inline" ? 42 : 64);

  return (
    <div className={`scan-activity-indicator scan-activity-indicator--${variant} ${className}`.trim()}>
      <div className="scan-activity-indicator__visual" aria-hidden="true">
        <div className="scan-activity-indicator__glow" />
        <div className="scan-activity-indicator__ring scan-activity-indicator__ring--outer" />
        <div className="scan-activity-indicator__ring scan-activity-indicator__ring--middle" />
        <div className="scan-activity-indicator__ring scan-activity-indicator__ring--inner" />
        <div className="scan-activity-indicator__core">
          <ShieldLogo size={resolvedSize} className="scan-activity-indicator__shield" />
        </div>
      </div>

      {!hideText && (
        <div className="scan-activity-indicator__content">
          <p className="scan-activity-indicator__eyebrow">ExtensionShield scanner</p>
          <h2 className="scan-activity-indicator__title">{title}</h2>
          <p className="scan-activity-indicator__status" aria-live="polite">
            {currentMessage}
          </p>
          {meta ? <p className="scan-activity-indicator__meta">{meta}</p> : null}
        </div>
      )}
    </div>
  );
};

export default ScanActivityIndicator;

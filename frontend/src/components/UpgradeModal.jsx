/**
 * UpgradeModal – Placeholder paywall/upgrade modal. No billing logic; wire later.
 */
import React, { useEffect, useRef } from "react";
import "./UpgradeModal.scss";

export default function UpgradeModal({ isOpen, onClose }) {
  const contentRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;
    const previouslyFocused = document.activeElement;
    const el = contentRef.current;
    if (el) {
      const focusables = el.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusables[0]) focusables[0].focus();
    }
    const handleEscape = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("keydown", handleEscape);
      if (previouslyFocused && typeof previouslyFocused.focus === "function") {
        previouslyFocused.focus();
      }
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="upgrade-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upgrade-modal-title"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div ref={contentRef} className="upgrade-modal">
        <button
          type="button"
          className="upgrade-modal__close"
          onClick={onClose}
          aria-label="Close"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
        <h2 id="upgrade-modal-title" className="upgrade-modal__title">
          Upgrade to Pro
        </h2>
        <p className="upgrade-modal__body">
          Dev Mode (upload private CRX/ZIP) is available on Pro. Billing and plans can be wired here later.
        </p>
        <button type="button" className="upgrade-modal__btn" onClick={onClose}>
          Got it
        </button>
      </div>
    </div>
  );
}

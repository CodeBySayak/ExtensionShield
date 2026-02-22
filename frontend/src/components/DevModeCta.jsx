/**
 * DevModeCta – Micro-CTA under the hero bullet: "Building an extension? Dev Mode (Pro) to upload a private CRX/ZIP."
 * Click behavior: paid → switch to dev + go to scan; not signed in → open sign-in modal; signed in but not paid → open upgrade modal.
 */
import React, { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useScanMode } from "../context/ScanModeContext";
import { useAuth } from "../context/AuthContext";
import UpgradeModal from "./UpgradeModal";
import "./DevModeCta.scss";

// TODO: wire to real plan/subscription when available (e.g. user?.plan === "pro", subscription tier)
function useIsPro() {
  const { user, isAuthenticated } = useAuth();
  // Stub: no plan/subscription in AuthContext yet
  const isPro = false;
  return { isPro, isAuthenticated };
}

export default function DevModeCta({ className = "" }) {
  const navigate = useNavigate();
  const { setMode } = useScanMode();
  const { isAuthenticated, openSignInModal } = useAuth();
  const { isPro } = useIsPro();
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);

  const handlePillClick = useCallback(() => {
    if (isPro) {
      setMode("dev");
      navigate("/scan");
      return;
    }
    if (!isAuthenticated) {
      openSignInModal();
      return;
    }
    setUpgradeModalOpen(true);
  }, [isPro, isAuthenticated, openSignInModal, setMode, navigate]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handlePillClick();
      }
    },
    [handlePillClick]
  );

  return (
    <>
      <p className={`dev-mode-cta ${className}`.trim()} aria-label="Dev Mode call to action">
        <span className="dev-mode-cta__prefix" aria-hidden="true">
          {"</>"}
        </span>{" "}
        Building an extension?{" "}
        <button
          type="button"
          className="dev-mode-cta__pill"
          onClick={handlePillClick}
          onKeyDown={handleKeyDown}
          aria-label="Switch to Dev Mode (Pro) to upload a private CRX or ZIP"
          title="Switch to Dev Mode to upload CRX/ZIP (Pro)"
        >
          Dev Mode (Pro)
        </button>{" "}
        to upload a private CRX/ZIP.
      </p>
      <UpgradeModal isOpen={upgradeModalOpen} onClose={() => setUpgradeModalOpen(false)} />
    </>
  );
}

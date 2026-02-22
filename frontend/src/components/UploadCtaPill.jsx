/**
 * UploadCtaPill – Micro-CTA under the hero bullet: "Building an extension? [Upload CRX/ZIP (Pro)] to scan a private build."
 * Click: logged out → sign-in modal then redirect to /scan/upload; logged in not Pro → upgrade modal then redirect; Pro → go to /scan/upload.
 */
import React, { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useUpgradeModal } from "../context/UpgradeModalContext";
import "./UploadCtaPill.scss";

const SCAN_UPLOAD_PATH = "/scan/upload";

// TODO: wire to real plan/subscription when available
function useIsPro() {
  const isPro = false;
  return { isPro };
}

export default function UploadCtaPill({ className = "" }) {
  const navigate = useNavigate();
  const { isAuthenticated, openSignInModal } = useAuth();
  const { openUpgradeModal } = useUpgradeModal();
  const { isPro } = useIsPro();

  const handlePillClick = useCallback(() => {
    if (!isAuthenticated) {
      try {
        sessionStorage.setItem("auth:returnTo", SCAN_UPLOAD_PATH);
      } catch (_) {}
      openSignInModal();
      return;
    }
    if (!isPro) {
      openUpgradeModal({ redirectOnClose: SCAN_UPLOAD_PATH });
      return;
    }
    navigate(SCAN_UPLOAD_PATH);
  }, [isAuthenticated, openSignInModal, isPro, navigate, openUpgradeModal]);

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
    <p className={`upload-cta-pill ${className}`.trim()} aria-label="Upload CRX/ZIP call to action">
      <span className="upload-cta-pill__prefix" aria-hidden="true">
        {"</>"}
      </span>{" "}
      Building an extension?{" "}
      <button
        type="button"
        className="upload-cta-pill__btn"
        onClick={handlePillClick}
        onKeyDown={handleKeyDown}
        aria-label="Upload CRX/ZIP (Pro) to scan a private build"
        title="Upload CRX or ZIP to scan a private build (Pro)"
      >
        Upload CRX/ZIP (Pro)
      </button>{" "}
      to scan a private build.
    </p>
  );
}

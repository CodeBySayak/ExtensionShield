/**
 * UpgradeModalContext – Global upgrade/paywall modal. Open from ScanContext (403 PRO_REQUIRED) or UploadCtaPill.
 * Supports redirectOnClose so pill can send user to /scan/upload after closing modal.
 */
import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import UpgradeModal from "../components/UpgradeModal";

const UpgradeModalContext = createContext(null);

export function useUpgradeModal() {
  const ctx = useContext(UpgradeModalContext);
  if (!ctx) {
    return { openUpgradeModal: () => {}, closeUpgradeModal: () => {} };
  }
  return ctx;
}

export function UpgradeModalProvider({ children }) {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const redirectOnCloseRef = useRef(null);

  const openUpgradeModal = useCallback((options) => {
    redirectOnCloseRef.current = options?.redirectOnClose || null;
    setIsOpen(true);
  }, []);

  const closeUpgradeModal = useCallback(() => {
    const redirectTo = redirectOnCloseRef.current;
    redirectOnCloseRef.current = null;
    setIsOpen(false);
    if (redirectTo && typeof redirectTo === "string" && redirectTo.startsWith("/")) {
      navigate(redirectTo);
    }
  }, [navigate]);

  return (
    <UpgradeModalContext.Provider value={{ openUpgradeModal, closeUpgradeModal }}>
      {children}
      <UpgradeModal isOpen={isOpen} onClose={closeUpgradeModal} />
    </UpgradeModalContext.Provider>
  );
}

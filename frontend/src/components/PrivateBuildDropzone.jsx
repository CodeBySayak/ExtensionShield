/**
 * PrivateBuildDropzone – Upload CTA for /scan/upload: drop area + "Choose file", filename chip.
 * Uses useExtensionUpload; when disabled, non-interactive (used with overlay for auth/Pro gate).
 */
import React, { useState, useRef, useCallback } from "react";
import { useExtensionUpload } from "../hooks/useExtensionUpload";
import ScanActivityIndicator from "./ScanActivityIndicator";
import "./PrivateBuildDropzone.scss";

const ACCEPT = ".crx,.zip";
const MAX_SIZE_MB = 25;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

function isValidFile(file) {
  if (!file?.name) return false;
  const ext = file.name.split(".").pop()?.toLowerCase();
  if (ext !== "crx" && ext !== "zip") return false;
  if (file.size > MAX_SIZE_BYTES) return false;
  return true;
}

function handleFiles(files, { onValid, inputRef }) {
  const file = files?.[0];
  if (!file || !isValidFile(file)) return;
  onValid(file);
  if (inputRef?.current) inputRef.current.value = "";
}

export default function PrivateBuildDropzone({ disabled = false }) {
  const { uploadFile, isUploading } = useExtensionUpload();
  const [isDragActive, setIsDragActive] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState(null);
  const inputRef = useRef(null);

  const handleDragEnter = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) setIsDragActive(true);
    },
    [disabled]
  );

  const handleDragLeave = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!e.currentTarget.contains(e.relatedTarget)) setIsDragActive(false);
    },
    []
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const applyFile = useCallback(
    (file) => {
      setSelectedFileName(file.name);
      uploadFile(file);
    },
    [uploadFile]
  );

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragActive(false);
      if (disabled || isUploading) return;
      handleFiles(e.dataTransfer?.files, { onValid: applyFile, inputRef });
    },
    [disabled, isUploading, applyFile]
  );

  const handleFileChange = useCallback(
    (e) => {
      handleFiles(e.target?.files, { onValid: applyFile, inputRef });
    },
    [applyFile]
  );

  const clearFile = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setSelectedFileName(null);
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const handleChooseClick = useCallback(() => {
    if (disabled || isUploading) return;
    inputRef.current?.click();
  }, [disabled, isUploading]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (!disabled) handleChooseClick();
      }
    },
    [disabled, handleChooseClick]
  );

  return (
    <div
      className={`private-build-dropzone private-upload-card ${isDragActive ? "private-build-dropzone--active is-drag-active" : ""} ${isUploading ? "private-build-dropzone--loading" : ""} ${disabled ? "private-build-dropzone--disabled" : ""}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label="Drop CRX or ZIP to scan a private build"
      onKeyDown={handleKeyDown}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        onChange={handleFileChange}
        className="private-build-dropzone__input"
        aria-hidden="true"
        tabIndex={-1}
        disabled={disabled}
      />
      <div className="private-build-dropzone__content private-upload-dropzone">
        <h3 className="private-build-dropzone__title">
          {isDragActive ? "Release to upload" : isUploading ? "Scan in progress" : "Drop CRX/ZIP here"}
        </h3>
        <p className="private-build-dropzone__sub">{isUploading ? "Secure upload in progress" : "or choose file"}</p>
        <p className="private-build-dropzone__micro">Max {MAX_SIZE_MB}MB • Private by default</p>
        <button
          type="button"
          className="private-build-dropzone__btn"
          onClick={handleChooseClick}
          disabled={disabled || isUploading}
          aria-label="Choose file"
        >
          <span className="private-build-dropzone__btn-icon" aria-hidden>
            {isUploading ? (
              <ScanActivityIndicator variant="button" title="Scan in progress" hideText />
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            )}
          </span>
          <span>{isUploading ? "Scan in progress" : "Choose file"}</span>
        </button>
        {selectedFileName && (
          <div className="private-build-dropzone__chip">
            <span className="private-build-dropzone__chip-name">{selectedFileName}</span>
            <button
              type="button"
              className="private-build-dropzone__chip-clear"
              onClick={clearFile}
              aria-label="Clear file"
            >
              ×
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

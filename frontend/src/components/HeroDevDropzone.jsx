import React, { useState, useRef, useCallback } from "react";
import { useExtensionUpload } from "../hooks/useExtensionUpload";
import "./HeroDevDropzone.scss";

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

export default function HeroDevDropzone({ variant }) {
  const isMinimal = variant === "minimal";
  const isOrbit = variant === "orbit";
  const { uploadFile, isUploading } = useExtensionUpload();
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef(null);

  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!e.currentTarget.contains(e.relatedTarget)) setIsDragActive(false);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragActive(false);
      if (isUploading) return;
      const file = e.dataTransfer?.files?.[0];
      if (!file || !isValidFile(file)) return;
      uploadFile(file);
    },
    [uploadFile, isUploading]
  );

  const handleFileChange = useCallback(
    (e) => {
      const file = e.target?.files?.[0];
      if (!file || !isValidFile(file)) return;
      uploadFile(file);
      e.target.value = "";
    },
    [uploadFile]
  );

  const handleChooseClick = useCallback(() => {
    if (isUploading) return;
    inputRef.current?.click();
  }, [isUploading]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleChooseClick();
      }
    },
    [handleChooseClick]
  );

  return (
    <div
      className={`hero-dev-dropzone ${isMinimal ? "hero-dev-dropzone--minimal" : ""} ${isOrbit ? "hero-dev-dropzone--orbit" : ""} ${isDragActive ? "hero-dev-dropzone--active" : ""} ${isUploading ? "hero-dev-dropzone--loading" : ""}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      aria-label="Drop your extension here. Upload CRX or ZIP to scan a private build."
      onKeyDown={handleKeyDown}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        onChange={handleFileChange}
        className="hero-dev-dropzone__input"
        aria-hidden="true"
        tabIndex={-1}
      />
      <div className="hero-dev-dropzone__content">
        <h3 className="hero-dev-dropzone__title">
          {isDragActive ? "Release to upload" : (isMinimal || isOrbit) ? "Drop CRX or ZIP anywhere" : "Drop your extension here"}
        </h3>
        {!isMinimal && !isOrbit && (
          <p className="hero-dev-dropzone__subtitle">
            Upload CRX or ZIP to scan a private build
          </p>
        )}
        <p className="hero-dev-dropzone__micro">
          Max {MAX_SIZE_MB}MB • Deleted after scan (unless saved)
        </p>
        <button
          type="button"
          className="hero-dev-dropzone__btn"
          onClick={handleChooseClick}
          disabled={isUploading}
          aria-label="Choose file"
        >
          {isUploading ? "Uploading…" : "Choose file"}
        </button>
      </div>
    </div>
  );
}

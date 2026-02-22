import React, { useRef, useCallback } from "react";
import { useExtensionUpload } from "../hooks/useExtensionUpload";
import "./FileUploadSection.scss";

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

export default function FileUploadSection() {
  const { uploadFile, isUploading } = useExtensionUpload();
  const inputRef = useRef(null);

  const handleChange = useCallback(
    (e) => {
      const file = e.target?.files?.[0];
      if (!file || !isValidFile(file)) return;
      uploadFile(file);
      e.target.value = "";
    },
    [uploadFile]
  );

  const handleClick = useCallback(() => {
    if (isUploading) return;
    inputRef.current?.click();
  }, [isUploading]);

  return (
    <section
      id="file-upload-section"
      className="file-upload-section"
      aria-labelledby="file-upload-section-title"
    >
      <h2 id="file-upload-section-title" className="file-upload-section__title">
        Upload CRX/ZIP File
      </h2>
      <p className="file-upload-section__hint">
        Max {MAX_SIZE_MB}MB. Deleted after scan (unless saved).
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        onChange={handleChange}
        className="file-upload-section__input"
        aria-label="Choose CRX or ZIP file to upload"
      />
      <button
        type="button"
        className="file-upload-section__btn"
        onClick={handleClick}
        disabled={isUploading}
        aria-label="Choose file to scan"
      >
        {isUploading ? "Uploading…" : "Choose file"}
      </button>
    </section>
  );
}

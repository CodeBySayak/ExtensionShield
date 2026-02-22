/**
 * Shared extension upload hook. Exposes the same upload flow used by the scan pipeline.
 * Use from FileUploadSection and HeroDevDropzone so both trigger the same handler.
 */
import { useScan } from "../context/ScanContext";

export function useExtensionUpload() {
  const { handleFileUpload, isScanning } = useScan();
  return {
    uploadFile: handleFileUpload,
    isUploading: isScanning,
  };
}

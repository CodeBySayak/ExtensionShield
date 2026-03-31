import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ScanProvider, useScan } from "../ScanContext";
import realScanService from "../../services/realScanService";
import databaseService from "../../services/databaseService";

const mockNavigate = vi.fn();
const mockOpenSignInModal = vi.fn();

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock("../AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    accessToken: "token-123",
    openSignInModal: mockOpenSignInModal,
  }),
}));

vi.mock("../../services/realScanService", () => ({
  default: {
    extractExtensionId: vi.fn(),
    getRealScanResults: vi.fn(),
    triggerScan: vi.fn(),
    getDeepScanLimitStatus: vi.fn(),
    hasCachedResults: vi.fn(),
    checkScanStatus: vi.fn(),
    uploadAndScan: vi.fn(),
  },
}));

vi.mock("../../services/databaseService", () => ({
  default: {
    getScanHistory: vi.fn(),
    getDashboardMetrics: vi.fn(),
  },
}));

const TEST_URL =
  "https://chromewebstore.google.com/detail/test/abcdefghijklmnopabcdefghijklmnop";
const TEST_EXTENSION_ID = "abcdefghijklmnopabcdefghijklmnop";

// Covers the cached-result path that must still write user history for signed-in scans.
function TriggerScanButton() {
  const { startScan } = useScan();

  return <button onClick={() => startScan(TEST_URL)}>Scan</button>;
}

describe("ScanContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    realScanService.extractExtensionId.mockReturnValue(TEST_EXTENSION_ID);
    realScanService.getRealScanResults.mockResolvedValue({
      extension_id: TEST_EXTENSION_ID,
      extension_name: "Test Extension",
      status: "completed",
    });
    realScanService.triggerScan.mockResolvedValue({
      already_scanned: true,
      extension_id: TEST_EXTENSION_ID,
      status: "completed",
    });
    databaseService.getScanHistory.mockResolvedValue([]);
    databaseService.getDashboardMetrics.mockResolvedValue({
      totalScans: { value: 0, sparkline: [0] },
      highRisk: { value: 0, sparkline: [0] },
      totalFiles: { value: 0, sparkline: [0] },
      totalVulnerabilities: { value: 0, sparkline: [0] },
    });
  });

  it("records cached scans for authenticated users so history stays user-scoped", async () => {
    render(
      <ScanProvider>
        <TriggerScanButton />
      </ScanProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Scan" }));

    await waitFor(() => {
      expect(realScanService.triggerScan).toHaveBeenCalledWith(TEST_URL);
    });

    await waitFor(() => {
      expect(databaseService.getScanHistory).toHaveBeenCalledWith(50, "token-123");
      expect(databaseService.getDashboardMetrics).toHaveBeenCalled();
    });
  });
});

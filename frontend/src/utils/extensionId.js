/**
 * Extension ID Normalization Utility
 * 
 * Supports two ID formats:
 * 1. Chrome extension IDs: 32 characters using base32 encoding (a-p)
 * 2. Upload scan IDs: UUIDs (for private CRX/ZIP uploads)
 * 
 * This utility extracts and normalizes extension IDs from various inputs,
 * handling edge cases like trailing characters, URL fragments, etc.
 */

// UUID v4 regex pattern (8-4-4-4-12 hex format)
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Checks if input is a valid UUID (upload scan ID)
 * @param {string} input - String to check
 * @returns {boolean} - True if valid UUID format
 */
export function isUUID(input) {
  return typeof input === 'string' && UUID_REGEX.test(input);
}

/**
 * Normalizes an extension ID by extracting a valid 32-character base32 string (a-p)
 * or returning a valid UUID as-is (for upload scans).
 * Chrome extension IDs use base32 encoding which only uses letters a-p (lowercase).
 * 
 * @param {string} input - Raw input that may contain an extension ID or UUID
 * @returns {string} - Normalized 32-character extension ID, UUID, or empty string if not found
 * 
 * @example
 * normalizeExtensionId("jcmljanephecacpljcpiogonhhadfpda") // "jcmljanephecacpljcpiogonhhadfpda"
 * normalizeExtensionId("jcmljanephecacpljcpiogonhhadfpda)") // "jcmljanephecacpljcpiogonhhadfpda" (strips trailing char)
 * normalizeExtensionId("/scan/progress/jcmljanephecacpljcpiogonhhadfpda") // "jcmljanephecacpljcpiogonhhadfpda"
 * normalizeExtensionId("50276216-0386-452c-ab31-485b72dabe8f") // "50276216-0386-452c-ab31-485b72dabe8f" (UUID)
 * normalizeExtensionId("invalid") // ""
 */
export function normalizeExtensionId(input) {
  if (!input || typeof input !== 'string') {
    return '';
  }

  const trimmed = input.trim();

  // Check if it's a valid UUID (upload scan ID) - return as-is
  if (isUUID(trimmed)) {
    return trimmed.toLowerCase();
  }

  // Chrome extension IDs are exactly 32 characters using base32 (a-p only)
  // Match exactly 32 consecutive lowercase letters a-p
  const match = trimmed.match(/[a-p]{32}/);
  return match ? match[0] : '';
}

/**
 * Validates if a string is a valid extension ID format (Chrome ID or UUID)
 * @param {string} id - Extension ID to validate
 * @returns {boolean} - True if valid format (Chrome extension ID or UUID)
 */
export function isValidExtensionId(id) {
  if (typeof id !== 'string') return false;
  return /^[a-p]{32}$/.test(id) || isUUID(id);
}

/**
 * Checks if the ID is a Chrome Web Store extension ID (not a UUID)
 * @param {string} id - ID to check
 * @returns {boolean} - True if Chrome extension ID format
 */
export function isChromeExtensionId(id) {
  return typeof id === 'string' && /^[a-p]{32}$/.test(id);
}


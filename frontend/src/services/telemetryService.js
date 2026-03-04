// Privacy-first analytics (no PII).
// Posts a single pageview event per route entry and fails silently if the API is down.
// Uses same API base as rest of app (VITE_API_URL) so production hits the backend, not static host.

let lastPathSent = null;
let lastSentAt = 0;

const MIN_INTERVAL_MS = 250;

function getApiBase() {
  const base = import.meta.env.VITE_API_URL || "";
  return base ? `${base.replace(/\/$/, "")}/api` : "/api";
}

export async function trackPageView(pathname) {
  try {
    const path = (pathname || "/").trim() || "/";

    const now = Date.now();
    if (lastPathSent === path && now - lastSentAt < MIN_INTERVAL_MS) return;

    lastPathSent = path;
    lastSentAt = now;

    await fetch(`${getApiBase()}/telemetry/pageview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
      keepalive: true,
    });
  } catch {
    // Fail silently (do not break UI)
  }
}

/**
 * Log a custom event (e.g. enterprise_custom_extension_cta_click).
 * No PII; fails silently.
 */
export async function trackEvent(eventName) {
  if (!eventName || typeof eventName !== "string") return;
  try {
    await fetch(`${getApiBase()}/telemetry/event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event: eventName.trim() }),
      keepalive: true,
    });
  } catch {
    // Fail silently
  }
}



import React, { useMemo, useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import realScanService from "../services/realScanService";
import SEOHead from "../components/SEOHead";
import { trackEvent } from "../services/telemetryService";
import "./EnterprisePage.scss";

const INTEREST_OPTIONS = [
  { value: "monitoring_rescan", label: "Monitoring + auto-rescan on updates" },
  { value: "policy_allow_block", label: "Policy allow/block + approvals" },
  { value: "audit_exports", label: "Audit exports / SIEM integrations" },
  { value: "custom_extension", label: "Custom extension build / hardening (pilot)" },
];

const EnterprisePage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const API_BASE_URL = import.meta.env.VITE_API_URL || "";

  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    notes: "",
    interests: [],
    custom_extension_notes: "",
  });

  const [submitState, setSubmitState] = useState("idle"); // idle | loading | success | error
  const [submitMessage, setSubmitMessage] = useState("");

  // Prefill interests when coming from landing CTA (?interest=custom-extension)
  useEffect(() => {
    const interest = searchParams.get("interest");
    if (interest === "custom-extension") {
      setForm((prev) => ({
        ...prev,
        interests: prev.interests.includes("custom_extension")
          ? prev.interests
          : [...prev.interests, "custom_extension"],
      }));
    }
  }, [searchParams]);

  const isValid = useMemo(() => {
    return Boolean(form.name.trim() && form.email.trim());
  }, [form.name, form.email]);

  const onChange = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const onInterestToggle = (value) => {
    setForm((prev) => {
      const next = prev.interests.includes(value)
        ? prev.interests.filter((i) => i !== value)
        : [...prev.interests, value];
      if (value === "custom_extension" && next.includes("custom_extension")) {
        trackEvent("enterprise_interest_custom_extension_checked");
      }
      return { ...prev, interests: next };
    });
  };

  const hasCustomExtensionInterest = form.interests.includes("custom_extension");

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!isValid || submitState === "loading") return;

    setSubmitState("loading");
    setSubmitMessage("");

    try {
      const payload = {
        name: form.name.trim(),
        email: form.email.trim(),
        company: form.company.trim() || null,
        notes: form.notes.trim() || null,
        interests: form.interests,
        custom_extension_notes: hasCustomExtensionInterest ? (form.custom_extension_notes.trim() || null) : null,
      };
      const res = await fetch(`${API_BASE_URL}/api/enterprise/pilot-request`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...realScanService.getUserHeaders() },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = data.detail;
        const message =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail) && detail[0]?.msg
              ? detail[0].msg
              : null;
        // 405 Method Not Allowed or other server/network errors: show friendly message
        if (res.status === 405 || res.status >= 500 || !message) {
          setSubmitState("error");
          setSubmitMessage("Something went wrong. Please try again.");
          return;
        }
        setSubmitState("error");
        setSubmitMessage(message || "Something went wrong. Please try again.");
        return;
      }

      setSubmitState("success");
      setSubmitMessage("Request received. We’ll reach out soon.");
      setForm({
        name: "",
        email: "",
        company: "",
        notes: "",
        interests: [],
        custom_extension_notes: "",
      });
    } catch (err) {
      setSubmitState("error");
      setSubmitMessage(err?.message || "Something went wrong. Please try again.");
    }
  };

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {
        "@type": "Question",
        "name": "What is enterprise extension management?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Enterprise extension management allows IT and security teams to monitor, govern, and enforce policies for browser extensions used across their organization. This includes risk scoring, compliance monitoring, and automated alerting."
        }
      },
      {
        "@type": "Question",
        "name": "How does extension governance work?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Extension governance enables organizations to create allow/block lists, enforce security policies, and generate audit-ready reports. Administrators can monitor extension usage and receive alerts when risk levels change."
        }
      },
      {
        "@type": "Question",
        "name": "What compliance features are available?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "ExtensionShield Enterprise provides policy packs for common compliance frameworks, audit-ready exports, and detailed reporting on extension security, privacy, and governance signals."
        }
      },
      {
        "@type": "Question",
        "name": "Can I monitor extensions automatically?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Yes! Enterprise plans include automatic monitoring and re-scanning when extensions are updated. You'll receive alerts when risk scores change or new security issues are detected."
        }
      }
    ]
  };

  return (
    <>
      <SEOHead
        title="Browser Extension Risk Assessment & Governance (Allowlist, Monitoring) | ExtensionShield"
        description="Extension governance: allowlist policies, monitoring, audit exports. Browser extension risk assessment for enterprise. Manage Chrome extensions at scale."
        pathname="/enterprise"
        ogType="website"
        schema={faqSchema}
      />
      <div className="enterprise-page">
      <div className="enterprise-container">
        <div className="enterprise-header">
          <button className="enterprise-back" onClick={() => navigate(-1)}>
            <span className="arrow">←</span> Back
          </button>

          <h1>Request an Enterprise Pilot</h1>
          <p>
            Monitoring, alerting, governance, and audit-ready exports for teams. No self-serve checkout — we’ll set up a pilot with you.
          </p>
        </div>

        <div className="enterprise-grid">
          <div className="enterprise-card">
            <h2>What you’ll get</h2>
            <ul className="enterprise-features">
              <li>Monitoring & auto-rescan on updates</li>
              <li>Alerting when risk changes</li>
              <li>Policy packs + audit exports</li>
              <li>Org allow/block list governance</li>
              <li>
                SSO/RBAC <span className="coming-soon-tag">Coming soon</span>
              </li>
            </ul>
            <div className="enterprise-card-divider" aria-hidden="true" />
            <div className="enterprise-pilot-addon">
              <h3 className="enterprise-pilot-addon__heading">Custom extensions, without the risk.</h3>
              <p className="enterprise-pilot-addon__text">
                We build or harden internal extensions with minimal permissions, signed builds, and change alerts so you stay in policy.
              </p>
            </div>
          </div>

          <form className="enterprise-form" onSubmit={onSubmit}>
            <h2>Tell us about your org</h2>

            <div className="form-grid">
              <div className="field">
                <label htmlFor="enterprise-name">Name</label>
                <input
                  id="enterprise-name"
                  value={form.name}
                  onChange={onChange("name")}
                  autoComplete="name"
                  aria-required="true"
                />
              </div>
              <div className="field">
                <label htmlFor="enterprise-email">Work email</label>
                <input
                  id="enterprise-email"
                  value={form.email}
                  onChange={onChange("email")}
                  autoComplete="email"
                  inputMode="email"
                  aria-required="true"
                />
              </div>
              <div className="field full">
                <label htmlFor="enterprise-company">Company (optional)</label>
                <input
                  id="enterprise-company"
                  value={form.company}
                  onChange={onChange("company")}
                  autoComplete="organization"
                />
              </div>
              <div className="field full enterprise-interests-field">
                <span className="field-label" id="enterprise-interests-label">What are you interested in?</span>
                <div className="enterprise-interests" role="group" aria-labelledby="enterprise-interests-label">
                  {INTEREST_OPTIONS.map((opt) => (
                    <label key={opt.value} className="enterprise-interest-checkbox">
                      <input
                        type="checkbox"
                        checked={form.interests.includes(opt.value)}
                        onChange={() => onInterestToggle(opt.value)}
                        aria-describedby={opt.value === "custom_extension" ? "enterprise-custom-notes-desc" : undefined}
                      />
                      <span>{opt.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              {hasCustomExtensionInterest && (
                <div className="field full" id="enterprise-custom-notes-desc">
                  <label htmlFor="enterprise-custom-extension-notes">Custom extension notes (optional)</label>
                  <textarea
                    id="enterprise-custom-extension-notes"
                    value={form.custom_extension_notes}
                    onChange={onChange("custom_extension_notes")}
                    placeholder="What should the extension do? Target sites, required permissions, users, and any compliance constraints."
                    rows={4}
                  />
                </div>
              )}
              <div className="field full">
                <label htmlFor="enterprise-notes">Notes (optional)</label>
                <textarea
                  id="enterprise-notes"
                  value={form.notes}
                  onChange={onChange("notes")}
                  rows={4}
                />
              </div>
            </div>

            {submitMessage && (
              <div className={`form-status ${submitState}`}>
                {submitMessage}
              </div>
            )}

            <button
              type="submit"
              className="enterprise-submit"
              disabled={!isValid || submitState === "loading"}
              title={!isValid ? "Please fill name and work email" : ""}
              aria-busy={submitState === "loading"}
            >
              {submitState === "loading" ? "Submitting..." : "Request Enterprise Pilot"}
            </button>

            <div className="form-note">
              We don’t collect payment here. This just starts a conversation.
            </div>
          </form>
        </div>
      </div>
      </div>
    </>
  );
};

export default EnterprisePage;



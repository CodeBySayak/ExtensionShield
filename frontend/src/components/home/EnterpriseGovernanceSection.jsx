import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ListChecks,
  AlertTriangle,
  RefreshCw,
  Database,
  Wrench,
} from "lucide-react";
import "./OpenCoreEnginesSection.scss";

const BULLETS = [
  { Icon: ListChecks, text: "Allow or block extensions — decide what can be installed" },
  { Icon: AlertTriangle, text: "Permission alerts — get notified when an extension asks for risky access" },
  { Icon: RefreshCw, text: "Update monitoring — see when extensions update and what permissions change" },
  { Icon: Database, text: "API and export — plug into SIEM, ticketing, and audit tools" },
];

/**
 * Enterprise governance section: "Extensions increase productivity — but only the right ones."
 * Two-column: left copy + bullets + CTAs, right policy flow (timeline-style like HowWeProtect).
 */
const EnterpriseGovernanceSection = ({ reducedMotion = false }) => {
  return (
    <section
      className="enterprise-governance-section landing-separator"
      aria-labelledby="enterprise-governance-heading"
    >
      <div className="enterprise-governance-inner">
        <div className="enterprise-governance-grid enterprise-governance-grid--copy-only">
          {/* Left: copy, bullets, CTAs */}
          <div className="enterprise-governance-copy">
            <motion.p
              className="enterprise-governance-eyebrow"
              initial={reducedMotion ? false : { opacity: 0, y: 8 }}
              whileInView={reducedMotion ? {} : { opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            >
              For security teams
            </motion.p>
            <motion.h2
              id="enterprise-governance-heading"
              className="enterprise-governance-title enterprise-governance-inner-headline"
              initial={reducedMotion ? false : { opacity: 0, y: 12 }}
              whileInView={reducedMotion ? {} : { opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.15 }}
              transition={{ duration: 0.4, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
            >
              Extensions boost productivity. Unmanaged ones create risk.
            </motion.h2>
            <motion.p
              className="enterprise-governance-subtext"
              initial={reducedMotion ? false : { opacity: 0, y: 8 }}
              whileInView={reducedMotion ? {} : { opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.35, delay: 0.1 }}
            >
              Enforce policy, flag risky permissions, and monitor updates before they become incidents.
            </motion.p>
            <ul className="enterprise-governance-bullets">
              {BULLETS.map((item, i) => (
                <motion.li
                  key={i}
                  className="enterprise-governance-bullet"
                  initial={reducedMotion ? false : { opacity: 0, x: -8 }}
                  whileInView={reducedMotion ? {} : { opacity: 1, x: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ duration: 0.35, delay: 0.08 + i * 0.04 }}
                >
                  <item.Icon className="enterprise-governance-bullet-icon" aria-hidden />
                  <span>{item.text}</span>
                </motion.li>
              ))}
              <motion.li
                className="enterprise-governance-bullet enterprise-governance-bullet--block"
                initial={reducedMotion ? false : { opacity: 0, x: -8 }}
                whileInView={reducedMotion ? {} : { opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.35, delay: 0.08 + BULLETS.length * 0.04 }}
              >
                <Wrench className="enterprise-governance-bullet-icon" aria-hidden />
                <div className="enterprise-governance-bullet__block">
                  <p className="enterprise-governance-bullet__block-title">Private builds and internal extensions — lower risk.</p>
                </div>
              </motion.li>
            </ul>
            <motion.div
              className="enterprise-governance-ctas"
              initial={reducedMotion ? false : { opacity: 0, y: 8 }}
              whileInView={reducedMotion ? {} : { opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.4, delay: 0.2 }}
            >
              <Link to="/enterprise#demo" className="enterprise-governance-btn enterprise-governance-btn--primary">
                Request a demo
              </Link>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default EnterpriseGovernanceSection;

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { CheckCircle, AlertCircle } from 'lucide-react';
import './LayerModal.scss';

const FACTOR_HUMAN = {
  SAST:                 { label: 'Code Safety',           category: 'code',   desc: 'Scans code for security problems' },
  VirusTotal:           { label: 'Malware Scan',          category: 'threat', desc: 'Antivirus detection results' },
  Obfuscation:          { label: 'Hidden Code',           category: 'code',   desc: 'Code readability analysis' },
  Manifest:             { label: 'Extension Config',      category: 'code',   desc: 'Configuration security check' },
  ChromeStats:          { label: 'Threat Intelligence',   category: 'threat', desc: 'Known security issues check' },
  Webstore:             { label: 'Store Reputation',      category: 'trust',  desc: 'Chrome store ratings & reviews' },
  Maintenance:          { label: 'Update Freshness',      category: 'trust',  desc: 'Last update recency' },
  PermissionsBaseline:  { label: 'Permission Risk',       category: 'access', desc: 'Browser access level' },
  PermissionCombos:     { label: 'Dangerous Combos',      category: 'access', desc: 'Risky permission combinations' },
  NetworkExfil:         { label: 'Data Sharing',          category: 'data',   desc: 'External data transmission' },
  CaptureSignals:       { label: 'Screen / Tab Capture',  category: 'data',   desc: 'Screen recording capability' },
  ToSViolations:        { label: 'Policy Violations',     category: 'policy', desc: 'Chrome store rule compliance' },
  Consistency:          { label: 'Behavior Match',        category: 'policy', desc: 'Claims vs. actual behavior' },
  DisclosureAlignment:  { label: 'Disclosure Accuracy',   category: 'policy', desc: 'Privacy policy accuracy' },
};

const CATEGORY_LABELS = {
  code:   'Code Checks',
  threat: 'Threat Detection',
  trust:  'Trust Signals',
  access: 'What It Can Access',
  data:   'Data Handling',
  policy: 'Rules & Policies',
};

const LAYER_CONFIG = {
  security: {
    title: 'Security',
    icon: '🛡️',
  },
  privacy: {
    title: 'Privacy',
    icon: '🔒',
  },
  governance: {
    title: 'Governance',
    icon: '📋',
  },
};

function humanizeFactor(factor) {
  const info = FACTOR_HUMAN[factor.name] || {
    label: factor.name,
    category: 'other',
    desc: '',
  };
  const severity = factor.severity ?? 0;
  let status, statusType;
  if (severity >= 0.4) {
    status = 'Issues Found';
    statusType = 'issues';
  } else {
    status = 'No Issues';
    statusType = 'clear';
  }
  return { ...info, status, statusType, severity, raw: factor };
}

function groupByCategory(items) {
  const groups = {};
  items.forEach(item => {
    const cat = item.category || 'other';
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(item);
  });
  Object.values(groups).forEach(g => g.sort((a, b) => b.severity - a.severity));
  return Object.entries(groups)
    .sort(([, a], [, b]) => Math.max(...b.map(x => x.severity)) - Math.max(...a.map(x => x.severity)));
}

function bandColor(band) {
  switch (band) {
    case 'GOOD': return 'var(--risk-good)';
    case 'WARN': return 'var(--risk-warn)';
    case 'BAD':  return 'var(--risk-bad)';
    default:     return 'var(--risk-neutral)';
  }
}

function bandLabel(band) {
  switch (band) {
    case 'GOOD': return 'Safe';
    case 'WARN': return 'Needs Review';
    case 'BAD':  return 'Not Safe';
    default:     return '';
  }
}

const LayerModal = ({
  open,
  onClose,
  layer,
  score = null,
  band = 'NA',
  factors = [],
  // eslint-disable-next-line no-unused-vars
  keyFindings = [],
  // eslint-disable-next-line no-unused-vars
  gateResults = [],
  // eslint-disable-next-line no-unused-vars
  layerReasons = [],
  layerDetails = null,
  // eslint-disable-next-line no-unused-vars
  onViewEvidence = null,
}) => {
  const config = LAYER_CONFIG[layer] || LAYER_CONFIG.security;
  const displayScore = score === null ? '--' : Math.round(score);
  const bc = bandColor(band);
  const bl = bandLabel(band);

  const ld = layerDetails?.[layer] || {};
  const oneLiner = ld.one_liner || '';

  const humanised = factors.map(humanizeFactor);
  const grouped = groupByCategory(humanised);

  const issueCount = humanised.filter(f => f.statusType === 'issues').length;
  const totalCount = humanised.length;

  const renderStatusIcon = (statusType) =>
    statusType === 'clear' ? (
      <CheckCircle className="lm-status-icon" size={16} strokeWidth={2} aria-hidden />
    ) : (
      <AlertCircle className="lm-status-icon" size={16} strokeWidth={2} aria-hidden />
    );

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="lm-content lm-dialog-smooth" aria-describedby="lm-summary-or-checks">
        <DialogHeader>
          <DialogTitle className="lm-header">
            <div className="lm-header-left">
              <span className="lm-icon" aria-hidden>{config.icon}</span>
              <span className="lm-title">{config.title}</span>
            </div>
            <div className="lm-header-right">
              <span className="lm-score-num" style={{ color: bc }}>{displayScore}</span>
              {bl && (
                <span className={`lm-verdict-pill lm-verdict-${band.toLowerCase()}`}>
                  {bl}
                </span>
              )}
            </div>
          </DialogTitle>
        </DialogHeader>

        <div className="lm-body" id="lm-summary-or-checks">
          <div className="lm-body-left">
            {oneLiner && (
              <p className="lm-summary">{oneLiner}</p>
            )}
            <div className="lm-stats-row" aria-live="polite">
              <span className="lm-stat">
                <span className="lm-stat-num">{totalCount}</span> checks run
              </span>
              {issueCount > 0 ? (
                <span className="lm-stat lm-stat-issues">
                  <span className="lm-stat-num">{issueCount}</span> with issues
                </span>
              ) : (
                <span className="lm-stat lm-stat-clear">All clear</span>
              )}
            </div>
          </div>

          {grouped.length > 0 && (
            <div className="lm-body-right">
              <div className="lm-checks" role="list" aria-label={`${config.title} checks`}>
                {grouped.map(([cat, items], catIdx) => (
                  <div key={cat} className="lm-group" style={{ animationDelay: `${catIdx * 40}ms` }} role="group" aria-label={CATEGORY_LABELS[cat] || cat}>
                    <span className="lm-group-label">{CATEGORY_LABELS[cat] || cat}</span>
                    <div className="lm-group-items">
                      {items.map((item, idx) => (
                        <div
                          key={idx}
                          className={`lm-check-card lm-check-${item.statusType}`}
                          style={{ animationDelay: `${(catIdx * 40 + (idx + 1) * 25)}ms` }}
                          role="listitem"
                          title={item.desc}
                        >
                          <span className="lm-check-name">{item.label}</span>
                          <span className="lm-status-wrap">
                            {renderStatusIcon(item.statusType)}
                            <span className={`lm-status lm-status-${item.statusType}`}>
                              {item.status}
                            </span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default LayerModal;

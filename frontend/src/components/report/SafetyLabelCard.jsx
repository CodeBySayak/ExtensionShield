import React from 'react';
import './SafetyLabelCard.scss';

/**
 * SafetyLabelCard - Compact list of safety label rows
 *
 * Props:
 * - rows: ConsumerSafetyLabelRow[]
 * - onEvidenceClick: (evidenceId: string) => void
 */
const SafetyLabelCard = ({ rows = [], onEvidenceClick }) => {
  const safeRows = Array.isArray(rows) ? rows : [];
  const handleEvidenceClick = (evidenceId) => {
    if (typeof onEvidenceClick === 'function') {
      onEvidenceClick(evidenceId);
    } else {
      // console.log('evidence:', evidenceId); // prod: no console
    }
  };

  if (safeRows.length === 0) {
    return (
      <div className="safety-label-card empty">
        No safety labels available.
      </div>
    );
  }

  return (
    <div className="safety-label-card">
      {safeRows.slice(0, 8).map((row, idx) => {
        const evidenceIds = Array.isArray(row?.evidence_ids)
          ? row.evidence_ids.slice(0, 2)
          : [];
        const severity = String(row?.severity || 'LOW').toLowerCase();
        const value = String(row?.value || 'UNKNOWN').toLowerCase();

        return (
          <div
            key={`${row?.id || 'row'}-${idx}`}
            className={`safety-label-row severity-${severity}`}
          >
            <div className="label-title">
              <span>{row?.title || row?.id || 'Label'}</span>
              {row?.why && (
                <span className="label-why" title={row.why} aria-label={row.why}>
                  ?
                </span>
              )}
            </div>
            <div className="label-right">
              <span className={`value-badge value-${value}`}>
                {row?.value || 'UNKNOWN'}
              </span>
              {evidenceIds.length > 0 && (
                <div className="label-evidence">
                  {evidenceIds.map((eid) => (
                    <button
                      type="button"
                      key={eid}
                      className="evidence-chip"
                      onClick={() => handleEvidenceClick(eid)}
                      title={`Evidence: ${eid}`}
                    >
                      {eid}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default SafetyLabelCard;


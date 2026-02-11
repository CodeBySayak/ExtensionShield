import React from 'react';
import './TopDriversRow.scss';

/**
 * TopDriversRow - Compact chips for top scoring drivers
 *
 * Props:
 * - drivers: ConsumerTopDriver[]
 * - onEvidenceClick: (evidenceId: string) => void
 */
const TopDriversRow = ({ drivers = [], onEvidenceClick }) => {
  const safeDrivers = Array.isArray(drivers) ? drivers : [];
  const handleEvidenceClick = (evidenceId) => {
    if (typeof onEvidenceClick === 'function') {
      onEvidenceClick(evidenceId);
    } else {
      // console.log('evidence:', evidenceId); // prod: no console
    }
  };

  if (safeDrivers.length === 0) {
    return (
      <div className="top-drivers-row empty">
        No top drivers available.
      </div>
    );
  }

  return (
    <div className="top-drivers-row">
      {safeDrivers.slice(0, 5).map((driver, idx) => {
        const contribution = Number.isFinite(driver?.contribution)
          ? Math.round(driver.contribution * 100)
          : 0;
        const evidenceIds = Array.isArray(driver?.evidence_ids)
          ? driver.evidence_ids.slice(0, 2)
          : [];

        return (
          <div className="driver-chip" key={`${driver?.name || 'driver'}-${idx}`}>
            <div className="driver-main">
              <span className="driver-name">{driver?.name || 'Unknown'}</span>
              <span className="driver-layer">{driver?.layer || 'unknown'}</span>
            </div>
            <div className="driver-meta">
              <span className="driver-contribution">{contribution}%</span>
              {evidenceIds.length > 0 && (
                <div className="driver-evidence">
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

export default TopDriversRow;


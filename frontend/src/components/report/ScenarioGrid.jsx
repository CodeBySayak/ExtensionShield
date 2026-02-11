import React from 'react';
import './ScenarioGrid.scss';

/**
 * ScenarioGrid - Grid of scenario cards
 *
 * Props:
 * - scenarios: ConsumerScenario[]
 * - onEvidenceClick: (evidenceId: string) => void
 */
const ScenarioGrid = ({ scenarios = [], onEvidenceClick }) => {
  const safeScenarios = Array.isArray(scenarios) ? scenarios : [];
  const handleEvidenceClick = (evidenceId) => {
    if (typeof onEvidenceClick === 'function') {
      onEvidenceClick(evidenceId);
    } else {
      // console.log('evidence:', evidenceId); // prod: no console
    }
  };

  if (safeScenarios.length === 0) {
    return (
      <div className="scenario-empty">
        No high-risk scenarios detected for this extension.
      </div>
    );
  }

  return (
    <div className="scenario-grid">
      {safeScenarios.map((scenario, idx) => {
        const severity = String(scenario?.severity || 'LOW').toLowerCase();
        const mitigations = Array.isArray(scenario?.mitigations)
          ? scenario.mitigations.slice(0, 2)
          : [];
        const evidenceIds = Array.isArray(scenario?.evidence_ids)
          ? scenario.evidence_ids.slice(0, 2)
          : [];

        return (
          <div
            key={`${scenario?.id || 'scenario'}-${idx}`}
            className={`scenario-card severity-${severity}`}
          >
            <div className="scenario-header">
              <div className="scenario-title">{scenario?.title || 'Scenario'}</div>
              <span className={`scenario-badge severity-${severity}`}>
                {scenario?.severity || 'LOW'}
              </span>
            </div>

            <div className="scenario-summary">
              {scenario?.summary || 'No summary available.'}
            </div>

            {scenario?.why && (
              <div className="scenario-why">
                {scenario.why}
              </div>
            )}

            {mitigations.length > 0 && (
              <ul className="scenario-mitigations">
                {mitigations.map((m, mIdx) => (
                  <li key={mIdx}>{m}</li>
                ))}
              </ul>
            )}

            {evidenceIds.length > 0 && (
              <div className="scenario-evidence">
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
        );
      })}
    </div>
  );
};

export default ScenarioGrid;


import React from "react";

const SourcesBox = ({ sources }) => {
  return (
    <div style={{
      background: 'rgba(13, 20, 36, 0.6)',
      border: '1px solid rgba(148, 163, 184, 0.1)',
      borderRadius: '12px',
      padding: '1.5rem',
      marginTop: '2rem'
    }}>
      <h4 style={{
        fontSize: '0.875rem',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        color: '#a78bfa',
        marginBottom: '1rem'
      }}>
        Data Sources
      </h4>
      <div style={{ display: 'grid', gap: '1rem' }}>
        {sources.map((source, index) => (
          <div key={index}>
            <a 
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: '#22c55e',
                textDecoration: 'none',
                fontWeight: 600,
                fontSize: '0.875rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem'
              }}
            >
              {source.name}
              <svg 
                width="14" 
                height="14" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2"
              >
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
            </a>
            <p style={{
              margin: '0.25rem 0 0 0',
              fontSize: '0.8125rem',
              color: '#94a3b8',
              lineHeight: 1.5
            }}>
              {source.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SourcesBox;


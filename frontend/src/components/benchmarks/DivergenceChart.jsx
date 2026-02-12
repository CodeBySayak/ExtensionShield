import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const DivergenceChart = ({ data }) => {
  const formattedData = data.map(item => ({
    category: item.extension_category,
    'ExtensionShield vs A': item.extensionshield_vs_a,
    'ExtensionShield vs B': item.extensionshield_vs_b,
    'A vs B': item.a_vs_b
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'rgba(13, 20, 36, 0.95)',
          border: '1px solid rgba(34, 197, 94, 0.3)',
          borderRadius: '8px',
          padding: '12px',
          color: '#f8fafc'
        }}>
          <p style={{ margin: 0, fontWeight: 600, marginBottom: '8px' }}>{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ margin: '4px 0', color: entry.color, fontSize: '0.875rem' }}>
              {entry.name}: {entry.value}% disagreement
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 400 }}>
      <h4 style={{ 
        fontSize: '0.9375rem', 
        fontWeight: 600, 
        marginBottom: '1rem',
        color: '#f8fafc'
      }}>
        Scanner Disagreement by Category
      </h4>
      <p style={{
        fontSize: '0.8125rem',
        color: '#94a3b8',
        marginBottom: '1rem',
        lineHeight: 1.5
      }}>
        Higher disagreement indicates ExtensionShield detects risks others miss (typically governance/privacy factors)
      </p>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart 
          data={formattedData} 
          margin={{ top: 5, right: 30, left: 20, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
          <XAxis 
            dataKey="category" 
            stroke="#64748b"
            angle={-45}
            textAnchor="end"
            height={80}
            style={{ fontSize: '0.75rem' }}
          />
          <YAxis 
            stroke="#64748b"
            style={{ fontSize: '0.75rem' }}
            label={{ value: 'Disagreement %', angle: -90, position: 'insideLeft', style: { fill: '#64748b' } }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ paddingTop: '20px', fontSize: '0.875rem' }}
            iconType="square"
          />
          <Bar dataKey="ExtensionShield vs A" fill="#22c55e" />
          <Bar dataKey="ExtensionShield vs B" fill="#8b5cf6" />
          <Bar dataKey="A vs B" fill="#64748b" opacity={0.5} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DivergenceChart;


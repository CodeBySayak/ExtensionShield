import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const PerformanceChart = ({ data }) => {
  const scanTimeData = [
    { scanner: 'ExtensionShield', value: data.extensionshield.median_scan_time_seconds },
    { scanner: 'Competitor A', value: data.competitor_a.median_scan_time_seconds },
    { scanner: 'Competitor B', value: data.competitor_b.median_scan_time_seconds }
  ];

  const cacheData = [
    { scanner: 'ExtensionShield', value: data.extensionshield.cache_hit_rate_percent },
    { scanner: 'Competitor A', value: data.competitor_a.cache_hit_rate_percent },
    { scanner: 'Competitor B', value: data.competitor_b.cache_hit_rate_percent }
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'rgba(13, 20, 36, 0.95)',
          border: '1px solid rgba(34, 197, 94, 0.3)',
          borderRadius: '8px',
          padding: '12px',
          color: '#f8fafc'
        }}>
          <p style={{ margin: 0, fontWeight: 600 }}>{payload[0].payload.scanner}</p>
          <p style={{ margin: '4px 0 0 0', color: '#22c55e', fontSize: '0.875rem' }}>
            {payload[0].value}{payload[0].name.includes('Time') ? 's' : '%'}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h4 style={{ 
          fontSize: '0.9375rem', 
          fontWeight: 600, 
          marginBottom: '1rem',
          color: '#f8fafc'
        }}>
          Median Scan Time (seconds)
        </h4>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={scanTimeData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
            <XAxis 
              dataKey="scanner" 
              stroke="#64748b"
              style={{ fontSize: '0.75rem' }}
            />
            <YAxis 
              stroke="#64748b"
              style={{ fontSize: '0.75rem' }}
              label={{ value: 'Seconds', angle: -90, position: 'insideLeft', style: { fill: '#64748b' } }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" fill="#22c55e" name="Scan Time" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h4 style={{ 
          fontSize: '0.9375rem', 
          fontWeight: 600, 
          marginBottom: '1rem',
          color: '#f8fafc'
        }}>
          Cache Hit Rate (%)
        </h4>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={cacheData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
            <XAxis 
              dataKey="scanner" 
              stroke="#64748b"
              style={{ fontSize: '0.75rem' }}
            />
            <YAxis 
              stroke="#64748b"
              style={{ fontSize: '0.75rem' }}
              domain={[0, 100]}
              label={{ value: 'Percent', angle: -90, position: 'insideLeft', style: { fill: '#64748b' } }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" fill="#8b5cf6" name="Cache Hit Rate" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PerformanceChart;


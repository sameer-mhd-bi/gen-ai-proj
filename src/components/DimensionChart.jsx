import React from 'react';
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const value = payload.find((p) => p.dataKey === 'value');
    return (
      <div
        style={{
          background: '#1e1e2e',
          border: '1px solid #444',
          borderRadius: 6,
          padding: '10px 14px',
          fontSize: 13,
          color: '#cdd6f4',
        }}
      >
        <p style={{ margin: 0, fontWeight: 600, marginBottom: 4 }}>
          Dimension {label}
        </p>
        {value && (
          <p style={{ margin: 0, color: '#89b4fa' }}>
            Value: {value.value?.toFixed ? value.value.toFixed(6) : value.value}
          </p>
        )}
      </div>
    );
  }
  return null;
};

const DimensionChart = ({ data = [], loading = false }) => {
  const chartData = data.map((item) => ({
    dimension_index: item.dimension_index,
    value: item.value,
  }));

  return (
    <div style={{ width: '100%' }}>
      <h2
        style={{
          fontSize: '1.2rem',
          fontWeight: 700,
          marginBottom: '1rem',
          color: '#686b78',
          letterSpacing: '0.02em',
        }}
      >
        Query Vector Dimensions
      </h2>

      {loading ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: 320,
            color: '#6c7086',
            fontSize: 14,
          }}
        >
          Loading dimension data…
        </div>
      ) : !chartData.length ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: 320,
            color: '#6c7086',
            fontSize: 14,
          }}
        >
          No dimension data available.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="1 3" stroke="#313244" />
            <XAxis
              dataKey="dimension_index"
              label={{
                value: 'Dimension Index',
                position: 'insideBottom',
                offset: -4,
                fill: '#6c7086',
                fontSize: 12,
              }}
              tick={{ fill: '#6c7086', fontSize: 11 }}
            />
            <YAxis
              label={{
                value: 'Vector Value',
                angle: -90,
                position: 'insideLeft',
                fill: '#6c7086',
                fontSize: 12,
              }}
              tick={{ fill: '#6c7086', fontSize: 11 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 12, color: '#cdd6f4', paddingTop: 8 }}
            />
            <Bar
              dataKey="value"
              name="Value"
              fill="#20a82b"
              radius={[3, 3, 0, 0]}
              maxBarSize={20}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default DimensionChart;

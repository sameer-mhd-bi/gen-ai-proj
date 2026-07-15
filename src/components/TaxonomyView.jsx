import React, { useState, useEffect, useMemo } from 'react';
import { FaSearch, FaTimes } from 'react-icons/fa';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import Plot from 'react-plotly.js';

const getSunburstData = (tree) => {
  if (!tree) return { ids: [], labels: [], parents: [], values: [], colors: [] };

  const ids = ["Insurance"];
  const labels = ["Insurance Root"];
  const parents = [""];
  const values = [0];
  const colors = ["#ffffff"];

  const traverse = (node, parentId, l1Name) => {
    if (Array.isArray(node)) {
      let sum = 0;
      node.forEach(leaf => {
        const id = `${parentId}-${leaf}`;
        ids.push(id);
        labels.push(leaf);
        parents.push(parentId);
        values.push(1);
        colors.push(l1Name === "Property Insurance" ? "#1f77b4" : "#ff7f0e");
        sum += 1;
      });
      return sum;
    } else {
      let sum = 0;
      const childData = [];
      for (const [key, child] of Object.entries(node)) {
        const currentL1 = parentId === "Insurance" ? key : l1Name;
        const id = `${parentId}-${key}`;
        childData.push({ key, child, id, currentL1 });
      }

      const indices = [];
      for (const { key, id, currentL1 } of childData) {
        ids.push(id);
        labels.push(key);
        parents.push(parentId);
        indices.push(values.length);
        values.push(0);
        colors.push(currentL1 === "Property Insurance" ? "#1f77b4" : "#ff7f0e");
      }

      for (let i = 0; i < childData.length; i++) {
        const { child, id, currentL1 } = childData[i];
        const childSum = traverse(child, id, currentL1);
        values[indices[i]] = childSum;
        sum += childSum;
      }
      return sum;
    }
  };

  values[0] = traverse(tree, "Insurance", null);
  return { ids, labels, parents, values, colors };
};

const TaxonomyView = () => {
  const [taxonomyTree, setTaxonomyTree] = useState(null);
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [isClassifying, setIsClassifying] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('http://localhost:5000/api/taxonomy-tree')
      .then(res => res.json())
      .then(data => setTaxonomyTree(data))
      .catch(err => console.error("Failed to load taxonomy tree", err));
  }, []);

  const sunburstData = useMemo(() => getSunburstData(taxonomyTree), [taxonomyTree]);

  const handleClassify = async () => {
    if (!query.trim()) return;

    setIsClassifying(true);
    setError('');
    setResult(null);
    setSubmittedQuery(query.trim());

    try {
      const response = await fetch('http://localhost:5000/api/taxonomy-classify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Classification failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsClassifying(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleClassify();
    }
  };

  const clearQuery = () => {
    setQuery('');
    setSubmittedQuery('');
    setResult(null);
    setError('');
  };

  return (
    <div className="taxonomy-container">
      <div className="search-result-panel-top">
        <div className="search-result-panel-header">Taxonomy Classification</div>
        <div className="search-input-panel" style={{ marginTop: '20px', position: 'relative' }}>
          <div className="search-input-wrapper" style={{ display: 'flex', alignItems: 'center', width: '100%', position: 'relative' }}>
            <FaSearch className="search-input-icon" aria-hidden="true" style={{ position: 'absolute', left: '15px' }} />
            <input
              type="text"
              className="search-input-field"
              placeholder="Enter claim description to classify..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              style={{ width: '100%', padding: '12px 100px 12px 45px', border: '1px solid #ccc', borderRadius: '4px' }}
            />
            {query && (
              <button
                className="search-clear-btn"
                onClick={clearQuery}
                aria-label="Clear text"
                tabIndex={0}
                style={{ position: 'absolute', right: '110px', background: 'none', border: 'none', cursor: 'pointer' }}
              >
                <FaTimes />
              </button>
            )}
            <button className="search-submit-btn" onClick={handleClassify} disabled={isClassifying} style={{ position: 'absolute', right: '5px' }}>
              {isClassifying ? 'Classifying...' : 'Classify'}
            </button>
          </div>

          {submittedQuery && !isClassifying && (
            <div style={{ marginTop: '15px', padding: '12px 16px', backgroundColor: '#f8f9fa', borderLeft: '4px solid #3b82f6', borderRadius: '4px', fontSize: '14px', color: '#333' }}>
              <strong>Analyzed Text: </strong> "{submittedQuery}"
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="error-message" style={{ color: '#d32f2f', borderLeft: '4px solid #d32f2f', paddingLeft: '12px', marginBottom: '20px' }}>
          {error}
        </div>
      )}

      {isClassifying && (
        <div style={{ textAlign: 'center', margin: '20px' }}>
          <p style={{ fontSize: '13px', color: '#666' }}>Processing text through the zero-shot classifier... This may take a few seconds.</p>
          <div className="tab-loading-spinner" style={{ margin: '0 auto' }}></div>
        </div>
      )}

      {result && (
        <div className="classification-result" style={{ background: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <div className="search-chart-container" style={{ marginTop: '20px', marginBottom: '30px' }}>
            <div className="search-chart-header">Interactive 5-Level Insurance Taxonomy Explorer</div>
            <p style={{ fontSize: '13px', color: '#666', marginBottom: '10px' }}>
              Explore the entire taxonomy space visually.
            </p>
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <Plot
                data={[
                  {
                    type: "sunburst",
                    ids: sunburstData.ids,
                    labels: sunburstData.labels,
                    parents: sunburstData.parents,
                    values: sunburstData.values,
                    marker: { colors: sunburstData.colors },
                    branchvalues: 'total',
                    insidetextorientation: 'radial'
                  }
                ]}
                layout={{
                  margin: { l: 0, r: 0, b: 0, t: 0 },
                  width: 600,
                  height: 600
                }}
                config={{ responsive: true, displayModeBar: false }}
              />
            </div>
          </div>


          <div className="search-chart-container" style={{ marginTop: '30px' }}>
            <div className="search-chart-header">Visual Taxonomy Path</div>
            <p style={{ fontSize: '13px', color: '#666', marginBottom: '20px' }}>
              Overall Path Integrity: {result.overall_score.toFixed(1)}%
            </p>
            <div style={{ height: '400px', width: '100%', marginTop: '20px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={[
                    { name: 'Insurance Root', score: 100 },
                    ...(result.plot_labels || []).map((label, idx) => ({
                      name: label.replace('\n', ' '),
                      score: (result.plot_scores[idx] * 100)
                    }))
                  ]}
                  margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#555', fontSize: 12 }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fill: '#555' }}
                    label={{ value: 'Confidence Score (%)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fill: '#666' } }}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                    formatter={(value) => [`${value.toFixed(1)}%`, 'Confidence']}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#bdc3c7"
                    strokeWidth={2}
                    dot={(props) => {
                      const { cx, cy, payload } = props;
                      let fill = '#c0392b';
                      if (payload.score === 100) fill = '#2c3e50';
                      else if (payload.score >= 70) fill = '#27ae60';
                      else if (payload.score >= 40) fill = '#f39c12';
                      return (
                        <circle cx={cx} cy={cy} r={10} fill={fill} stroke="#fff" strokeWidth={2} />
                      );
                    }}
                    activeDot={{ r: 12, stroke: '#fff', strokeWidth: 2 }}
                    animationDuration={1500}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  )
};

export default TaxonomyView;

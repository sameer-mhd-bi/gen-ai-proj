import React, { useState, useRef, useEffect } from 'react';
import { FaBell, FaFileAlt, FaBrain, FaFolder, FaSitemap, FaChartBar, FaRobot, FaComments, FaCheckCircle, FaSearch } from 'react-icons/fa';
import ForceGraph2D from 'react-force-graph-2d';

const loadingSteps = [
  { text: "Analyzing the policy data...", icon: FaFileAlt, color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-100" },
  { text: "Extracting claim data...", icon: FaBrain, color: "text-purple-600", bg: "bg-purple-50", border: "border-purple-100" },
  { text: "Deriving Taxonomy classification...", icon: FaFolder, color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100" },
  { text: "Building knowledge graph ontology...", icon: FaSitemap, color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-100" },
  { text: "Finding semantic similarity matches...", icon: FaSearch, color: "text-indigo-600", bg: "bg-indigo-50", border: "border-indigo-100" },
  { text: "Running risk & fraud analytics...", icon: FaChartBar, color: "text-rose-600", bg: "bg-rose-50", border: "border-rose-100" },
  { text: "Evaluating coverage reasoning rules...", icon: FaCheckCircle, color: "text-teal-600", bg: "bg-teal-50", border: "border-teal-100" },
  { text: "Formulating AI recommendation...", icon: FaRobot, color: "text-slate-600", bg: "bg-slate-50", border: "border-slate-100" }
];

export default function InsuranceClaimsCopilot() {
  const [claimText, setClaimText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [selectedSimilarClaim, setSelectedSimilarClaim] = useState(null);
  const [loadingStepIndex, setLoadingStepIndex] = useState(0);

  useEffect(() => {
    let interval;
    if (loading) {
      setLoadingStepIndex(0);
      interval = setInterval(() => {
        setLoadingStepIndex((prev) => (prev + 1) % loadingSteps.length);
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const graphWrapperRef = useRef(null);
  const graphRef = useRef(null);
  const [graphWidth, setGraphWidth] = useState(600);

  useEffect(() => {
    if (!graphWrapperRef.current) return;
    const observer = new ResizeObserver((entries) => {
      setGraphWidth(entries[0].contentRect.width);
    });
    observer.observe(graphWrapperRef.current);
    return () => observer.disconnect();
  }, [data]);

  useEffect(() => {
    if (graphRef.current) {
      const graph = graphRef.current;
      graph.d3Force('charge').strength(-400);
      graph.d3Force('link').distance(80);
    }
  }, [data]);

  const analyzeClaim = async () => {
    if (!claimText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:5000/api/workflow/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: claimText }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Failed to analyze claim');
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getGraphData = () => {
    if (!data || !data.knowledge_graph) return { nodes: [], links: [] };

    const nodes = [
      { id: 'Claim', label: data.extraction.claim_id || 'Claim', type: 'subject' },
      { id: 'Customer', label: data.knowledge_graph.nodes[0] || 'Customer', type: 'object' },
      { id: 'Coverage', label: data.knowledge_graph.nodes[2] || 'Coverage', type: 'object' },
      { id: 'Structure', label: data.knowledge_graph.nodes[3] || 'Structure', type: 'object' },
      { id: 'Peril', label: data.knowledge_graph.nodes[4] || 'Peril', type: 'object' }
    ];

    const links = [
      { source: 'Claim', target: 'Customer', label: 'customer' },
      { source: 'Claim', target: 'Structure', label: 'damaged' },
      { source: 'Claim', target: 'Peril', label: 'caused by' }
    ];

    if (data.customer_policies && data.customer_policies.length > 0) {
      data.customer_policies.forEach((policy) => {
        const policyId = `Policy_${policy.policy_number}`;
        
        // Add policy node
        nodes.push({ 
          id: policyId, 
          label: `${policy.policy_number} (${policy.policy_type})`, 
          type: 'policy_node' 
        });

        // Link Customer -> Policy
        links.push({ source: 'Customer', target: policyId, label: 'owns policy' });

        // If this is the policy used in the claim, link Claim -> Policy and Policy -> Coverage
        if (policy.policy_number === data.extraction.policy) {
          links.push({ source: 'Claim', target: policyId, label: 'policy' });
          links.push({ source: policyId, target: 'Coverage', label: 'includes' });
        }
      });
    } else {
      // Fallback to single policy if no policy list is returned
      nodes.push({ id: 'Policy', label: data.knowledge_graph.nodes[1] || 'Policy', type: 'policy_node' });
      links.push({ source: 'Claim', target: 'Policy', label: 'policy' });
      links.push({ source: 'Policy', target: 'Coverage', label: 'includes' });
    }

    return { nodes, links };
  };

  return (
    <div className='min-h-screen bg-slate-100 p-6 text-left'>
      <div className='max-w-[95%] mx-auto space-y-4'>

        <div className='bg-white shadow-sm px-8 py-5 rounded-2xl mb-4'>
          <div className='flex flex-col lg:flex-row lg:items-center justify-between gap-6'>
            <div className='flex items-center gap-5'>
              <div className='w-14 h-14 bg-blue-50 text-blue-600 rounded flex items-center justify-center text-3xl shadow-inner border border-blue-100 flex-shrink-0'>
                <FaFileAlt />
              </div>
              <div className='flex flex-col justify-center'>
                <h1 className='text-2xl text-slate-700 tracking-tight leading-none mb-1.5'>
                  Insurance Claims Copilot
                </h1>
                <span className='text-xs text-slate-500 font-medium'>Intelligent FNOL Processing Engine</span>
              </div>
            </div>
            
            <div className='flex flex-wrap items-center gap-8'>
              <div className='flex flex-col justify-center'>
                <span className='text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1.5'>Engine Capabilities</span>
                <div className='flex items-center gap-4 text-xs font-semibold text-slate-700'>
                  <span className='flex items-center gap-1.5'><FaBrain className="text-purple-500" /> Semantic Search</span>
                  <span className='flex items-center gap-1.5'><FaFolder className="text-emerald-500" /> Taxonomy</span>
                  <span className='flex items-center gap-1.5'><FaSitemap className="text-amber-500" /> Ontology</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className='bg-white rounded-3xl shadow p-5'>
          <h3 className='font-semibold text-sm mb-3'>Input Claim Description</h3>
          <textarea
            className='w-full border border-slate-200 rounded-xl p-3 text-xs mb-3 min-h-[100px] outline-none focus:border-blue-400'
            placeholder='Enter claim description here (e.g. High winds caused an old oak tree to snap and fall onto my detached workshop...)'
            value={claimText}
            onChange={(e) => setClaimText(e.target.value)}
          />
          <div className='flex gap-3 items-center'>
            <button
              onClick={analyzeClaim}
              disabled={loading || !claimText}
              className='bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-xl text-xs font-medium transition-colors'
            >
              {loading ? 'Analyzing with AI...' : 'Analyze Claim'}
            </button>
            {error && !error.includes("not found") && <span className='text-red-500 text-xs'>{error}</span>}
          </div>
        </div>

        {data && (
          <>
            <div className='bg-blue-50 border border-blue-200 rounded-3xl p-5'>
              <div className='flex justify-between items-center'>
                <div>
                  <h2 className='text-base font-semibold mb-1 flex items-center gap-2'><FaBell className="text-red-500" /> New Claim Analyzed</h2>
                  <p className='text-[11px] text-slate-600'>Source: {data.extraction.source} • Evaluated Just Now</p>
                </div>
                <span className='bg-green-100 text-green-800 px-3 py-1 rounded-full text-[11px] font-medium'>Analysis Complete</span>
              </div>
            </div>

            <div className='grid lg:grid-cols-10 gap-4'>

              <div className='bg-white rounded-3xl shadow p-5 lg:col-span-3'>
                <h3 className='font-semibold text-sm mb-3 flex items-center gap-2'><FaFileAlt className="text-blue-500" /> Incoming Claim</h3>
                <div className='space-y-2 text-[11px]'>
                  <div><b>Claim ID:</b> {data.extraction.claim_id}</div>
                  <div><b>Policy:</b> {data.extraction.policy}</div>
                  <div><b>Customer:</b> {data.extraction.customer}</div>
                  <div><b>Source:</b> {data.extraction.source}</div>
                </div>

                <div
                  className='mt-4 p-3 bg-slate-50 rounded-xl text-[11px] leading-relaxed'
                  dangerouslySetInnerHTML={{ __html: data.extraction.highlighted_text }}
                />
              </div>

              <div className='bg-white rounded-3xl shadow p-5 lg:col-span-3'>
                <h3 className='font-semibold text-sm mb-3 flex items-center gap-2'><FaBrain className="text-purple-500" /> AI Extracted Information</h3>
                <div className='space-y-3 text-[11px]'>
                  <div>Peril: <b>{data.extraction.peril}</b></div>
                  <div>Damage Type: <b>{data.extraction.damage_type}</b></div>
                  <div>Structure: <b>{data.extraction.structure}</b></div>
                  <div>Estimated Loss: <b>{data.extraction.estimated_loss}</b></div>
                </div>

                <div className='mt-4 flex flex-wrap gap-2 text-[10px] font-medium'>
                  <span className='bg-blue-100 px-3 py-1 rounded-full'>{data.extraction.peril}</span>
                  <span className='bg-green-100 px-3 py-1 rounded-full'>{data.extraction.damage_type}</span>
                  <span className='bg-purple-100 px-3 py-1 rounded-full'>Coverage Reviewed</span>
                </div>
              </div>

              <div className='bg-white rounded-3xl shadow p-5 lg:col-span-4'>
                <h3 className='font-semibold text-sm mb-3 flex items-center gap-2'><FaFolder className="text-amber-500" /> Taxonomy</h3>
                <div
                  className='text-[11px] leading-8 font-mono text-slate-700 bg-slate-50 p-4 rounded-xl overflow-x-auto'
                  dangerouslySetInnerHTML={{ __html: data.taxonomy_path }}
                />
              </div>
            </div>

            <div className='bg-white rounded-3xl shadow p-5'>
              <h3 className='font-semibold text-sm mb-4 flex items-center gap-2'><FaSitemap className="text-green-600" /> Knowledge Graph & Coverage Reasoning</h3>

              <div ref={graphWrapperRef} className='w-full h-[250px] border border-slate-200 rounded-xl overflow-hidden bg-slate-50 relative'>
                {data && data.knowledge_graph && (
                  <ForceGraph2D
                    ref={graphRef}
                    graphData={getGraphData()}
                    nodeCanvasObject={(node, ctx) => {
                      const radius = node.id === 'Claim' ? 14 : 10;
                      ctx.fillStyle = node.id === 'Claim' ? '#4CAF50' : 
                                      node.type === 'policy_node' ? '#FF9800' : '#2196F3';
                      ctx.beginPath();
                      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
                      ctx.fill();
                      ctx.strokeStyle = 'white';
                      ctx.lineWidth = 2;
                      ctx.stroke();
                      ctx.fillStyle = '#333';
                      ctx.font = '8px Arial';
                      ctx.textAlign = 'center';
                      ctx.textBaseline = 'top';
                      ctx.fillText(node.label, node.x, node.y + radius + 4);
                    }}
                    linkCanvasObject={(link, ctx) => {
                      ctx.strokeStyle = '#ccc';
                      ctx.lineWidth = 1.5;
                      ctx.beginPath();
                      ctx.moveTo(link.source.x, link.source.y);
                      ctx.lineTo(link.target.x, link.target.y);
                      ctx.stroke();
                      const midX = (link.source.x + link.target.x) / 2;
                      const midY = (link.source.y + link.target.y) / 2;
                      ctx.fillStyle = '#888';
                      ctx.font = '7px Arial';
                      ctx.textAlign = 'center';
                      ctx.textBaseline = 'middle';
                      ctx.fillText(link.label, midX, midY);
                    }}
                    width={graphWidth}
                    height={250}
                    cooldownTicks={100}
                    onEngineStop={() => graphRef.current?.zoomToFit(200, 30)}
                    enableZoomInteraction={true}
                    enableNodeDrag={true}
                  />
                )}
              </div>

              <div className='mt-5 p-4 bg-green-50 border border-green-200 rounded-xl text-[11px] leading-relaxed'>
                <div className="flex items-center gap-2 mb-1"><FaCheckCircle className="text-green-600" /> <b>Coverage Conditions Satisfied</b></div>
                {data.knowledge_graph.reasoning}
              </div>
            </div>

            <div className='grid lg:grid-cols-3 gap-4'>

              {/* Similar Claims Card */}
              <div className='bg-white rounded-3xl shadow p-5 flex flex-col justify-between h-full'>
                <div>
                  <h3 className='font-semibold text-sm mb-3 flex items-center gap-2'>
                    <FaSearch className="text-blue-600" /> Similar Claims
                  </h3>
                  <div className="overflow-y-auto max-h-[160px] pr-1">
                    {data.similar_claims && data.similar_claims.length > 0 ? (
                      data.similar_claims.map((claim) => (
                        <div 
                          key={claim.claim_id} 
                          onClick={() => setSelectedSimilarClaim(claim)}
                          className="p-3 border border-slate-100 rounded-2xl hover:bg-slate-50 transition-colors cursor-pointer mb-2.5 last:mb-0 text-[11px]"
                        >
                          <div className="flex justify-between items-center mb-1">
                            <span className="font-bold text-slate-700">{claim.claim_id}</span>
                            <span className="bg-blue-50 text-blue-700 font-semibold px-2 py-0.5 rounded-full text-[10px]">
                              {claim.similarity}% match
                            </span>
                          </div>
                          <div className="text-slate-500 line-clamp-2 mb-1.5">{claim.description}</div>
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="text-slate-400 font-medium">{claim.peril}</span>
                            <span className={`font-semibold ${
                              claim.recommendation === 'Approve' ? 'text-green-600' :
                              claim.recommendation === 'Reject' ? 'text-red-600' : 'text-amber-500'
                            }`}>{claim.recommendation}</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-400 text-center py-8">No similar claims found.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Risk Analytics Card */}
              <div className='bg-white rounded-3xl shadow p-5 flex flex-col justify-between h-full'>
                <div>
                  <h3 className='font-semibold text-sm mb-3 flex items-center gap-2'>
                    <FaChartBar className="text-blue-600" /> Risk Analytics
                  </h3>
                  <div className='grid grid-cols-1 gap-2.5 text-[11px] mt-2'>
                    <div className='flex justify-between border-b pb-2'>
                      <span className="text-slate-500">Fraud Probability:</span> 
                      <span className="font-semibold text-slate-800">{data.risk_analytics.fraud_probability}</span>
                    </div>
                    <div className='flex justify-between border-b pb-2'>
                      <span className="text-slate-500">Coverage Confidence:</span> 
                      <span className="font-semibold text-slate-800">{data.risk_analytics.coverage_confidence}</span>
                    </div>
                    <div className='flex justify-between border-b pb-2'>
                      <span className="text-slate-500">Historical Matches:</span> 
                      <span className="font-semibold text-slate-800">{data.risk_analytics.historical_matches}</span>
                    </div>
                    <div className='flex justify-between border-b pb-2'>
                      <span className="text-slate-500">Semantic Similarity:</span> 
                      <span className="font-semibold text-slate-800">{data.risk_analytics.semantic_similarity}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* AI Recommendation Card */}
              <div className='bg-white rounded-3xl shadow p-5 flex flex-col justify-between h-full min-h-[220px]'>
                <div>
                  <h3 className='font-semibold text-sm mb-3 flex items-center gap-2'>
                    <FaRobot className="text-slate-600" /> AI Recommendation
                  </h3>
                  <div className={`font-bold text-base mb-4 ${data.recommendation === 'Approve' ? 'text-green-700' :
                    data.recommendation === 'Reject' ? 'text-red-700' : 'text-amber-600'
                    }`}>
                    {data.recommendation}
                  </div>
                </div>

                <div className='flex flex-wrap gap-2'>
                  <button className={`px-4 py-2 rounded-xl text-[11px] font-medium transition-colors ${data.recommendation === 'Approve' ? 'bg-green-600 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}>Approve</button>
                  <button className={`px-4 py-2 rounded-xl text-[11px] font-medium transition-colors ${data.recommendation === 'Manual Review' ? 'bg-amber-500 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}>Manual Review</button>
                  <button className={`px-4 py-2 rounded-xl text-[11px] font-medium transition-colors ${data.recommendation === 'Reject' ? 'bg-red-600 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}>Reject</button>
                </div>
              </div>
            </div>

            <div className='bg-white rounded-3xl shadow p-5'>
              <h3 className='font-semibold text-sm mb-3 flex items-center gap-2'><FaComments className="text-indigo-500" /> Claims Copilot</h3>
              <div className='bg-slate-50 rounded-xl p-4 text-[11px] leading-relaxed'>
                {data.knowledge_graph.reasoning || 'Recommendation based on AI analysis.'}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modal for Similar Claim Detail */}
      {selectedSimilarClaim && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-xl max-w-lg w-full overflow-hidden border border-slate-100">
            <div className="p-6 text-left">
              <div className="flex justify-between items-center border-b pb-4 mb-4">
                <div>
                  <h4 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    Claim Details: {selectedSimilarClaim.claim_id}
                  </h4>
                  <p className="text-[10px] text-slate-500 font-medium">Historical Match Details</p>
                </div>
                <span className="bg-blue-50 text-blue-700 font-bold px-3 py-1 rounded-full text-xs">
                  {selectedSimilarClaim.similarity}% match
                </span>
              </div>
              
              <div className="space-y-4 text-[11px]">
                <div>
                  <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Description</span>
                  <p className="mt-1 text-slate-700 bg-slate-50 p-3 rounded-xl leading-relaxed">
                    {selectedSimilarClaim.description}
                  </p>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Peril</span>
                    <p className="mt-0.5 font-semibold text-slate-700">{selectedSimilarClaim.peril}</p>
                  </div>
                  <div>
                    <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Damage Type</span>
                    <p className="mt-0.5 font-semibold text-slate-700">{selectedSimilarClaim.damage_type}</p>
                  </div>
                  <div>
                    <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Estimated Loss</span>
                    <p className="mt-0.5 font-semibold text-slate-700">${selectedSimilarClaim.estimated_loss.toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">AI Recommendation</span>
                    <p className={`mt-0.5 font-semibold ${
                      selectedSimilarClaim.recommendation === 'Approve' ? 'text-green-600' :
                      selectedSimilarClaim.recommendation === 'Reject' ? 'text-red-600' : 'text-amber-500'
                    }`}>{selectedSimilarClaim.recommendation}</p>
                  </div>
                </div>
              </div>
              
              <div className="mt-6 flex justify-end">
                <button 
                  onClick={() => setSelectedSimilarClaim(null)}
                  className="bg-slate-800 hover:bg-slate-900 text-white font-medium text-xs px-4 py-2 rounded-xl transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal for Policy/Claim ID Validation Error */}
      {error && error.includes("not found") && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-xl max-w-sm w-full overflow-hidden border border-red-100 animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 text-center">
              <div className="w-12 h-12 bg-red-50 text-red-500 rounded-full flex items-center justify-center text-xl mx-auto mb-4 border border-red-100">
                ⚠️
              </div>
              <h4 className="text-sm font-bold text-slate-800 mb-2">Validation Alert</h4>
              <p className="text-xs text-slate-600 mb-6 leading-relaxed">
                {error}
              </p>
              <button 
                onClick={() => setError(null)}
                className="w-full bg-red-600 hover:bg-red-700 text-white font-medium text-xs py-2.5 rounded-xl transition-colors shadow-sm"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal for Processing Claim Loading Animation */}
      {loading && (() => {
        const currentStep = loadingSteps[loadingStepIndex] || loadingSteps[0];
        const StepIcon = currentStep.icon;
        return (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-3xl shadow-xl max-w-sm w-full overflow-hidden border border-slate-100 p-6 text-center animate-in fade-in zoom-in-95 duration-200">
              <div className={`w-14 h-14 ${currentStep.bg} ${currentStep.color} rounded-full flex items-center justify-center text-2xl mx-auto mb-4 border ${currentStep.border} animate-pulse transition-all duration-500 relative overflow-hidden`}>
                <StepIcon className="animate-icon-slide text-2xl absolute" />
              </div>
              <h4 className="text-sm font-bold text-slate-800 mb-1">Processing Claim</h4>
              <p className="text-xs text-slate-500 mb-6 font-medium h-4 transition-all duration-300">
                {currentStep.text}
              </p>
              
              {/* Loading Slider Animation Bar */}
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden relative">
                <div className="bg-blue-600 h-full rounded-full w-1/3 animate-slide absolute left-0 top-0"></div>
              </div>
              
              <p className="text-[10px] text-slate-400 mt-4">AI engines are evaluating taxonomy, ontology, and fraud risk...</p>
            </div>
            
            <style>{`
              @keyframes slide {
                0% { left: -40%; }
                100% { left: 100%; }
              }
              .animate-slide {
                animation: slide 1.5s infinite ease-in-out;
              }
              @keyframes icon-slide {
                0% { transform: translateX(-25px); opacity: 0; }
                15% { transform: translateX(-15px); opacity: 0.5; }
                50% { transform: translateX(0px); opacity: 1; }
                85% { transform: translateX(15px); opacity: 0.5; }
                100% { transform: translateX(25px); opacity: 0; }
              }
              .animate-icon-slide {
                animation: icon-slide 2.2s infinite ease-in-out;
              }
            `}</style>
          </div>
        );
      })()}
    </div>
  );
}

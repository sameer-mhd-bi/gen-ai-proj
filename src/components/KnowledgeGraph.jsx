import { useEffect, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import '../styles/KnowledgeGraph.css'

export default function KnowledgeGraph({ triplets = [], loading = false }) {
  const graphRef = useRef(null)
  const wrapperRef = useRef(null)
  const canvasWrapperRef = useRef(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [wrapperSize, setWrapperSize] = useState({ width: window.innerWidth - 40, height: 500 })
  const [filterText, setFilterText] = useState('')
  const [filterType, setFilterType] = useState('all') // 'all', 'subject', 'object'

  // Convert triplets to graph data format with filtering
  const getGraphData = () => {
    const nodes = new Map()
    const links = []

    // Filter triplets based on search criteria
    const filteredTriplets = triplets.filter((triplet) => {
      if (!filterText.trim()) return true
      
      const searchLower = filterText.toLowerCase()
      const subjectMatch = triplet.subject.toLowerCase().includes(searchLower)
      const objectMatch = triplet.object.toLowerCase().includes(searchLower)
      
      if (filterType === 'subject') return subjectMatch
      if (filterType === 'object') return objectMatch
      return subjectMatch || objectMatch // 'all'
    })

    filteredTriplets.forEach((triplet) => {
      const { subject, predicate, object } = triplet

      // Add subject node
      if (!nodes.has(subject)) {
        nodes.set(subject, {
          id: subject,
          label: subject,
          type: 'subject'
        })
      }

      // Add object node
      if (!nodes.has(object)) {
        nodes.set(object, {
          id: object,
          label: object,
          type: 'object'
        })
      }

      // Add link with predicate as label
      links.push({
        source: subject,
        target: object,
        label: predicate
      })
    })

    return {
      nodes: Array.from(nodes.values()),
      links: links,
      filteredTriplets
    }
  }

  const graphData = getGraphData()
  const filteredTriplets = graphData.filteredTriplets

  useEffect(() => {
    if (graphRef.current) {
      const graph = graphRef.current

      // Configure graph behavior
      graph.d3Force('charge').strength(-600)
      graph.d3Force('link').distance(160)
      graph.d3Force('collide')?.strength(0.5)

      // Center the graph
      setTimeout(() => {
        graph.zoomToFit(400, 50)
      }, 100)
    }
  }, [graphData])

  // Sync isFullscreen state with fullscreenchange event
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
    }
  }, [])

  // ResizeObserver to track wrapper dimensions
  useEffect(() => {
    if (!wrapperRef.current) return
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        setWrapperSize({ width, height })
      }
    })
    observer.observe(wrapperRef.current)
    return () => observer.disconnect()
  }, [])

  // ResizeObserver to track canvas wrapper height
  const [canvasHeight, setCanvasHeight] = useState(500)
  useEffect(() => {
    if (!canvasWrapperRef.current) return
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setCanvasHeight(entry.contentRect.height)
      }
    })
    observer.observe(canvasWrapperRef.current)
    return () => observer.disconnect()
  }, [])

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      wrapperRef.current?.requestFullscreen().then(() => {
        graphRef.current?.zoomToFit(400, 50)
      })
    } else {
      document.exitFullscreen()
    }
  }

  const handleZoomIn = () => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom()
      graphRef.current.zoom(currentZoom * 1.5, 300)
    }
  }

  const handleZoomOut = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(300, 20)
    }
  }

  const handleClearFilter = () => {
    setFilterText('')
    setFilterType('all')
  }

  if (loading) {
    return (
      <div className="knowledge-graph-container">
        <div className="knowledge-graph-loading">
          <div className="spinner"></div>
          <p>Extracting knowledge graph...</p>
        </div>
      </div>
    )
  }

  if (!triplets || triplets.length === 0) {
    return (
      <div className="knowledge-graph-container">
        <div className="knowledge-graph-empty">
          <p>No triplets available. Extract from a PDF to visualize the knowledge graph.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="knowledge-graph-container">
      <div className="knowledge-graph-stats">
        <div className="stat-item">
          <span className="stat-label">Nodes:</span>
          <span className="stat-value">{graphData.nodes.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Relations:</span>
          <span className="stat-value">{graphData.links.length}</span>
        </div>
        {filterText && (
          <div className="stat-item">
            <span className="stat-label">Filtered:</span>
            <span className="stat-value">{filteredTriplets.length} / {triplets.length}</span>
          </div>
        )}
      </div>
      
      {/* Filter Panel */}
      <div className="filter-panel">
        <div className="filter-input-group">
          <input
            type="text"
            className="filter-input"
            placeholder="Search by subject or object..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
          />
          {filterText && (
            <button className="filter-clear-btn" onClick={handleClearFilter} title="Clear filter">
              ✕
            </button>
          )}
        </div>
        <div className="filter-type-group">
          <label className="filter-radio">
            <input
              type="radio"
              name="filterType"
              value="all"
              checked={filterType === 'all'}
              onChange={(e) => setFilterType(e.target.value)}
            />
            <span>All</span>
          </label>
          <label className="filter-radio">
            <input
              type="radio"
              name="filterType"
              value="subject"
              checked={filterType === 'subject'}
              onChange={(e) => setFilterType(e.target.value)}
            />
            <span>Subject Only</span>
          </label>
          <label className="filter-radio">
            <input
              type="radio"
              name="filterType"
              value="object"
              checked={filterType === 'object'}
              onChange={(e) => setFilterType(e.target.value)}
            />
            <span>Object Only</span>
          </label>
        </div>
      </div>
      
      <div className={`knowledge-graph-wrapper${isFullscreen ? ' fullscreen' : ''}`} ref={wrapperRef}>
        <button className="fullscreen-toggle-btn" onClick={toggleFullscreen} title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}>
          {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
        </button>
        <button className="zoom-in-btn" onClick={handleZoomIn} title="Zoom In">
          +
        </button>
        <button className="zoom-out-btn" onClick={handleZoomOut} title="Zoom to Fit">
          −
        </button>
        <div ref={canvasWrapperRef} style={{ width: '100%', height: isFullscreen ? 'calc(100vh - 200px)' : '500px', overflow: 'hidden' }}>
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            nodeCanvasObject={(node, ctx) => {
              const radius = 18
              ctx.fillStyle = node.type === 'subject' ? '#4CAF50' : '#2196F3'

              // Draw shadow/glow
              ctx.shadowColor = 'rgba(0, 0, 0, 0.35)'
              ctx.shadowBlur = 8
              ctx.beginPath()
              ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
              ctx.fill()
              ctx.shadowBlur = 0

              // Draw stroke ring
              ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)'
              ctx.lineWidth = 2
              ctx.beginPath()
              ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
              ctx.stroke()

              // Draw label BELOW the bubble
              const label = node.label
              ctx.font = 'bold 11px Arial'
              ctx.textAlign = 'center'
              ctx.textBaseline = 'top'
              const labelY = node.y + radius + 5

              // White text-shadow effect
              ctx.fillStyle = 'rgba(255, 255, 255, 0.85)'
              ctx.fillText(label, node.x - 1, labelY + 1)
              ctx.fillText(label, node.x + 1, labelY + 1)
              ctx.fillText(label, node.x - 1, labelY - 1)
              ctx.fillText(label, node.x + 1, labelY - 1)

              // Dark label text
              ctx.fillStyle = '#222'
              ctx.fillText(label, node.x, labelY)
            }}
            nodePointerAreaPaint={(node, color, ctx) => {
              const radius = 20
              ctx.fillStyle = color
              ctx.beginPath()
              ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
              ctx.fill()
            }}
            linkCanvasObject={(link, ctx) => {
              const start = link.source
              const end = link.target

              ctx.strokeStyle = '#ccc'
              ctx.lineWidth = 1.5
              ctx.beginPath()
              ctx.moveTo(start.x, start.y)
              ctx.lineTo(end.x, end.y)
              ctx.stroke()

              // Draw edge label (predicate)
              const midX = (start.x + end.x) / 2
              const midY = (start.y + end.y) / 2
              
              ctx.fillStyle = '#666'
              ctx.font = '10px Arial'
              ctx.textAlign = 'center'
              ctx.textBaseline = 'middle'
              ctx.fillText(link.label.substring(0, 15), midX, midY)
            }}
            onNodeHover={(node) => {
              // Cursor feedback
              document.body.style.cursor = node ? 'pointer' : null
            }}
            onLinkHover={(link) => {
              document.body.style.cursor = link ? 'pointer' : null
            }}
            nodeLabel={(node) => `${node.label}`}
            linkLabel={(link) => `${link.label}`}
            width={wrapperSize.width}
            height={canvasHeight}
            enableNodeDrag={true}
            enableZoomInteraction={true}
            minZoom={0.5}
            maxZoom={8}
          />
        </div>


        <div className="knowledge-graph-legend">
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#4CAF50' }}></div>
            <span>Subject</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: '#2196F3' }}></div>
            <span>Object</span>
          </div>
          <div className="legend-item">
            <div className="legend-line"></div>
            <span>Relation</span>
          </div>
        </div>


        <div className="knowledge-graph-triplets">
          <div className="triplets-header">
            Extracted Triplets ({filteredTriplets.length}{filterText ? ` of ${triplets.length}` : ''})
          </div>
          <div className="triplets-list">
            {filteredTriplets.map((triplet, index) => (
              <div key={index} className="triplet-item">
                <div className="triplet-row">
                  <span className="triplet-index">{index + 1}</span>
                  <div className="triplet-content">
                    <div className="triplet-subject">{triplet.subject}</div>
                    <div className="triplet-arrow">→</div>
                    <div className="triplet-predicate">{triplet.predicate}</div>
                    <div className="triplet-arrow">→</div>
                    <div className="triplet-object">{triplet.object}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

import { useEffect, useRef } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import '../styles/KnowledgeGraph.css'

export default function KnowledgeGraph({ triplets = [], loading = false }) {
  const graphRef = useRef(null)

  // Convert triplets to graph data format
  const getGraphData = () => {
    const nodes = new Map()
    const links = []

    triplets.forEach((triplet) => {
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
      links: links
    }
  }

  const graphData = getGraphData()

  useEffect(() => {
    if (graphRef.current) {
      const graph = graphRef.current

      // Configure graph behavior
      graph.d3Force('charge').strength(-300)
      graph.d3Force('link').distance(80)
      graph.d3Force('collide')?.strength(0.5)

      // Center the graph
      setTimeout(() => {
        graph.zoomToFit(400, 50)
      }, 100)
    }
  }, [graphData])

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
      </div>
      
      <div className="knowledge-graph-wrapper">
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeCanvasObject={(node, ctx) => {
            const radius = 8
            ctx.fillStyle = node.type === 'subject' ? '#4CAF50' : '#2196F3'
            ctx.beginPath()
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
            ctx.fill()

            // Draw label
            const label = node.label
            ctx.fillStyle = '#fff'
            ctx.font = 'bold 12px Arial'
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillText(label.substring(0, 10), node.x, node.y)
          }}
          nodePointerAreaPaint={(node, color, ctx) => {
            const radius = 12
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
          width={window.innerWidth - 40}
          height={500}
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
        <div className="triplets-header">Extracted Triplets ({triplets.length})</div>
        <div className="triplets-list">
          {triplets.map((triplet, index) => (
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
  )
}

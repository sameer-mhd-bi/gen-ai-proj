import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'
import Sidebar from './components/Sidebar'
import { FaBars, FaSearch, FaTimes, FaTrash } from 'react-icons/fa'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import DimensionChart from './components/DimensionChart'

function App() {
  const [searchQuery, setSearchQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  const [activePath, setActivePath] = useState('/search')
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [collections, setCollections] = useState([])
  const [selectedCollection, setSelectedCollection] = useState('')
  const [selectedPdfForVectorization, setSelectedPdfForVectorization] = useState('')
  const [isVectorizing, setIsVectorizing] = useState(false)
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [defaultCollection, setDefaultCollection] = useState(() => {
    // Initialize from localStorage if it exists
    return localStorage.getItem('selectedCollection') || ''
  })
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [selectedDocuments, setSelectedDocuments] = useState([])
  const [selectedCollections, setSelectedCollections] = useState([])
  const [isDeleting, setIsDeleting] = useState(false)
  const [isTabLoading, setIsTabLoading] = useState(false)
  const [selectedCollectionForChunks, setSelectedCollectionForChunks] = useState(null)
  const [isLoadingChunks, setIsLoadingChunks] = useState(false)
  const [collectionChunks, setCollectionChunks] = useState([])
  const [dimensionData, setDimensionData] = useState([])
  const [isDimensionLoading, setIsDimensionLoading] = useState(false)
  const searchInputRef = useRef(null)
  const fileInputRef = useRef(null)
  const debounceTimer = useRef(null)

  // Persist selected collection to localStorage whenever it changes
  useEffect(() => {
    if (defaultCollection) {
      localStorage.setItem('selectedCollection', defaultCollection)
      console.log('Saved collection to localStorage:', defaultCollection)
    }
  }, [defaultCollection])

  // Debug: Track defaultCollection changes
  useEffect(() => {
    console.log('defaultCollection changed to:', defaultCollection)
  }, [defaultCollection])

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    // Fetch documents on mount
    fetchDocuments()
    fetchCollections()
  }, [])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        searchInputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Handle tab switching with loading state and selective state reset
  useEffect(() => {
    setIsTabLoading(true)
    
    // Reset state only for non-search tabs when switching
    const resetTabState = () => {
      if (activePath === '/collections') {
        // Reset collections tab state
        setSelectedCollection('')
        setSelectedPdfForVectorization('')
        setSelectedCollectionForChunks(null)
        setCollectionChunks([])
      } else if (activePath === '/documents') {
        // Reset documents tab state
        setSelectedDocument(null)
        setSelectedDocuments([])
        setSelectedCollections([])
      }
      // Search tab state is NOT reset - it persists across tabs
    }

    resetTabState()
    
    // Simulate minimal loading time and refresh data based on active tab
    const loadTabData = async () => {
      if (activePath === '/documents') {
        await fetchDocuments()
      } else if (activePath === '/collections') {
        await fetchCollections()
      }
      setIsTabLoading(false)
    }

    // Use requestAnimationFrame to ensure smooth transition
    const timer = requestAnimationFrame(() => {
      loadTabData()
    })

    return () => cancelAnimationFrame(timer)
  }, [activePath])

  const handleSearch = async () => {
    if (!inputValue.trim()) {
      console.log('Search query is empty')
      return
    }

    console.log('Current defaultCollection:', defaultCollection)
    
    if (!defaultCollection) {
      console.log('No collection selected, showing error')
      setSearchError('Please select a collection first. Go to Collections tab and click "Use This Collection"')
      setSubmittedQuery(inputValue)
      setSearchResults([])
      return
    }

    setIsSearching(true)
    setSearchError('')

    try {
      console.log('Sending search request with query:', inputValue, 'collection:', defaultCollection)
      
      const response = await fetch('http://localhost:5000/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query: inputValue,
          collection: defaultCollection
        }),
      })

      console.log('Response status:', response.status, response.statusText)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('API error response:', errorText)
        throw new Error(`Search request failed: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      console.log('Search response data:', data)
      setSubmittedQuery(data.query)
      setSearchResults(data.results || [])
      
      if (data.results && data.results.length === 0) {
        console.warn('No results returned from search')
        setSearchError('No results found. Make sure you have vectorized PDFs in the selected collection.')
      }

      if (data.results && data.results.length > 0) {
        setIsDimensionLoading(true)
        try {
         const dimResponse = await fetch(`http://localhost:5000/api/search/dimensions?collection=${encodeURIComponent(defaultCollection)}&query=${encodeURIComponent(inputValue)}`)
          if (dimResponse.ok) {
            const dimData = await dimResponse.json()
            setDimensionData(Array.isArray(dimData) ? dimData : (dimData.dimensions || []))
          } else {
            console.error('Failed to fetch dimension stats:', dimResponse.status)
            setDimensionData([])
          }
        } catch (dimError) {
          console.error('Error fetching dimension stats:', dimError)
          setDimensionData([])
        } finally {
          setIsDimensionLoading(false)
        }
      }
    } catch (error) {
      console.error('Error during search:', error)
      setSearchError(`Search error: ${error.message}`)
      setSubmittedQuery(inputValue)
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const handleInputChange = useCallback((e) => {
    const val = e.target.value
    setInputValue(val)
  }, [])

  const clearSearch = () => {
    setInputValue('')
    setSubmittedQuery('')
    searchInputRef.current?.focus()
  }

  const fetchDocuments = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/documents')
      if (response.ok) {
        const data = await response.json()
        setUploadedFiles(data.files || [])
      }
    } catch (error) {
      console.error('Error fetching documents:', error)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please upload a PDF file')
      return
    }

    setIsUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('http://localhost:5000/api/upload', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const data = await response.json()
        console.log('File uploaded successfully:', data)
        await fetchDocuments()
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      } else {
        alert('Upload failed')
      }
    } catch (error) {
      console.error('Error uploading file:', error)
      alert('Error uploading file')
    } finally {
      setIsUploading(false)
    }
  }

  const fetchCollections = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/collections')
      if (response.ok) {
        const data = await response.json()
        console.log('Collections fetched:', data.collections)
        setCollections(data.collections || [])
      } else {
        console.error('Failed to fetch collections:', response.status)
      }
    } catch (error) {
      console.error('Error fetching collections:', error)
    }
  }

  const fetchChunksForCollection = async (collectionName) => {
    setIsLoadingChunks(true)
    try {
      const response = await fetch(`http://localhost:5000/api/collections/${collectionName}/chunks`)
      if (response.ok) {
        const data = await response.json()
        console.log('Chunks fetched:', data.chunks)
        setCollectionChunks(data.chunks || [])
        setSelectedCollectionForChunks(collectionName)
      } else {
        console.error('Failed to fetch chunks:', response.status)
        alert('Failed to fetch chunks')
      }
    } catch (error) {
      console.error('Error fetching chunks:', error)
      alert('Error fetching chunks')
    } finally {
      setIsLoadingChunks(false)
    }
  }

  const handleVectorize = async () => {
    if (!selectedPdfForVectorization) {
      alert('Please select a PDF file')
      return
    }

    if (!selectedCollection) {
      alert('Please enter a collection name')
      return
    }

    setIsVectorizing(true)
    try {
      const response = await fetch('http://localhost:5000/api/vectorize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: selectedPdfForVectorization,
          collection_name: selectedCollection
        }),
      })

      if (response.ok) {
        const data = await response.json()
        console.log('PDF vectorized successfully:', data)
        alert(`Success! Vectorized ${data.chunks_count} chunks into collection '${data.collection}'`)
        await fetchCollections()
        setSelectedPdfForVectorization('')
      } else {
        const error = await response.json()
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      console.error('Error vectorizing PDF:', error)
      alert('Error vectorizing PDF')
    } finally {
      setIsVectorizing(false)
    }
  }

  const handleDeleteDocuments = async () => {
    if (selectedDocuments.length === 0) {
      alert('Please select at least one document to delete')
      return
    }

    if (!confirm(`Are you sure you want to delete ${selectedDocuments.length} document(s)? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(true)
    try {
      for (const filename of selectedDocuments) {
        const response = await fetch(`http://localhost:5000/api/documents/${filename}`, {
          method: 'DELETE',
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.error || `Failed to delete ${filename}`)
        }
      }

      console.log('Documents deleted successfully')
      alert(`Successfully deleted ${selectedDocuments.length} document(s)`)
      setSelectedDocuments([])
      await fetchDocuments()
    } catch (error) {
      console.error('Error deleting documents:', error)
      alert(`Error deleting documents: ${error.message}`)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleDeleteCollections = async () => {
    if (selectedCollections.length === 0) {
      alert('Please select at least one collection to delete')
      return
    }

    if (!confirm(`Are you sure you want to delete ${selectedCollections.length} collection(s)? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(true)
    try {
      for (const collectionName of selectedCollections) {
        const response = await fetch(`http://localhost:5000/api/collections/${collectionName}`, {
          method: 'DELETE',
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.error || `Failed to delete ${collectionName}`)
        }
      }

      console.log('Collections deleted successfully')
      alert(`Successfully deleted ${selectedCollections.length} collection(s)`)
      setSelectedCollections([])
      if (selectedCollections.includes(defaultCollection)) {
        setDefaultCollection('')
      }
      await fetchCollections()
    } catch (error) {
      console.error('Error deleting collections:', error)
      alert(`Error deleting collections: ${error.message}`)
    } finally {
      setIsDeleting(false)
    }
  }

  const toggleDocumentSelection = (filename) => {
    setSelectedDocuments(prev =>
      prev.includes(filename)
        ? prev.filter(f => f !== filename)
        : [...prev, filename]
    )
  }

  const toggleCollectionSelection = (collectionName) => {
    setSelectedCollections(prev =>
      prev.includes(collectionName)
        ? prev.filter(c => c !== collectionName)
        : [...prev, collectionName]
    )
  }

  const handleDeleteSingleDocument = async (filename) => {
    if (!confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(true)
    try {
      const response = await fetch(`http://localhost:5000/api/documents/${filename}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || `Failed to delete ${filename}`)
      }

      console.log('Document deleted successfully:', filename)
      if (selectedDocument?.name === filename) {
        setSelectedDocument(null)
      }
      await fetchDocuments()
    } catch (error) {
      console.error('Error deleting document:', error)
      alert(`Error deleting document: ${error.message}`)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleDeleteSingleCollection = async (collectionName) => {
    if (!confirm(`Are you sure you want to delete collection "${collectionName}"? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(true)
    try {
      const response = await fetch(`http://localhost:5000/api/collections/${collectionName}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || `Failed to delete ${collectionName}`)
      }

      console.log('Collection deleted successfully:', collectionName)
      if (defaultCollection === collectionName) {
        setDefaultCollection('')
      }
      await fetchCollections()
    } catch (error) {
      console.error('Error deleting collection:', error)
      alert(`Error deleting collection: ${error.message}`)
    } finally {
      setIsDeleting(false)
    }
  }


  return (
    <div className="app-layout">
      <div className="app-content-wrapper">
        <Sidebar
          isCollapsed={isCollapsed}
          onToggle={() => setIsCollapsed(prev => !prev)}
          open={sidebarOpen}
          onMobileToggle={() => setSidebarOpen(prev => !prev)}
          activePath={activePath}
          onPathChange={setActivePath}
        />
        <main className={`main-content${isCollapsed ? ' collapsed' : ''}${isMobile ? ' mobile' : ''}`}>
          {isTabLoading && (
            <div className="tab-loading-overlay">
              <div className="tab-loading-spinner"></div>
            </div>
          )}
          {activePath === '/search' && (
            <>
              <div className="search-input-panel">
                <div className="search-input-wrapper">
                  <FaSearch className="search-input-icon" aria-hidden="true" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    className="search-input-field"
                    placeholder="Enter your search query..."
                    value={inputValue}
                    onChange={handleInputChange}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    aria-label="Search"
                    autoComplete="off"
                    spellCheck="false"
                  />
                  {inputValue && (
                    <button
                      className="search-clear-btn"
                      onClick={clearSearch}
                      aria-label="Clear search"
                      tabIndex={0}
                    >
                      <FaTimes />
                    </button>
                  )}
                  <button className="search-submit-btn" onClick={handleSearch}>
                    Search
                  </button>
                </div>
              </div>
              
              {!defaultCollection && (
                <div className="search-result-panel-top">
                  <div className="search-result-panel-content" style={{ color: '#d32f2f', borderLeft: '4px solid #d32f2f', paddingLeft: '12px', fontWeight: '500' }}>
                    ⚠️ No collection selected. Go to Collections tab and select a collection before searching.
                  </div>
                </div>
              )}


              
              {defaultCollection && (
                <div className="search-result-panel-top">
                  <div className="search-result-panel-content" style={{ color: '#4caf50', borderLeft: '4px solid #4caf50', paddingLeft: '12px', fontSize: '14px' }}>
                    ✓ Using collection: <strong>{defaultCollection}</strong>
                  </div>
                </div>
              )}
              
              {submittedQuery && (
                <div className="search-result-panel-top">
                  <div className="search-result-panel-header">Search Query:</div>
                  <div className="search-result-panel-content">
                    {submittedQuery}
                  </div>
                </div>
              )}
              
              {isSearching && (
                <div className="search-result-panel-top">
                  <div className="search-result-panel-content" style={{ textAlign: 'center', color: '#999' }}>
                    Searching... Please wait.
                  </div>
                </div>
              )}
              
              {searchError && (
                <div className="search-result-panel-top">
                  <div className="search-result-panel-content" style={{ color: '#d32f2f', borderLeft: '4px solid #d32f2f', paddingLeft: '12px' }}>
                    {searchError}
                  </div>
                </div>
              )}
              
              {!isSearching && submittedQuery && searchResults.length === 0 && !searchError && (
                <div className="search-result-panel-top">
                  <div className="search-result-panel-content" style={{ textAlign: 'center', color: '#999' }}>
                    No results found for this query.
                  </div>
                </div>
              )}
              
              {searchResults.length > 0 && (
                <div className="search-results">
                  <div className="search-result-panel-header">Search Results ({searchResults.length}):</div>
                  {searchResults.map((result, index) => (
                    <div key={index} className="search-result-card">
                      <div className="search-result-header">
                        <div className="search-result-badge">{index + 1}</div>
                        <div className="search-result-title">{result.source}</div>
                        <div className="search-result-score">
                          <span className="relevance-label">Relevance</span>
                          <span className={`relevance-value ${result.similarity < 0 ? 'negative' : ''}`}>{(result.similarity * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                      <div className="search-result-preview">
                        {result.content}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {searchResults.length > 0 && (
                <div className="search-results-analytics">
                  <div className="search-chart-container">
                    <div className="search-chart-header">Relevancy Score Chart</div>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart 
                        data={searchResults.map((result, index) => ({
                          name: `Result ${index + 1}`,
                          relevance: parseFloat((result.similarity * 100).toFixed(2))
                        }))}
                        margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                        <XAxis 
                          dataKey="name" 
                          stroke="#666"
                          style={{ fontSize: '12px' }}
                        />
                        <YAxis 
                          domain={[0, 100]} 
                          stroke="#666"
                          style={{ fontSize: '12px' }}
                          label={{ value: 'Relevance Score (%)', angle: -90, position: 'left', offset: 10, textAnchor: 'middle' }}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#fff', 
                            border: '1px solid #ccc',
                            borderRadius: '4px',
                            padding: '8px'
                          }}
                          formatter={(value) => [`${value.toFixed(2)}%`, 'Relevance']}
                        />
                        <Legend 
                          wrapperStyle={{ paddingTop: '20px' }}
                          iconType="line"
                        />
                        <Line 
                          type="monotone" 
                          dataKey="relevance" 
                          stroke="#7baad8" 
                          strokeWidth={3}
                          dot={{ fill: '#7baad8', r: 6 }}
                          activeDot={{ r: 8 }}
                          name="Relevance Score"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  
                  <div className="documents-list-panel">
                    <div className="documents-list-header">Documents by Relevance</div>
                    <div className="documents-list">
                      {searchResults
                        .sort((a, b) => b.similarity - a.similarity)
                        .map((result, index) => (
                          <div key={index} className="document-list-item">
                            <div className="document-rank">{index + 1}</div>
                            <div className="document-info">
                              <div className="document-name">{result.source}</div>
                              <div className={`document-relevance ${result.similarity < 0 ? 'negative' : ''}`}>{(result.similarity * 100).toFixed(1)}%</div>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          {activePath === '/collections' && (
            <div className="collections-container">
              <div className="search-result-panel-top">
                <div className="search-result-panel-header">Collections</div>
                <div className="collections-form">
                  <div className="form-group">
                    <label>Select PDF to Vectorize:</label>
                    <select 
                      value={selectedPdfForVectorization}
                      onChange={(e) => setSelectedPdfForVectorization(e.target.value)}
                      className="form-select"
                    >
                      <option value="">-- Select a PDF --</option>
                      {uploadedFiles.map((file) => (
                        <option key={file.name} value={file.name}>
                          {file.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label>Collection Name:</label>
                    <input
                      type="text"
                      value={selectedCollection}
                      onChange={(e) => setSelectedCollection(e.target.value)}
                      placeholder="Enter collection name"
                      className="form-input"
                    />
                  </div>
                  
                  <button 
                    onClick={handleVectorize}
                    disabled={isVectorizing}
                    className="vectorize-button"
                  >
                    {isVectorizing ? 'Vectorizing...' : 'Vectorize & Store'}
                  </button>
                </div>
              </div>

              {collections.length > 0 && (
                <div className="search-result-panel-top">
                  <div className="search-result-panel-header">Available Collections ({collections.length})</div>
                  {collections.map((collection) => (
                    <div key={collection.name} className="document-partition" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1, display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <div style={{ flex: 1 }}>
                          <div className="document-partition-title" style={{ marginBottom: '0' }}>
                            <input
                              type="radio"
                              name="default-collection"
                              value={collection.name}
                              checked={defaultCollection === collection.name}
                              onChange={(e) => {
                                console.log('Radio button changed to:', e.target.value)
                                setDefaultCollection(e.target.value)
                              }}
                              style={{ marginRight: '10px', cursor: 'pointer' }}
                            />
                            {collection.name}
                          </div>
                          <div className="document-partition-content" style={{ marginBottom: '8px' }}>
                            <span 
                              style={{ cursor: 'pointer', color: '#7baad8', textDecoration: 'underline' }}
                              onClick={() => fetchChunksForCollection(collection.name)}
                              role="button"
                              tabIndex={0}
                              onKeyDown={(e) => e.key === 'Enter' && fetchChunksForCollection(collection.name)}
                            >
                              Total Chunks: {collection.count}
                            </span>
                          </div>
                          {collection.pdfs && collection.pdfs.length > 0 && (
                            <div style={{ fontSize: '13px', color: '#666', marginTop: '8px' }}>
                              <div style={{ fontWeight: '500', marginBottom: '4px' }}>PDFs in this collection:</div>
                              {collection.pdfs.map((pdf, idx) => (
                                <div key={idx} style={{ 
                                  fontSize: '12px', 
                                  color: '#7baad8', 
                                  marginLeft: '16px',
                                  wordBreak: 'break-word',
                                  marginBottom: '2px'
                                }}>
                                  • {pdf}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <button
                          className="collection-delete-btn"
                          onClick={() => handleDeleteSingleCollection(collection.name)}
                          disabled={isDeleting}
                          aria-label={`Delete ${collection.name}`}
                          title="Delete collection"
                        >
                          <FaTrash />
                        </button>
                      </div>
                    </div>
                  ))}
                  
                  {defaultCollection && (
                    <div style={{ marginTop: '16px', padding: '16px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                      <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>
                        Selected collection: <strong>{defaultCollection}</strong>
                      </div>
                      <button
                        onClick={() => {
                          // Collection is already set, just provide feedback
                          alert(`Using collection "${defaultCollection}" for search`)
                        }}
                        style={{
                          padding: '10px 20px',
                          backgroundColor: '#7baad8',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '14px',
                          fontWeight: '500'
                        }}
                      >
                        Use This Collection
                      </button>
                    </div>
                  )}
                </div>
              )}

              {selectedCollectionForChunks && (
                <div className="chunks-modal-overlay" onClick={() => setSelectedCollectionForChunks(null)}>
                  <div className="chunks-modal-container" onClick={(e) => e.stopPropagation()}>
                    <div className="chunks-modal-header">
                      <span className="chunks-modal-title">
                        Chunks from "{selectedCollectionForChunks}" ({collectionChunks.length} total)
                      </span>
                      <button 
                        className="chunks-modal-close"
                        onClick={() => setSelectedCollectionForChunks(null)}
                        aria-label="Close chunks viewer"
                      >
                        ✕
                      </button>
                    </div>
                    <div className="chunks-modal-content">
                      {isLoadingChunks ? (
                        <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                          Loading chunks... Please wait.
                        </div>
                      ) : collectionChunks.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                          No chunks found in this collection.
                        </div>
                      ) : (
                        <div className="chunks-list">
                          {collectionChunks.map((chunk, index) => (
                            <div key={index} className="chunk-item">
                              <div className="chunk-header">
                                <div className="chunk-number">Chunk {chunk.id}</div>
                                <div className="chunk-source">{chunk.source}</div>
                              </div>
                              <div className="chunk-content">
                                {chunk.content}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          {activePath === '/documents' && (
            <div className="collections-container">
              <div className="search-result-panel-top">
                <div className="search-result-panel-header">Document Details</div>
                
                <div className="document-partition">
                  <div className="document-partition-title">Upload PDF</div>
                  <div className="upload-box">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf"
                      onChange={handleFileUpload}
                      disabled={isUploading}
                      style={{ display: 'none' }}
                      aria-label="Upload PDF file"
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isUploading}
                      className="upload-button"
                    >
                      {isUploading ? 'Uploading...' : '+ Upload PDF'}
                    </button>
                  </div>
                </div>

                {uploadedFiles.length > 0 && (
                  <div className="document-partition">
                    <div className="document-partition-title">Uploaded Files ({uploadedFiles.length})</div>
                    <div className="files-list">
                      {uploadedFiles.map((file, index) => (
                        <div 
                          key={index} 
                          className="file-item"
                          style={{ backgroundColor: selectedDocument?.name === file.name ? '#e8f4f8' : 'var(--bg)' }}
                        >
                          <span 
                            className="file-name"
                            onClick={() => setSelectedDocument(file)}
                            style={{ flex: 1, cursor: 'pointer' }}
                          >
                            {file.name}
                          </span>
                          <span className="file-size">({(file.size / 1024).toFixed(2)} KB)</span>
                          <button
                            className="file-delete-btn"
                            onClick={() => handleDeleteSingleDocument(file.name)}
                            disabled={isDeleting}
                            aria-label={`Delete ${file.name}`}
                            title="Delete document"
                          >
                            <FaTrash />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {selectedDocument && (
                <div className="pdf-modal-overlay" onClick={() => setSelectedDocument(null)}>
                  <div className="pdf-modal-container" onClick={(e) => e.stopPropagation()}>
                    <div className="pdf-modal-header">
                      <span className="pdf-modal-title">Viewing: {selectedDocument.name}</span>
                      <button 
                        className="pdf-modal-close"
                        onClick={() => setSelectedDocument(null)}
                        aria-label="Close PDF viewer"
                      >
                        ✕
                      </button>
                    </div>
                    <div className="pdf-modal-content">
                      <iframe
                        src={`http://localhost:5000/api/documents/${selectedDocument.name}`}
                        title={selectedDocument.name}
                      />
                    </div>
                    
                  </div>
                </div>
                
              )}
            </div>
          )}

                    {searchResults.length > 0 && (
            <div className="dimension-chart-section">
              <div className="dimension-chart-header">Embedding Dimension Statistics</div>
              <DimensionChart data={dimensionData} loading={isDimensionLoading} />
            </div>
          )}
        </main>
      </div>
      
    </div>
  )
}


export default App

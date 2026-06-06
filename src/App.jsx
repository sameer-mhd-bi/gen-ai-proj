import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'
import Sidebar from './components/Sidebar'
import { FaBars, FaSearch, FaTimes } from 'react-icons/fa'

function App() {
  const [searchQuery, setSearchQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  const searchInputRef = useRef(null)
  const debounceTimer = useRef(null)

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
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

  const handleSearch = () => {
    console.log('Searching for:', inputValue)
    setSubmittedQuery(inputValue)
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


  return (
    <div className="app-layout">
      <div className={`topbar${isCollapsed ? ' collapsed' : ''}`}>
        {isMobile && (
          <button
            className="topbar-hamburger"
            onClick={() => setSidebarOpen(prev => !prev)}
            aria-label="Open navigation"
          >
            <FaBars />
          </button>
        )}
        <div className="topbar-search-wrapper">
          <FaSearch className="topbar-search-icon-left" aria-hidden="true" />
          <input
            ref={searchInputRef}
            type="text"
            className="topbar-search-input"
            placeholder="delayed shipments from asiapac to europe in Q2 due to port congestion and customs"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            aria-label="Search"
            autoComplete="off"
            spellCheck="false"
          />
          <div className="topbar-search-actions">
            {inputValue && (
              <button
                className="topbar-clear-btn"
                onClick={clearSearch}
                aria-label="Clear search"
                tabIndex={0}
              >
                <FaTimes />
              </button>
            )}
          </div>
          <button className="topbar-search-btn" onClick={handleSearch}>
            Search
          </button>
        </div>
      </div>
      <Sidebar
        isCollapsed={isCollapsed}
        onToggle={() => setIsCollapsed(prev => !prev)}
        open={sidebarOpen}
        onMobileToggle={() => setSidebarOpen(prev => !prev)}
      />
      <main className={`main-content${isCollapsed ? ' collapsed' : ''}${isMobile ? ' mobile' : ''}`}>
      </main>
      {submittedQuery && (
        <div className={`search-result-panel${isCollapsed ? ' collapsed' : ''}`}>
          <div className="search-result-panel-header">Search Query:</div>
          <div className="search-result-panel-content">
            {submittedQuery}
          </div>
        </div>
      )}
    </div>
  )
}


export default App

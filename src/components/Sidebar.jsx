import React, { useState, useEffect } from 'react';
import { FaHome, FaUser, FaCog, FaChartBar, FaEnvelope, FaFileAlt, FaBars, FaTimes, FaFolder, FaSearch } from 'react-icons/fa';
import aspireLogo from '../assets/aspire.png';
import './Sidebar.css';

const Sidebar = ({ collapsed, open, onToggle, activePath, onPathChange }) => {
  const navItems = [
    { path: '/search', label: 'Search', icon: <FaSearch /> },
    { path: '/collections', label: 'Collections', icon: <FaFolder /> },
    { path: '/documents', label: 'Documents', icon: <FaFileAlt /> },
    { path: '/knowledge-graph', label: 'Knowledge Graph', icon: <FaChartBar /> },
    { path: '/settings', label: 'Settings', icon: <FaCog /> },
  ];

  useEffect(() => {
    // Set active path based on current URL if not already set
    const currentPath = window.location.pathname;
    const matchingItem = navItems.find(item => item.path === currentPath);
    if (matchingItem) {
      onPathChange(currentPath);
    }
  }, []);

  const handleNavClick = (path) => {
    onPathChange(path);
  };

  return (
    <>
      {open && (
        <div className="sidebar-overlay" onClick={onToggle} />
      )}
      <div className={`sidebar ${collapsed ? 'collapsed' : ''} ${open ? 'open' : ''}`}>

        <img src={aspireLogo} alt="Aspire" className="sidebar-aspire-logo" />
        <div className="sidebar-logo">Semantic Search</div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <a
            key={item.path}
            href={item.path}
            className={`sidebar-nav-item ${activePath === item.path ? 'active' : ''}`}
            onClick={() => handleNavClick(item.path)}
          >
            <span className="sidebar-nav-icon">{item.icon}</span>
            <span className="sidebar-nav-link">{item.label}</span>
          </a>
        ))}
      </nav>
     
      </div>
    </>
  );
};

export default Sidebar;
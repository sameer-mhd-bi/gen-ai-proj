import React from 'react';
import { FaHome, FaUser, FaCog, FaChartBar, FaEnvelope, FaFileAlt, FaBars, FaTimes, FaFolder } from 'react-icons/fa';
import './Sidebar.css';

const Sidebar = ({ collapsed, open, onToggle }) => {
  const navItems = [
    { path: '/collection', label: 'Collection', icon: <FaFolder /> },
    { path: '/documents', label: 'Documents', icon: <FaFileAlt /> },
    { path: '/settings', label: 'Settings', icon: <FaCog /> },
  ];

  return (
    <>
      {open && (
        <div className="sidebar-overlay" onClick={onToggle} />
      )}
      <div className={`sidebar ${collapsed ? 'collapsed' : ''} ${open ? 'open' : ''}`}>

        <div className="sidebar-logo">Semantic Search</div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <a
            key={item.path}
            href={item.path}
            className="sidebar-nav-item"
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
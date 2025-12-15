'use client';

import React, { useState, useEffect, useRef } from 'react';

interface ContextMenuProps {
  x: number;
  y: number;
  workflowId: string;
  currentRecommendation: string | null;
  onClose: () => void;
  onUpdate: (workflowId: string, recommendation: string | null) => void;
}

export const WorkflowContextMenu: React.FC<ContextMenuProps> = ({
  x,
  y,
  workflowId,
  currentRecommendation,
  onClose,
  onUpdate,
}) => {
  const [showExecutionSubmenu, setShowExecutionSubmenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const executionModes = [
    { label: 'No recommendation (Async)', value: null, icon: '🔄' },
    { label: 'Sync - Wait for completion', value: 'true', icon: '⚡' },
    { label: 'Sync - 10 seconds', value: 'timeout=10', icon: '⏱️' },
    { label: 'Sync - 30 seconds', value: 'timeout=30', icon: '⏱️' },
    { label: 'Sync - 60 seconds', value: 'timeout=60', icon: '⏱️' },
  ];

  const handleExecutionModeSelect = async (value: string | null) => {
    await onUpdate(workflowId, value);
    onClose();
  };

  return (
    <div
      ref={menuRef}
      className="context-menu"
      style={{
        position: 'fixed',
        top: y,
        left: x,
        zIndex: 1000,
      }}
    >
      {/* Main Menu */}
      <div className="context-menu-item" onMouseEnter={() => setShowExecutionSubmenu(true)}>
        <span className="context-menu-icon">⚙️</span>
        <span className="context-menu-label">Set Execution Mode</span>
        <span className="context-menu-arrow">▶</span>
      </div>

      <div className="context-menu-separator" />

      {/* Future options (disabled for now) */}
      <div className="context-menu-item disabled">
        <span className="context-menu-icon">⭐</span>
        <span className="context-menu-label">Add to Favorites</span>
        <span className="context-menu-badge">Soon</span>
      </div>

      <div className="context-menu-item disabled">
        <span className="context-menu-icon">📋</span>
        <span className="context-menu-label">Duplicate</span>
        <span className="context-menu-badge">Soon</span>
      </div>

      <div className="context-menu-item disabled">
        <span className="context-menu-icon">🗑️</span>
        <span className="context-menu-label">Delete</span>
        <span className="context-menu-badge">Soon</span>
      </div>

      {/* Submenu */}
      {showExecutionSubmenu && (
        <div
          className="context-submenu"
          style={{
            position: 'fixed',
            top: y,
            left: x + 220, // Offset to the right
          }}
          onMouseLeave={() => setShowExecutionSubmenu(false)}
        >
          {executionModes.map((mode) => (
            <div
              key={mode.value || 'null'}
              className={`context-menu-item ${
                currentRecommendation === mode.value ? 'active' : ''
              }`}
              onClick={() => handleExecutionModeSelect(mode.value)}
            >
              <span className="context-menu-icon">{mode.icon}</span>
              <span className="context-menu-label">{mode.label}</span>
              {currentRecommendation === mode.value && (
                <span className="context-menu-check">✓</span>
              )}
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .context-menu {
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          min-width: 220px;
          padding: 4px 0;
          font-size: 14px;
        }

        .context-submenu {
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          min-width: 240px;
          padding: 4px 0;
          font-size: 14px;
        }

        .context-menu-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          cursor: pointer;
          transition: background 0.15s;
        }

        .context-menu-item:hover:not(.disabled) {
          background: #f5f5f5;
        }

        .context-menu-item.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .context-menu-item.active {
          background: #e3f2fd;
        }

        .context-menu-icon {
          font-size: 16px;
          width: 20px;
          text-align: center;
        }

        .context-menu-label {
          flex: 1;
        }

        .context-menu-arrow {
          color: #999;
          font-size: 12px;
        }

        .context-menu-check {
          color: #4caf50;
          font-weight: bold;
        }

        .context-menu-badge {
          background: #2196f3;
          color: white;
          font-size: 10px;
          padding: 2px 6px;
          border-radius: 10px;
        }

        .context-menu-separator {
          height: 1px;
          background: #e0e0e0;
          margin: 4px 0;
        }
      `}</style>
    </div>
  );
};


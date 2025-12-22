/**
 * Folder Picker Component
 * Simple text input for folder paths
 * 
 * Just type or paste your folder path - browsers can't browse folders for security reasons
 */

import React from 'react';

export interface FolderPickerProps {
  value?: string;
  onChange: (folderPath: string | null) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function FolderPicker({
  value,
  onChange,
  disabled = false,
  placeholder = 'Enter full folder path (e.g., D:\\exports or C:\\Users\\YourName\\Desktop)',
}: FolderPickerProps) {
  
  const handleClear = () => {
    onChange('');
  };

  return (
    <div className="folder-picker">
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <span style={{ 
            position: 'absolute', 
            left: '10px', 
            top: '50%', 
            transform: 'translateY(-50%)',
            fontSize: '14px'
          }}>
            📁
          </span>
          <input
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            style={{
              width: '100%',
              padding: '8px 12px 8px 32px',
              border: '1px solid var(--theme-border)',
              borderRadius: '6px',
              background: disabled ? 'var(--theme-surface)' : 'var(--theme-surface-variant)',
              color: 'var(--theme-text)',
              fontSize: '13px',
              fontFamily: 'monospace',
              opacity: disabled ? 0.6 : 1,
            }}
          />
        </div>

        {value && !disabled && (
          <button
            onClick={handleClear}
            style={{
              padding: '6px 10px',
              background: 'transparent',
              border: '1px solid var(--theme-border)',
              borderRadius: '4px',
              cursor: 'pointer',
              color: 'var(--theme-text-secondary)',
              fontSize: '12px',
            }}
            title="Clear"
          >
            ✕
          </button>
        )}
      </div>
      
      <div style={{ 
        fontSize: '11px', 
        color: 'var(--theme-text-secondary)', 
        marginTop: '4px',
      }}>
        💡 Copy path from File Explorer address bar (Ctrl+L → Ctrl+C → Paste here)
      </div>
    </div>
  );
}

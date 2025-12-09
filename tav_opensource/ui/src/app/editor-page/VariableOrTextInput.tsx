/**
 * VariableOrTextInput Component
 * 
 * Advanced input component that allows users to choose between:
 * - Literal: Direct text input
 * - Variable: Pick from shared space variables
 * - Template: Mix text with {{variable}} placeholders
 */

import React, { useState, useRef, useEffect } from 'react';

interface AvailableVariable {
  nodeName: string;
  nodeId: string;
  uniqueKey: string; // For React keys to avoid duplicates
  fields: { name: string; type?: string }[];
}

interface ConfigValue {
  source: 'literal' | 'variable' | 'template';
  value?: string;
  variable_path?: string;
  template?: string;
}

interface VariableOrTextInputProps {
  label: string;
  value: any; // Can be string, ConfigValue object, or undefined
  onChange: (value: ConfigValue | string) => void;
  availableVariables: AvailableVariable[];
  widget?: 'text' | 'textarea' | 'password';
  placeholder?: string;
  required?: boolean;
  description?: string;
}

export function VariableOrTextInput({
  label,
  value,
  onChange,
  availableVariables,
  widget = 'text',
  placeholder,
  required,
  description,
}: VariableOrTextInputProps) {
  // Parse existing value
  const parseValue = (val: any): ConfigValue => {
    if (!val) {
      return { source: 'literal', value: '' };
    }
    
    // If it's already our config format
    if (typeof val === 'object' && val.source) {
      return val;
    }
    
    // If it's a plain string, detect if it has templates
    if (typeof val === 'string') {
      // Check for both {{ (node variables) and { (system variables)
      if (val.includes('{')) {
        return { source: 'template', template: val };
      }
      return { source: 'literal', value: val };
    }
    
    return { source: 'literal', value: String(val) };
  };

  const [configValue, setConfigValue] = useState<ConfigValue>(parseValue(value));
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [autocompleteType, setAutocompleteType] = useState<'node' | 'system'>('node'); // Track which type
  const [cursorPosition, setCursorPosition] = useState(0);
  const [showPassword, setShowPassword] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  // Update when value prop changes
  useEffect(() => {
    setConfigValue(parseValue(value));
  }, [value]);

  const handleSourceChange = (newSource: 'literal' | 'variable' | 'template') => {
    const newValue: ConfigValue = { source: newSource };
    
    if (newSource === 'literal') {
      newValue.value = configValue.value || configValue.template || '';
    } else if (newSource === 'variable') {
      newValue.variable_path = configValue.variable_path || '';
    } else if (newSource === 'template') {
      newValue.template = configValue.template || configValue.value || '';
    }
    
    setConfigValue(newValue);
    onChange(newValue);
  };

  const handleTextChange = (text: string) => {
    let newValue = { ...configValue };
    let shouldCheckAutocomplete = false;
    
    if (configValue.source === 'literal') {
      // Auto-switch to template mode if user types { or {{
      if (text.includes('{')) {
        console.log('🔄 Auto-switching from LITERAL to TEMPLATE mode');
        newValue.source = 'template';
        newValue.template = text;
        delete newValue.value;
        shouldCheckAutocomplete = true;
      } else {
        newValue.value = text;
      }
    } else if (configValue.source === 'template') {
      newValue.template = text;
      shouldCheckAutocomplete = true;
    }
    
    // Check for autocomplete if we're in template mode (or just switched to it)
    if (shouldCheckAutocomplete) {
      // Simple check: look at what's at the cursor position
      // Find last unclosed brace sequence
      let showDropdown = false;
      let dropdownType: 'node' | 'system' = 'node';
      
      // Check if we're in the middle of typing a variable
      const lastDoubleOpen = text.lastIndexOf('{{');
      const lastSingleOpen = text.lastIndexOf('{');
      const lastDoubleClose = text.lastIndexOf('}}');
      const lastSingleClose = text.lastIndexOf('}');
      
      // If {{ exists and is not closed
      if (lastDoubleOpen !== -1 && lastDoubleOpen > lastDoubleClose) {
        showDropdown = true;
        dropdownType = 'node';
        console.log('🟢 {{ open and not closed - showing NODE variables');
      }
      // Else if single { exists and is not closed AND it's not part of {{
      else if (lastSingleOpen !== -1 && lastSingleOpen > lastSingleClose) {
        // Make sure this { is not part of a {{
        const isPartOfDouble = lastSingleOpen > 0 && text[lastSingleOpen - 1] === '{';
        if (!isPartOfDouble) {
          showDropdown = true;
          dropdownType = 'system';
          console.log('🟡 { open and not closed - showing SYSTEM variables');
        }
      }
      
      setShowAutocomplete(showDropdown);
      if (showDropdown) {
        setAutocompleteType(dropdownType);
      }
    } else {
      setShowAutocomplete(false);
    }
    
    setConfigValue(newValue);
    
    // For backend compatibility: output plain strings instead of structured format
    // Backend's resolve_template() handles {{var}} and {system} in plain strings automatically
    if (newValue.source === 'literal') {
      onChange(text);  // Plain string
    } else if (newValue.source === 'template') {
      onChange(text);  // Plain string with {{}} or {}
    } else {
      onChange(newValue);  // Only variable mode uses structured format
    }
  };

  const handleVariableSelect = (varPath: string, isSystemVar: boolean = false) => {
    if (configValue.source === 'variable') {
      const newValue = { source: 'variable' as const, variable_path: varPath };
      setConfigValue(newValue);
      // For variable mode, keep structured format for clarity
      onChange(newValue);
    } else if (configValue.source === 'template' && inputRef.current) {
      // Insert variable into template at cursor position
      const text = configValue.template || '';
      const beforeCursor = text.substring(0, cursorPosition);
      const afterCursor = text.substring(cursorPosition);
      
      let newText: string;
      
      if (isSystemVar) {
        // Find the { before cursor (single brace)
        const lastBraceIndex = beforeCursor.lastIndexOf('{');
        newText = 
          text.substring(0, lastBraceIndex) + 
          `{${varPath}}` + 
          afterCursor;
      } else {
        // Find the {{ before cursor (double brace)
        const lastBraceIndex = beforeCursor.lastIndexOf('{{');
        newText = 
          text.substring(0, lastBraceIndex) + 
          `{{${varPath}}}` + 
          afterCursor;
      }
      
      const newValue = { source: 'template' as const, template: newText };
      setConfigValue(newValue);
      // Output plain string for backend
      onChange(newText);
      setShowAutocomplete(false);
    }
  };

  const getCurrentValue = () => {
    if (configValue.source === 'literal') return configValue.value || '';
    if (configValue.source === 'template') return configValue.template || '';
    return '';
  };

  return (
    <div className="space-y-2">
      {/* Source Selector */}
      <div className="flex gap-3 items-center">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="radio"
            name={`source-${label}`}
            checked={configValue.source === 'literal'}
            onChange={() => handleSourceChange('literal')}
            className="w-3.5 h-3.5"
            style={{ accentColor: 'var(--theme-primary)' }}
          />
          <span className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
            Literal
          </span>
        </label>
        
        {availableVariables.length > 0 && (
          <>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name={`source-${label}`}
                checked={configValue.source === 'variable'}
                onChange={() => handleSourceChange('variable')}
                className="w-3.5 h-3.5"
                style={{ accentColor: 'var(--theme-primary)' }}
              />
              <span className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
                Variable
              </span>
            </label>
            
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name={`source-${label}`}
                checked={configValue.source === 'template'}
                onChange={() => handleSourceChange('template')}
                className="w-3.5 h-3.5"
                style={{ accentColor: 'var(--theme-primary)' }}
              />
              <span className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
                Template
              </span>
            </label>
          </>
        )}
      </div>

      {/* Input Field */}
      {configValue.source === 'variable' ? (
        // Variable Picker Dropdown with nested structure
        <select
          value={configValue.variable_path || ''}
          onChange={(e) => handleVariableSelect(e.target.value)}
          className="w-full px-3 py-2 border rounded text-sm focus:outline-none"
          style={{
            background: 'var(--theme-surface-variant)',
            color: 'var(--theme-text)',
            borderColor: 'var(--theme-border)',
          }}
          onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
          onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
        >
          <option value="">Select variable...</option>
          {availableVariables.map((node) => (
            <optgroup key={node.uniqueKey} label={node.nodeName}>
              {node.fields.map((field) => {
                // System variables are flat (just the field name)
                const isSystemVar = node.nodeId === 'system';
                
                if (isSystemVar) {
                  // System variables: just use field name
                  return (
                    <option key={field.name} value={field.name}>
                      {field.name}
                    </option>
                  );
                }
                
                // For node variables, add nested options
                const options = [
                  { value: `${node.nodeId}.${field.name}`, label: field.name },
                ];
                
                // Add common nested paths for structured data
                if (field.type === 'universal' || field.type === 'object' || field.name === 'output') {
                  options.push(
                    { value: `${node.nodeId}.${field.name}.data`, label: `${field.name}.data` },
                    { value: `${node.nodeId}.${field.name}.result`, label: `${field.name}.result` },
                    { value: `${node.nodeId}.${field.name}.value`, label: `${field.name}.value` },
                    { value: `${node.nodeId}.${field.name}.text`, label: `${field.name}.text` },
                    { value: `${node.nodeId}.${field.name}.content`, label: `${field.name}.content` },
                    { value: `${node.nodeId}.${field.name}.message`, label: `${field.name}.message` },
                    { value: `${node.nodeId}.${field.name}.body`, label: `${field.name}.body` },
                    { value: `${node.nodeId}.${field.name}.status`, label: `${field.name}.status` }
                  );
                }
                
                return options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ));
              })}
            </optgroup>
          ))}
        </select>
      ) : widget === 'textarea' ? (
        // Textarea for literal/template
        <div className="relative">
          <textarea
            ref={inputRef as React.RefObject<HTMLTextAreaElement>}
            value={getCurrentValue()}
            onChange={(e) => {
              handleTextChange(e.target.value);
              setCursorPosition(e.target.selectionStart || 0);
            }}
            onKeyDown={(e) => {
              if (e.key === '{' && e.currentTarget.value.endsWith('{')) {
                setShowAutocomplete(true);
              }
            }}
            placeholder={
              configValue.source === 'template'
                ? 'Type text and use {{variable}} or {system} for dynamic values'
                : placeholder
            }
            className="w-full px-3 py-2 border rounded text-sm resize-y min-h-[80px] focus:outline-none"
            style={{
              background: 'var(--theme-surface-variant)',
              color: 'var(--theme-text)',
              borderColor: 'var(--theme-border)',
            }}
            onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--theme-border)';
              setTimeout(() => setShowAutocomplete(false), 200);
            }}
            rows={4}
          />
          
          {/* Autocomplete for template mode */}
          {showAutocomplete && configValue.source === 'template' && availableVariables.length > 0 && (
            <div
              className="absolute z-10 mt-1 w-full border rounded shadow-lg max-h-48 overflow-y-auto"
              style={{
                background: 'var(--theme-surface)',
                borderColor: 'var(--theme-border)',
              }}
            >
              {availableVariables
                .filter(node => {
                  // Show system variables only for system autocomplete, others for node
                  if (autocompleteType === 'system') {
                    return node.nodeId === 'system';
                  } else {
                    return node.nodeId !== 'system';
                  }
                })
                .map((node) => (
                <div key={node.uniqueKey}>
                  <div
                    className="px-3 py-1.5 text-xs font-semibold"
                    style={{
                      background: 'var(--theme-surface-variant)',
                      color: 'var(--theme-text-secondary)',
                    }}
                  >
                    {node.nodeName}
                  </div>
                  {node.fields.map((field) => (
                    <button
                      key={field.name}
                      type="button"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        const isSystemVar = node.nodeId === 'system';
                        const varPath = isSystemVar ? field.name : `${node.nodeId}.${field.name}`;
                        handleVariableSelect(varPath, isSystemVar);
                      }}
                      className="w-full text-left px-4 py-1.5 text-sm hover:bg-opacity-80 transition-colors"
                      style={{
                        color: 'var(--theme-text)',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--theme-surface-hover)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      {field.name}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        // Text or Password input for literal/template
        <div className="relative">
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type={widget === 'password' && !showPassword ? 'password' : 'text'}
            value={getCurrentValue()}
            onChange={(e) => {
              handleTextChange(e.target.value);
              setCursorPosition(e.target.selectionStart || 0);
            }}
            onKeyDown={(e) => {
              if (e.key === '{' && e.currentTarget.value.endsWith('{')) {
                setShowAutocomplete(true);
              }
            }}
            placeholder={
              configValue.source === 'template'
                ? 'Type text and use {{variable}} or {system} for dynamic values'
                : placeholder
            }
            className={`w-full px-3 py-2 border rounded text-sm focus:outline-none ${widget === 'password' ? 'pr-10' : ''}`}
            style={{
              background: 'var(--theme-surface-variant)',
              color: 'var(--theme-text)',
              borderColor: 'var(--theme-border)',
            }}
            onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--theme-border)';
              setTimeout(() => setShowAutocomplete(false), 200);
            }}
          />
          
          {/* Password visibility toggle button */}
          {widget === 'password' && (
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 focus:outline-none"
              style={{
                color: showPassword ? 'var(--theme-primary)' : 'var(--theme-text-muted)',
                cursor: 'pointer',
              }}
              title={showPassword ? 'Hide' : 'Show'}
            >
              {showPassword ? (
                // Eye slash (hide)
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              ) : (
                // Eye (show)
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              )}
            </button>
          )}
          
          {/* Autocomplete for template mode */}
          {showAutocomplete && configValue.source === 'template' && availableVariables.length > 0 && (
            <div
              className="absolute z-10 mt-1 w-full border rounded shadow-lg max-h-48 overflow-y-auto"
              style={{
                background: 'var(--theme-surface)',
                borderColor: 'var(--theme-border)',
              }}
            >
              {availableVariables
                .filter(node => {
                  // Show system variables only for system autocomplete, others for node
                  if (autocompleteType === 'system') {
                    return node.nodeId === 'system';
                  } else {
                    return node.nodeId !== 'system';
                  }
                })
                .map((node) => (
                <div key={node.uniqueKey}>
                  <div
                    className="px-3 py-1.5 text-xs font-semibold"
                    style={{
                      background: 'var(--theme-surface-variant)',
                      color: 'var(--theme-text-secondary)',
                    }}
                  >
                    {node.nodeName}
                  </div>
                  {node.fields.map((field) => (
                    <button
                      key={field.name}
                      type="button"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        const isSystemVar = node.nodeId === 'system';
                        const varPath = isSystemVar ? field.name : `${node.nodeId}.${field.name}`;
                        handleVariableSelect(varPath, isSystemVar);
                      }}
                      className="w-full text-left px-4 py-1.5 text-sm hover:bg-opacity-80 transition-colors"
                      style={{
                        color: 'var(--theme-text)',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--theme-surface-hover)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      {field.name}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Help Text */}
      {configValue.source === 'template' && (
        <p className="text-xs flex items-center gap-1" style={{ color: 'var(--theme-text-muted)' }}>
          <i className="fas fa-info-circle"></i>
          Type <code className="px-1 py-0.5 rounded" style={{ background: 'var(--theme-surface-variant)' }}>
            {'{{'}
          </code> for node variables or <code className="px-1 py-0.5 rounded" style={{ background: 'var(--theme-surface-variant)' }}>
            {'{'}
          </code> for system variables
        </p>
      )}
    </div>
  );
}


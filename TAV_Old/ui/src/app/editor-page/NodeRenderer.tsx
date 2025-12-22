import React from 'react';

interface Port {
  id: string;
  label: string;
  type: string;
  required?: boolean;
}

interface WorkflowNode {
  node_id: string;  // Changed from 'id' to match backend
  node_type: string; // Changed from 'type' to match backend
  name: string;
  category: string;
  position: { x: number; y: number };
  inputs: Port[];
  outputs: Port[];
  config: any;
  status?: 'idle' | 'pending' | 'executing' | 'completed' | 'failed';
  selected?: boolean;
  icon?: string; // FontAwesome icon class
  flipped?: boolean; // Whether ports are flipped horizontally
}

interface NodeRendererProps {
  node: WorkflowNode;
  executionStatus?: 'idle' | 'pending' | 'executing' | 'completed' | 'failed';
  previewData?: any;  // Execution result data for preview
  hasExecutionData?: boolean;  // Whether node has execution output data
  onSelect: (nodeId: string, event?: React.MouseEvent) => void;
  onDelete: (nodeId: string) => void;
  onDragStart: (nodeId: string, e: React.MouseEvent) => void;
  onPortMouseDown: (nodeId: string, portId: string, portType: 'input' | 'output', e: React.MouseEvent) => void;
  onContextMenu?: (nodeId: string, e: React.MouseEvent) => void;
}

export function NodeRenderer({ 
  node, 
  executionStatus = 'idle',
  previewData,
  hasExecutionData = false,
  onSelect, 
  onDelete, 
  onDragStart,
  onPortMouseDown,
  onContextMenu
}: NodeRendererProps) {
  
  // Build CSS class based on execution status
  const getExecutionStatusClass = () => {
    switch (executionStatus) {
      case 'pending': return 'node-pending';
      case 'executing': return 'node-executing';
      case 'completed': return 'node-completed';
      case 'failed': return 'node-failed';
      default: return '';
    }
  };
  
  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      triggers: 'node-category-triggers',
      communication: 'node-category-communication',
      ai: 'node-category-ai',
      workflow: 'node-category-workflow',
      input: 'node-category-input',
      output: 'node-category-output',
      processing: 'node-category-processing',
      actions: 'node-category-actions',
      control: 'node-category-control',
      business: 'node-category-business',
      analytics: 'node-category-analytics',
    };
    return colors[category.toLowerCase()] || '';
  };
  
  const getDefaultIcon = (category: string) => {
    const icons: Record<string, string> = {
      triggers: 'fa-solid fa-bolt',
      communication: 'fa-solid fa-paper-plane',
      ai: 'fa-solid fa-brain',
      workflow: 'fa-solid fa-sitemap',
      input: 'fa-solid fa-keyboard',
      output: 'fa-solid fa-display',
      processing: 'fa-solid fa-gears',
      actions: 'fa-solid fa-play',
      control: 'fa-solid fa-code-branch',
      business: 'fa-solid fa-briefcase',
      analytics: 'fa-solid fa-chart-line',
    };
    return icons[category.toLowerCase()] || 'fa-solid fa-cube';
  };

  // Render text preview
  const renderTextPreview = () => {
    if (!previewData || previewData.type !== 'text_preview') return null;
    
    const text = previewData.text || '';
    const charCount = previewData.char_count || 0;
    const wordCount = previewData.word_count || 0;
    
    return (
      <div className="node-preview-area">
        <div className="text-preview">
          <div className="preview-header">
            <span className="preview-label">📄 Output Preview</span>
            <span className="preview-badge">{charCount} chars{wordCount ? `, ${wordCount} words` : ''}</span>
          </div>
          <div className="preview-text-scroll">{text}</div>
        </div>
      </div>
    );
  };

  return (
    <div 
      className={`workflow-node ${getCategoryColor(node.category)} ${node.selected ? 'selected' : ''} ${getExecutionStatusClass()} ${node.flipped ? 'node-flipped' : ''}`}
      style={{
        left: `${node.position.x}px`,
        top: `${node.position.y}px`,
      }}
      onClick={(e) => onSelect(node.node_id, e)}
      onContextMenu={(e) => onContextMenu?.(node.node_id, e)}
      data-node-id={node.node_id}
    >
      {/* Execution Status Badge - Top Right */}
      {executionStatus === 'completed' && (
        <div className="node-status-badge success">
          <i className="fas fa-check"></i>
        </div>
      )}
      {executionStatus === 'failed' && (
        <div className="node-status-badge fail">
          <i className="fas fa-times"></i>
        </div>
      )}

      {/* Node Header */}
      <div 
        className="node-header"
        onClick={(e) => {
          // Handle selection on header click
          // Don't trigger if clicking delete button
          const target = e.target as HTMLElement;
          if (!target.closest('.node-delete-btn')) {
            // Don't stop propagation - let it bubble to parent for selection
            // But we do need to call onSelect here because the parent won't get it due to onMouseDown
            onSelect(node.node_id, e);
          }
        }}
        onMouseDown={(e) => {
          // Prevent click event from firing when dragging
          const target = e.target as HTMLElement;
          if (!target.closest('.node-delete-btn')) {
            onDragStart(node.node_id, e);
          }
        }}
      >
        <div className="node-title">
          <span className="node-icon">
            <i className={node.icon || getDefaultIcon(node.category)}></i>
          </span>
          <span className="node-title-text">{node.name}</span>
          {hasExecutionData && (
            <span 
              className="node-data-indicator" 
              title="Has execution data - click node to view in Output tab"
              style={{
                display: 'inline-block',
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: '#10b981',
                marginLeft: '6px',
                boxShadow: '0 0 4px rgba(16, 185, 129, 0.6)'
              }}
            ></span>
          )}
        </div>
        <div className="node-actions">
          <button
            className="node-delete-btn"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(node.node_id);
            }}
            title="Delete node"
          >
            <i className="fas fa-trash"></i>
          </button>
        </div>
      </div>

      {/* Node Body */}
      <div className="node-body">
        {/* Preview Area - Shows text/image content after execution */}
        {renderTextPreview()}
        
        <div className="node-ports">
          {!node.flipped ? (
            <>
              {/* Normal: Inputs on left, Outputs on right */}
              <div className="node-inputs">
                {(node.inputs || []).map((input) => (
                  <div 
                    key={input.id || `input-${Math.random()}`}
                    className="node-port node-input"
                    data-port={input.id}
                    data-port-type={input.type}
                  >
                    <div 
                      className={`port-handle input-handle port-type-${input.type}`}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        onPortMouseDown(node.node_id, input.id, 'input', e);
                      }}
                    ></div>
                    <div className="port-label">{input.label}</div>
                  </div>
                ))}
              </div>

              <div className="node-outputs">
                {(node.outputs || []).map((output) => (
                  <div 
                    key={output.id || `output-${Math.random()}`}
                    className="node-port node-output"
                    data-port={output.id}
                    data-port-type={output.type}
                  >
                    <div className="port-label">{output.label}</div>
                    <div 
                      className={`port-handle output-handle port-type-${output.type}`}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        onPortMouseDown(node.node_id, output.id, 'output', e);
                      }}
                    ></div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              {/* Flipped: Outputs on left, Inputs on right */}
              <div className="node-outputs" style={{ alignItems: 'flex-start' }}>
                {(node.outputs || []).map((output) => (
                  <div 
                    key={output.id || `output-${Math.random()}`}
                    className="node-port node-output"
                    data-port={output.id}
                    data-port-type={output.type}
                  >
                    <div 
                      className={`port-handle output-handle port-type-${output.type}`}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        onPortMouseDown(node.node_id, output.id, 'output', e);
                      }}
                    ></div>
                    <div className="port-label">{output.label}</div>
                  </div>
                ))}
              </div>

              <div className="node-inputs" style={{ alignItems: 'flex-end' }}>
                {(node.inputs || []).map((input) => (
                  <div 
                    key={input.id || `input-${Math.random()}`}
                    className="node-port node-input"
                    data-port={input.id}
                    data-port-type={input.type}
                  >
                    <div className="port-label">{input.label}</div>
                    <div 
                      className={`port-handle input-handle port-type-${input.type}`}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        onPortMouseDown(node.node_id, input.id, 'input', e);
                      }}
                    ></div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

interface NodesLayerProps {
  nodes: WorkflowNode[];
  nodeStates: Record<string, { status: 'idle' | 'pending' | 'executing' | 'completed' | 'failed'; error?: string; previewData?: any }>;
  nodeExecutionData?: Record<string, any>;  // Add execution data map
  onNodeSelect: (nodeId: string, event?: React.MouseEvent) => void;
  onNodeDelete: (nodeId: string) => void;
  onNodeDragStart: (nodeId: string, e: React.MouseEvent) => void;
  onPortMouseDown: (nodeId: string, portId: string, portType: 'input' | 'output', e: React.MouseEvent) => void;
  onNodeContextMenu?: (nodeId: string, e: React.MouseEvent) => void;
  selectedNodes?: Set<string>;  // Add selected nodes set for multi-selection
}

export function NodesLayer({
  nodes,
  nodeStates,
  nodeExecutionData = {},
  onNodeSelect,
  onNodeDelete,
  onNodeDragStart,
  onPortMouseDown,
  onNodeContextMenu,
  selectedNodes = new Set(),
}: NodesLayerProps) {
  return (
    <>
      {nodes.map((node) => {
        // Check if this node is in the multi-selection
        const isSelected = selectedNodes.has(node.node_id);
        
        return (
          <NodeRenderer
            key={node.node_id}
            node={{ ...node, selected: isSelected }}
            executionStatus={nodeStates[node.node_id]?.status || 'idle'}
            previewData={nodeStates[node.node_id]?.previewData}
            hasExecutionData={!!nodeExecutionData[node.node_id]}
            onSelect={onNodeSelect}
            onDelete={onNodeDelete}
            onDragStart={onNodeDragStart}
            onPortMouseDown={onPortMouseDown}
            onContextMenu={onNodeContextMenu}
          />
        );
      })}
    </>
  );
}


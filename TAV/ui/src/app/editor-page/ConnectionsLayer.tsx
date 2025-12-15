import React from 'react';

interface Connection {
  id: string;
  source: {
    node_id: string;
    port_id: string;
  };
  target: {
    node_id: string;
    port_id: string;
  };
}

interface WorkflowNode {
  node_id: string;  // Changed from 'id' to match backend
  position: { x: number; y: number };
  inputs: Array<{ id: string; label: string; type: string }>;
  outputs: Array<{ id: string; label: string; type: string }>;
  flipped?: boolean; // Whether ports are flipped
}

interface ConnectionsLayerProps {
  connections: Connection[];
  nodes: WorkflowNode[];
  tempConnection?: {
    fromNode: string;
    fromPort: string;
    fromType: 'input' | 'output';
    currentX: number;
    currentY: number;
  } | null;
  onConnectionClick?: (connectionId: string) => void;
}

export function ConnectionsLayer({
  connections,
  nodes,
  tempConnection,
  onConnectionClick,
}: ConnectionsLayerProps) {
  
  const getPortPosition = (
    nodeId: string,
    portId: string,
    portType: 'input' | 'output'
  ): { x: number; y: number } | null => {
    // Always use calculated position for consistency
    const node = nodes.find(n => n.node_id === nodeId);
    if (!node) return null;

    const ports = portType === 'input' ? node.inputs : node.outputs;
    const portIndex = ports.findIndex(p => p.id === portId);
    if (portIndex === -1) return null;

    // Get actual node width from DOM
    let nodeWidth = 240; // Default fallback
    const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
    if (nodeElement) {
      const computedStyle = window.getComputedStyle(nodeElement);
      nodeWidth = parseFloat(computedStyle.width) || 240;
    }

    // Node dimensions
    const nodeHeaderHeight = 41;
    const nodeBodyPaddingTop = 12;
    const portGap = 8;
    const portRowHeight = 16;
    const portHandleCenter = portRowHeight / 2;
    const finetuneOffset = 8;
    
    const portOffsetY = nodeHeaderHeight + nodeBodyPaddingTop + (portIndex * (portRowHeight + portGap)) + portHandleCenter + finetuneOffset;
    
    // Handle flipped nodes: inputs and outputs swap sides
    const isFlipped = (node as any).flipped;
    let portOffsetX;
    
    if (!isFlipped) {
      // Normal: inputs on left (0), outputs on right (nodeWidth)
      portOffsetX = portType === 'input' ? 0 : nodeWidth;
    } else {
      // Flipped: inputs on right (nodeWidth), outputs on left (0)
      portOffsetX = portType === 'input' ? nodeWidth : 0;
    }

    const x = node.position.x + portOffsetX;
    const y = node.position.y + portOffsetY;

    return { x, y };
  };

  const createPath = (
    x1: number,
    y1: number,
    x2: number,
    y2: number,
    sourceFlipped: boolean = false,
    targetFlipped: boolean = false
  ): string => {
    // Calculate horizontal distance between points
    const dx = x2 - x1;
    const dy = y2 - y1;
    
    // Determine port directions based on flip state
    // Normal output: goes right, Flipped output: goes left
    // Normal input: comes from left, Flipped input: comes from right
    const sourceGoesLeft = sourceFlipped; // Flipped output goes left
    const targetFromLeft = !targetFlipped; // Normal input receives from left
    
    // SPECIAL CASE: Both ports on LEFT side (flipped output + normal input)
    // This requires a loop curve instead of hook
    if (sourceGoesLeft && targetFromLeft && Math.abs(dy) > 30) {
      const horizontalOut = 500; // Moderate horizontal extension left
      const verticalPush = 100; // Moderate vertical curve
      const curveDirection = dy > 0 ? 1 : -1; // 1 = down, -1 = up
      
      // Curve goes: moderately left → curve down/up → back in
      const cp1x = x1 - horizontalOut;
      const cp1y = y1 + (verticalPush * curveDirection);
      
      const cp2x = x2 - horizontalOut;
      const cp2y = y2 - (verticalPush * curveDirection);
      
      return `M ${x1},${y1} C ${cp1x},${cp1y} ${cp2x},${cp2y} ${x2},${y2}`;
    }
    
    // Check if connection is going backwards (output to the right of input)
    const isBackwards = dx < 0;
    
    if (isBackwards || sourceGoesLeft) {
      // Create a fish hook shape for backwards connections or flipped outputs
      const hookDistance = 80; // How far to extend horizontally
      
      // Determine which direction to go initially
      const initialDirection = sourceGoesLeft ? -1 : 1; // -1 = left, 1 = right
      
      // Control points for clean hook shape without end curl
      // cp1: Go straight out from source (left if flipped, right if normal)
      const cp1x = x1 + (hookDistance * initialDirection);
      const cp1y = y1;
      
      // cp2: Curve down/up (depending on target position)
      const cp2x = x1 + (hookDistance * initialDirection);
      const cp2y = y2;
      
      // Simple cubic bezier: straight out, curve around, straight in
      return `M ${x1},${y1} C ${cp1x},${cp1y} ${cp2x},${cp2y} ${x2},${y2}`;
    } else {
      // Normal forward connection - use smooth S-curve bezier
      // Normal forward connection - use smooth bezier curve
      // Calculate adaptive offset based on distance
      const distance = Math.abs(dx);
      const offset = Math.min(distance / 2, 150); // Cap at 150px
      
      const cp1x = x1 + offset;
      const cp1y = y1;
      const cp2x = x2 - offset;
      const cp2y = y2;
      
      return `M ${x1},${y1} C ${cp1x},${cp1y} ${cp2x},${cp2y} ${x2},${y2}`;
    }
  };

  const getConnectionColor = (portType?: string): string => {
    const colors: Record<string, string> = {
      // Core types
      signal: '#6366f1',       // indigo
      universal: '#9ca3af',    // gray
      
      // Multimodal types
      text: '#3b82f6',         // blue
      image: '#ec4899',        // pink
      audio: '#8b5cf6',        // purple
      video: '#f97316',        // orange
      document: '#06b6d4',     // cyan
      
      // Special types
      tools: '#84cc16',        // lime
      memory: '#eab308',       // yellow
      ui: '#f43f5e',           // rose
      
      // Legacy types
      number: '#10b981',       // green
      boolean: '#f59e0b',      // amber
      object: '#8b5cf6',       // purple
      array: '#ec4899',        // pink
      any: '#6b7280',          // gray
    };
    return colors[portType || 'universal'] || '#6b7280';
  };

  return (
    <svg
      className="pointer-events-none"
      style={{ 
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 5, // Slightly above normal nodes (nodes default z-index: 1), selected nodes keep z-index: 10
        overflow: 'visible',
      }}
    >
      <defs>
        {/* Arrow markers for different connection types */}
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="10"
          refX="8"
          refY="3"
          orient="auto"
          markerUnits="strokeWidth"
        >
          <path d="M0,0 L0,6 L9,3 z" fill="currentColor" />
        </marker>
      </defs>

      {/* Render existing connections */}
      {connections.map((conn) => {
        const sourcePos = getPortPosition(conn.source.node_id, conn.source.port_id, 'output');
        const targetPos = getPortPosition(conn.target.node_id, conn.target.port_id, 'input');
        
        if (!sourcePos || !targetPos) {
          return null;
        }

        // Get source and target nodes to check flip state
        const sourceNode = nodes.find(n => n.node_id === conn.source.node_id);
        const targetNode = nodes.find(n => n.node_id === conn.target.node_id);
        
        const path = createPath(
          sourcePos.x, 
          sourcePos.y, 
          targetPos.x, 
          targetPos.y,
          sourceNode?.flipped || false,
          targetNode?.flipped || false
        );

        // Get port type from source node
        const sourcePort = sourceNode?.outputs.find(p => p.id === conn.source.port_id);
        const portType = sourcePort?.type || 'universal';
        const color = getConnectionColor(portType);

        return (
          <g key={conn.id}>
            {/* Invisible thick path for easier clicking */}
            <path
              d={path}
              stroke="transparent"
              strokeWidth="16"
              fill="none"
              className="pointer-events-auto cursor-pointer"
              onClick={() => onConnectionClick?.(conn.id)}
            />
            {/* Visible connection line */}
            <path
              d={path}
              stroke={color}
              strokeWidth="2"
              fill="none"
              className="pointer-events-none connection-line"
              style={{ color }}
            />
          </g>
        );
      })}

      {/* Render temporary connection being drawn */}
      {tempConnection && (() => {
        const sourcePos = getPortPosition(
          tempConnection.fromNode,
          tempConnection.fromPort,
          tempConnection.fromType
        );
        
        if (!sourcePos) return null;

        const x1 = tempConnection.fromType === 'output' ? sourcePos.x : tempConnection.currentX;
        const y1 = tempConnection.fromType === 'output' ? sourcePos.y : tempConnection.currentY;
        const x2 = tempConnection.fromType === 'output' ? tempConnection.currentX : sourcePos.x;
        const y2 = tempConnection.fromType === 'output' ? tempConnection.currentY : sourcePos.y;

        // Get source node flip state for temporary connection
        const sourceNode = nodes.find(n => n.node_id === tempConnection.fromNode);
        const sourceFlipped = tempConnection.fromType === 'output' ? (sourceNode?.flipped || false) : false;
        const targetFlipped = tempConnection.fromType === 'input' ? (sourceNode?.flipped || false) : false;

        const path = createPath(x1, y1, x2, y2, sourceFlipped, targetFlipped);
        
        return (
          <path
            d={path}
            stroke="#6b7280"
            strokeWidth="2"
            strokeDasharray="5,5"
            fill="none"
            className="pointer-events-none temp-connection"
          />
        );
      })()}
    </svg>
  );
}


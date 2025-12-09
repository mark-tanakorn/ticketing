/**
 * Workflow Variable Utilities
 * 
 * Helper functions for working with shared space variables in workflows.
 */

/**
 * Sanitize node name to create a valid variable identifier.
 * Removes spaces, special chars, converts to snake_case.
 */
function sanitizeVariableName(name: string): string {
  return name
    .trim()
    .replace(/\s+/g, '_')           // Replace spaces with underscores
    .replace(/[^a-zA-Z0-9_]/g, '')  // Remove special characters
    .replace(/^[0-9]/, '_$&')       // Prepend underscore if starts with number
    .toLowerCase();
}

interface WorkflowNode {
  node_id: string;
  node_type: string;
  name: string;
  share_output_to_variables?: boolean;
  variable_name?: string;
  output_ports?: Array<{ name: string; type?: string }>;
}

interface WorkflowConnection {
  source_node_id?: string;
  target_node_id?: string;
  // Support both formats
  source?: { node_id: string; port_id: string };
  target?: { node_id: string; port_id: string };
}

interface AvailableVariable {
  nodeName: string;
  nodeId: string;
  uniqueKey: string; // For React keys to avoid duplicates
  fields: Array<{ name: string; type?: string }>;
}

/**
 * Get all available variables for a specific node.
 * Scans all predecessor nodes that have sharing enabled.
 * 
 * @param workflow - Current workflow with nodes and connections
 * @param currentNodeId - The node we're configuring
 * @param nodeDefinitions - Node type definitions with port info
 * @returns Array of available variables grouped by source node
 */
export function getAvailableVariables(
  nodes: WorkflowNode[],
  connections: WorkflowConnection[],
  currentNodeId: string,
  nodeDefinitions: any[]
): AvailableVariable[] {
  
  const availableVars: AvailableVariable[] = [];
  
  // Add system variables (always available)
  availableVars.push({
    nodeName: '🔧 System Variables',
    nodeId: 'system',
    uniqueKey: 'system-variables',
    fields: [
      { name: 'current_date', type: 'string' },
      { name: 'current_time', type: 'string' },
      { name: 'current_datetime', type: 'string' },
      { name: 'timestamp', type: 'string' },
    ],
  });
  
  // Find all predecessor nodes (nodes that come before current node in the graph)
  const predecessorIds = findPredecessorNodes(nodes, connections, currentNodeId);
  
  
  // Count occurrences of each node name across ALL sharing nodes in the workflow
  // This is important: backend assigns suffixes (_1, _2) based on ALL nodes with same name,
  // not just predecessors. So we need to match that behavior.
  const nameCount = new Map<string, number>();
  const nameToNodeIds = new Map<string, string[]>();
  
  for (const node of nodes) {
    if (node.share_output_to_variables) {
      const sanitizedName = sanitizeVariableName(node.name);
      nameCount.set(sanitizedName, (nameCount.get(sanitizedName) || 0) + 1);
      
      if (!nameToNodeIds.has(sanitizedName)) {
        nameToNodeIds.set(sanitizedName, []);
      }
      nameToNodeIds.get(sanitizedName)!.push(node.node_id);
    }
  }
  
  // Sort node IDs for each name group to match backend's deterministic ordering
  for (const [name, nodeIds] of nameToNodeIds.entries()) {
    nameToNodeIds.set(name, nodeIds.sort());
  }
  
  // For each predecessor
  for (const nodeId of predecessorIds) {
    const node = nodes.find(n => n.node_id === nodeId);
    
    
    if (!node || !node.share_output_to_variables) {
      continue; // Skip if node doesn't share outputs
    }
    
    // Get node definition to find output ports
    const nodeDef = nodeDefinitions.find(def => 
      def.node_type === node.node_type ||
      def.node_type.replace(/_/g, '') === node.node_type.replace(/_/g, '')
    );
    
    if (!nodeDef) {
      console.warn(`⚠️ Node definition not found for node type "${node.node_type}" (node ${nodeId})`);
      console.warn(`  Available node definitions:`, nodeDefinitions.length, nodeDefinitions.map(d => d.node_type));
      continue;
    }
    
    // Extract output port names as available fields
    const fields: Array<{ name: string; type?: string }> = [];
    
    // If node has output ports defined
    if (nodeDef.output_ports && Array.isArray(nodeDef.output_ports)) {
      for (const port of nodeDef.output_ports) {
        // Check if port has a schema with properties (detailed field info)
        if (port.schema && port.schema.properties) {
          // IMPORTANT: Backend flattens single "output" port dicts
          // So {"output": {"text": "..."}} becomes {"text": "..."}
          // We need to generate field paths that match backend's flattening behavior
          const willBeFlattenedByBackend = (port.name === 'output' && nodeDef.output_ports.length === 1);
          
          // Parse schema to extract nested fields
          for (const [propName, propDef] of Object.entries(port.schema.properties as Record<string, any>)) {
            // Generate field path based on whether backend will flatten
            const fieldPath = willBeFlattenedByBackend ? propName : `${port.name}.${propName}`;
            fields.push({ 
              name: fieldPath, 
              type: propDef.type || 'unknown'
            });
            
            // For arrays, also add indexed access hints for first few items
            if (propDef.type === 'array' && propDef.items?.properties) {
              for (let i = 0; i < 3; i++) {
                for (const [itemProp, itemPropDef] of Object.entries(propDef.items.properties as Record<string, any>)) {
                  fields.push({
                    name: `${fieldPath}.${i}.${itemProp}`,
                    type: itemPropDef.type || 'unknown'
                  });
                }
              }
            }
          }
        } else {
          // No schema - use generic approach
          // If it's a single "output" port with universal type,
          // we know backend will flatten it, so we can't predict fields
          // Show generic field hints (without "output." prefix since it gets flattened)
          if (port.name === 'output' && nodeDef.output_ports.length === 1) {
            // Backend flattens, so these are top-level fields
            fields.push({ name: 'data', type: 'unknown' });
            fields.push({ name: 'result', type: 'unknown' });
            fields.push({ name: 'value', type: 'unknown' });
            fields.push({ name: 'text', type: 'unknown' });
          } else {
            fields.push({ name: port.name, type: port.type });
          }
        }
      }
    }
    
    // If no fields detected, add generic ones
    if (fields.length === 0) {
      fields.push({ name: 'output', type: 'universal' });
    }
    
    // Determine display name with duplicate indicator
    const baseName = node.name;
    const sanitizedName = sanitizeVariableName(node.name);
    const count = nameCount.get(sanitizedName) || 1;
    let displayName = baseName;
    
    // Get the variable name for building paths (what backend expects)
    let variableName = node.variable_name || sanitizedName;
    
    if (node.variable_name) {
      // User set a custom variable name - show it in the display name
      // Format: "Node Name → custom_var_name" so user can see both
      displayName = `${baseName} → ${node.variable_name}`;
    } else if (count > 1) {
      // Multiple nodes with same name - find this node's position in sorted order
      const sortedNodeIds = nameToNodeIds.get(sanitizedName) || [];
      const occurrence = sortedNodeIds.indexOf(node.node_id) + 1; // 1-based index
      
      displayName = `${baseName} (${occurrence})`;
      
      // Also append suffix to variable name to make it unique
      variableName = `${variableName}_${occurrence}`;
    }
    
    availableVars.push({
      nodeName: displayName,
      nodeId: variableName,  // Use variable name for paths (backend compatibility)
      uniqueKey: node.node_id,  // Use unique node_id for React keys
      fields,
    });
  }
  
  return availableVars;
}

/**
 * Find all nodes that are predecessors of the target node.
 * Uses BFS to traverse the graph backwards from target node.
 */
function findPredecessorNodes(
  nodes: WorkflowNode[],
  connections: WorkflowConnection[],
  targetNodeId: string
): string[] {
  const predecessors = new Set<string>();
  const queue: string[] = [targetNodeId];
  const visited = new Set<string>([targetNodeId]);
  
  
  while (queue.length > 0) {
    const currentId = queue.shift()!;
    
    // Find all connections pointing TO current node
    // Support both flat and nested connection formats
    const incomingConnections = connections.filter(conn => {
      const targetId = conn.target_node_id || conn.target?.node_id;
      return targetId === currentId;
    });
    
    
    for (const conn of incomingConnections) {
      const sourceId = conn.source_node_id || conn.source?.node_id;
      
      if (!sourceId) {
        console.warn('⚠️ Connection has no source node ID:', conn);
        continue;
      }
      
      
      if (!visited.has(sourceId)) {
        visited.add(sourceId);
        predecessors.add(sourceId);
        queue.push(sourceId);
      }
    }
  }
  
  return Array.from(predecessors);
}

/**
 * Check if a field config should use variable input.
 * 
 * @param field - Config field definition
 * @returns true if field should support variables
 */
export function shouldUseVariableInput(field: any): boolean {
  // 1. Explicitly enabled via allow_template flag (takes precedence)
  if (field.allow_template === true) {
    return true;
  }
  
  // 2. Explicitly disabled via allow_template flag (takes precedence)
  if (field.allow_template === false) {
    return false;
  }
  
  // 3. Type-based explicit opt-in
  if (field.type === 'variable_or_text') {
    return true;
  }
  
  // 4. Auto-detection based on widget type
  //    ALLOWLIST: Only simple text inputs should support variables
  //    Everything else (dropdowns, pickers, etc.) has specialized UI
  const allowedWidgets = [
    'text',            // Simple text input
    'textarea',        // Multi-line text
    'password',        // Password input (can use variables for dynamic passwords)
    // That's it! Everything else has its own specialized UI
  ];
  
  // If widget is specified and NOT in allowlist, block it
  if (field.widget && !allowedWidgets.includes(field.widget)) {
    return false;
  }
  
  // 5. String fields with allowed widgets (or no widget) can use variables
  //    This includes: text, textarea
  if (field.type === 'string') {
    return true;
  }
  
  return false;
}

/**
 * Parse variable paths from a template string.
 * 
 * @param template - Template string like "Hello {{var1}} and {{var2}}"
 * @returns Array of variable paths found
 */
export function extractVariablePaths(template: string): string[] {
  const regex = /\{\{([^}]+)\}\}/g;
  const paths: string[] = [];
  let match;
  
  while ((match = regex.exec(template)) !== null) {
    paths.push(match[1].trim());
  }
  
  return paths;
}

/**
 * Validate that all variable references in a config exist.
 * 
 * @param configValue - Config value to validate
 * @param availableVars - Available variables in workflow
 * @returns Array of missing variable paths
 */
export function validateVariableReferences(
  configValue: any,
  availableVars: AvailableVariable[]
): string[] {
  const missing: string[] = [];
  
  // Build set of available paths
  const availablePaths = new Set<string>();
  for (const node of availableVars) {
    for (const field of node.fields) {
      availablePaths.add(`${node.nodeId}.${field.name}`);
    }
  }
  
  // Check based on config type
  if (typeof configValue === 'object' && configValue !== null) {
    if (configValue.source === 'variable' && configValue.variable_path) {
      if (!availablePaths.has(configValue.variable_path)) {
        missing.push(configValue.variable_path);
      }
    } else if (configValue.source === 'template' && configValue.template) {
      const paths = extractVariablePaths(configValue.template);
      for (const path of paths) {
        if (!availablePaths.has(path)) {
          missing.push(path);
        }
      }
    }
  } else if (typeof configValue === 'string') {
    const paths = extractVariablePaths(configValue);
    for (const path of paths) {
      if (!availablePaths.has(path)) {
        missing.push(path);
      }
    }
  }
  
  return missing;
}


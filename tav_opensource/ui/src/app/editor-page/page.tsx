"use client";

import { useEffect, useRef, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { createPortal } from "react-dom";
import {
  createWorkflow,
  updateWorkflow,
  getWorkflow,
  listWorkflows,
  fetchNodeDefinitions,
} from "@/lib/editor";
import { NodesLayer } from "./NodeRenderer";
import { ConnectionsLayer } from "./ConnectionsLayer";
import { ConfigPanel } from "./ConfigPanel";
import { useCanvasPanZoom } from "./hooks/useCanvasPanZoom";
import { useWorkflowExecution } from "./hooks/useWorkflowExecution";
import { useGridSettings } from "./hooks/useGridSettings";
import { useUndoableState } from "@/lib/hooks/useUndoableState";
import { groupNodesByCategory, getNodeIcon, getDummyCategories } from "./utils/nodeUtils";
import "./nodes.css";

function WorkflowEditorInner() {
  const viewportRef = useRef<HTMLDivElement>(null);
  const logBodyRef = useRef<HTMLDivElement>(null);
  const logPanelRef = useRef<HTMLDivElement>(null);
  
  // URL params for workflow ID
  const searchParams = useSearchParams();
  const router = useRouter();
  
  // UI State
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
  const [isLogCollapsed, setIsLogCollapsed] = useState(false);
  const [logHeight, setLogHeight] = useState(200);
  const [searchTerm, setSearchTerm] = useState("");
  const [isResizing, setIsResizing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());
  // Normalize category keys for stable comparisons (trim + lowercase)
  const normCategory = (s: string) => (s || '').toString().trim().toLowerCase();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [showMinimap, setShowMinimap] = useState(false);
  const [minimapViewport, setMinimapViewport] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const [isDraggingMinimap, setIsDraggingMinimap] = useState(false);

  // Workflow State
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [workflowName, setWorkflowName] = useState("Untitled Workflow");
  const [workflowDescription, setWorkflowDescription] = useState("");
  const [nodes, setNodes] = useState<any[]>([]);
  const [connections, setConnections] = useState<any[]>([]);
  const [isDirty, setIsDirty] = useState(false);
  
  // Node definitions from backend
  const [nodeDefinitions, setNodeDefinitions] = useState<any[]>([]);
  
  // Canvas rendering state (using node_id and node_type to match backend)
  const [canvasNodes, setCanvasNodes] = useState<any[]>([]);
  const [canvasObjects, setCanvasObjects] = useState<any[]>([]); // Groups and text annotations
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());
  const [selectedObject, setSelectedObject] = useState<string | null>(null); // Selected group/text
  
  // Clipboard for copy/paste (stores deep-cloned nodes + internal connections)
  const clipboardRef = useRef<{ nodes: any[]; connections: any[] } | null>(null);
  const pasteOffsetRef = useRef(0); // increases on repeated pastes to offset placement
  const [editingText, setEditingText] = useState<string | null>(null); // ID of text being edited
  const [resizingGroup, setResizingGroup] = useState<{ id: string; handle: string; startX: number; startY: number; startSize: { width: number; height: number }; startPos: { x: number; y: number } } | null>(null);
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isDraggingNode, setIsDraggingNode] = useState(false);
  const [isDraggingGroup, setIsDraggingGroup] = useState(false);
  const [isDraggingObject, setIsDraggingObject] = useState(false); // Dragging group/text
  const [groupDragStart, setGroupDragStart] = useState<{ x: number; y: number } | null>(null);
  const [groupDragOffsets, setGroupDragOffsets] = useState<Map<string, { x: number; y: number }>>(new Map());
  const [selectionBox, setSelectionBox] = useState<{
    startX: number;
    startY: number;
    currentX: number;
    currentY: number;
  } | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);
  const [nodeContextMenu, setNodeContextMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const [tempConnection, setTempConnection] = useState<{
    fromNode: string;
    fromPort: string;
    fromType: 'input' | 'output';
    currentX: number;
    currentY: number;
  } | null>(null);
  
  // Track sidebar node placement for staircase effect
  const [sidebarNodeCount, setSidebarNodeCount] = useState(0);
  const prevViewportScroll = useRef({ left: 0, top: 0 });

  // Node execution states (node_id -> status)
  type NodeStatus = 'idle' | 'pending' | 'executing' | 'completed' | 'failed';
  interface NodeState { 
    status: NodeStatus; 
    error?: string; 
    previewData?: any;  // Execution result data for preview (text, images, etc.)
  }
  const [nodeStates, setNodeStates] = useState<Record<string, NodeState>>({});
  const [nodeExecutionData, setNodeExecutionData] = useState<Record<string, any>>({});
  
  // Helper to update node state
  const updateNodeState = (nodeId: string, status: NodeStatus, error?: string, previewData?: any, fullExecutionData?: any) => {
    setNodeStates(prev => {
      const newStates = {
        ...prev,
        [nodeId]: { status, error, previewData }
      };
      return newStates;
    });
    
    // Store full execution data if provided
    if (fullExecutionData) {
      setNodeExecutionData(prev => ({
        ...prev,
        [nodeId]: fullExecutionData
      }));
    }
  };
  
  // Helper to reset all node states
  const resetAllNodeStates = () => {
    // Instead of wiping all states, preserve preview data for output nodes
    const resetStates: Record<string, NodeState> = {};
    canvasNodes.forEach(node => {
      const oldState = nodeStates[node.node_id];
      const shouldPreservePreview = node.category === 'output' || node.node_type?.includes('display');
      
      if (shouldPreservePreview && oldState?.previewData) {
        // Keep preview data but remove status (back to idle)
        resetStates[node.node_id] = { 
          status: 'idle',
          previewData: oldState.previewData 
        };
      } else if (oldState?.status === 'failed') {
        // Reset failed nodes to idle explicitly
        resetStates[node.node_id] = { 
          status: 'idle'
        };
      }
      // Other nodes just get cleared (no entry = idle)
    });
    setNodeStates(resetStates);
  };
  
  // Helper to set all nodes to pending state
  const setAllNodesPending = () => {
    const pendingStates: Record<string, NodeState> = {};
    canvasNodes.forEach(node => {
      // Preserve preview data for output/display nodes
      const oldState = nodeStates[node.node_id];
      const shouldPreservePreview = node.category === 'output' || node.node_type?.includes('display');
      
      pendingStates[node.node_id] = { 
        status: 'pending',
        // Keep previous preview data if this is an output/display node
        ...(shouldPreservePreview && oldState?.previewData ? { previewData: oldState.previewData } : {})
      };
    });
    setNodeStates(pendingStates);
  };
  
  // Modals & Data
  const [showLoadModal, setShowLoadModal] = useState(false);
  const [showSaveAsModal, setShowSaveAsModal] = useState(false);
  const [showLoadFromFileModal, setShowLoadFromFileModal] = useState(false);
  const [showSaveOptionsModal, setShowSaveOptionsModal] = useState(false);
  const [showLoadOptionsModal, setShowLoadOptionsModal] = useState(false);
  const [saveMode, setSaveMode] = useState<'save' | 'save_as' | 'save_copy'>('save');
  const [availableWorkflows, setAvailableWorkflows] = useState<any[]>([]);
  const [nodeCategories, setNodeCategories] = useState<any[]>([]);
  const [confirmClear, setConfirmClear] = useState(false);
  const clearButtonRef = useRef<HTMLButtonElement | null>(null);

  // Custom hooks
  const gridSettings = useGridSettings();
  const canvasPanZoom = useCanvasPanZoom(viewportRef, {
    gridSize: gridSettings.gridSize,
    gridOpacity: gridSettings.gridOpacity,
    enableGrid: gridSettings.enableGrid
  }, (scale) => {
    // Update zoom level when canvas scale changes (from wheel or buttons)
    setZoomLevel(Math.round(scale * 100));
  });
  const execution = useWorkflowExecution(workflowId, addLog, updateNodeState, resetAllNodeStates, setAllNodesPending);

  // Undo / redo support (patch-based via immer)
  const deepClone = (obj: any) => typeof structuredClone === 'function' ? structuredClone(obj) : JSON.parse(JSON.stringify(obj));

  const getSnapshot = () => ({
    canvasNodes: deepClone(canvasNodes),
    connections: deepClone(connections),
    canvasObjects: deepClone(canvasObjects),
    selectedNode,
  });

  const { present, pushProducer, pushSnapshot, replace: replaceSnapshot, undo, redo, canUndo, canRedo } = useUndoableState(getSnapshot(), 200);

  // Track whether we're in an undo/redo operation
  const isUndoRedoOperation = useRef(false);

  // Keep UI in sync with present (ensures UI updates when undo/redo happen)
  useEffect(() => {
    const p = present as any;
    if (!p) return;
    setCanvasNodes(p.canvasNodes || []);
    setConnections(p.connections || []);
    setCanvasObjects(p.canvasObjects || []);
    // Only reset selectedNode during undo/redo, not during regular updates
    if (isUndoRedoOperation.current) {
      setSelectedNode(p.selectedNode ?? null);
      isUndoRedoOperation.current = false;
    }
  }, [present]);

  // Initialize history on mount
  useEffect(() => {
    replaceSnapshot(getSnapshot());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle log panel resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !logPanelRef.current) return;
      const rect = logPanelRef.current.getBoundingClientRect();
      const newHeight = rect.bottom - e.clientY;
      const minHeight = 32;
      const maxHeight = window.innerHeight * 0.6;
      const constrainedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
      setLogHeight(constrainedHeight);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    if (isResizing) {
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "ns-resize";
      document.body.style.userSelect = "none";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  // Load nodes on mount
  useEffect(() => {
    loadNodes();
  }, []);
  
  // Load workflow from URL if workflow ID is present
  useEffect(() => {
    const urlWorkflowId = searchParams.get('workflow');
    if (urlWorkflowId && urlWorkflowId !== workflowId) {
      loadWorkflowById(urlWorkflowId);
    }
  }, [searchParams]);

  async function loadNodes() {
    try {
      const response = await fetchNodeDefinitions();

      
      const categories = groupNodesByCategory(response.nodes || []);
      setNodeCategories(categories);
      setNodeDefinitions(response.nodes || []); // Store all node definitions
      addLog(`✅ Loaded ${response.nodes?.length || 0} nodes from backend`);
    } catch (error) {
      console.error('Failed to load nodes:', error);
      addLog(`❌ Failed to load nodes: ${error}`);
      setNodeCategories(getDummyCategories());
    }
  }
  
  // ==================== Workflow CRUD ====================
  
  // Helper function to generate UUID
  const generateUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  };
  
  // Helper to generate workflow data for saving
  const getWorkflowData = (id?: string) => {
    const workflowNodes = canvasNodes.map(node => ({
      node_id: node.node_id,
      node_type: node.node_type,
      name: node.name,
      category: node.category,
      position: node.position,
      input_ports: (node.inputs || []).map((port: any) => ({
        name: port.id,
        type: port.type,
        display_name: port.label,
        description: port.description || '',
        required: port.required !== false
      })),
      output_ports: (node.outputs || []).map((port: any) => ({
        name: port.id,
        type: port.type,
        display_name: port.label,
        description: port.description || '',
        required: port.required !== false
      })),
      config: node.config || {},
      status: node.status || 'idle',
      icon: node.icon,
      share_output_to_variables: node.share_output_to_variables || false,
      variable_name: node.variable_name || undefined,
      flipped: node.flipped || false,
    }));
    
    const workflowConnections = connections.map(conn => ({
      connection_id: conn.connection_id || conn.id,
      source_node_id: conn.source.node_id,
      source_port: conn.source.port_id,
      target_node_id: conn.target.node_id,
      target_port: conn.target.port_id,
    }));
    
    return {
      id: id || workflowId || generateUUID(),
      name: workflowName,
      description: workflowDescription,
      nodes: workflowNodes,
      connections: workflowConnections,
      canvas_objects: canvasObjects || [] // Include canvas objects
    };
  };
  
  // Download workflow as JSON file
  const handleDownloadJSON = () => {
    const data = getWorkflowData();
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    addLog(`📥 Downloaded workflow as JSON: ${a.download}`);
  };
  
  // Load workflow from JSON file
  const handleLoadFromFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target?.result as string);
        loadWorkflowFromData(json);
        setShowLoadFromFileModal(false);
        addLog(`📤 Loaded workflow from file: ${file.name}`);
      } catch (error) {
        addLog(`❌ Failed to parse JSON file: ${error}`);
        alert('Failed to parse JSON file. Please ensure it\'s a valid workflow file.');
      }
    };
    reader.readAsText(file);
  };
  
  // Load workflow from data object
  const loadWorkflowFromData = (workflow: any) => {
    // When loading from file, we should treat it as a new draft but preserve the ID
    // until the user saves it. However, if we want to run it, we need an ID.
    // Let's generate a new ID if one isn't present, or use the imported one.
    // Important: We mark it as dirty so auto-save will pick it up if they run it.
    
    // Check if we should generate a new ID to avoid collisions unless it's a direct load
    // For now, trust the ID from the file, but maybe we should clear it if we want to force "Save As"?
    // The user said: "When I import a json ... I need to save as first".
    // This implies the imported JSON might have an ID but it's not "saved" in the backend yet.
    
    setWorkflowId(workflow.id); // This ID might not exist in backend yet!
    setWorkflowName(workflow.name);
    setWorkflowDescription(workflow.description || "");
    setNodes(workflow.nodes);
    
    const convertedConnections = workflow.connections.map((conn: any) => ({
      id: conn.connection_id || conn.id,
      connection_id: conn.connection_id || conn.id,
      source: {
        node_id: conn.source_node_id,
        port_id: conn.source_port
      },
      target: {
        node_id: conn.target_node_id,
        port_id: conn.target_port
      }
    }));
    setConnections(convertedConnections);
    
    const canvas = workflow.nodes.map((node: any) => ({
      node_id: node.node_id,
      node_type: node.node_type,
      name: node.name || node.node_type,
      category: node.category || 'default',
      position: node.position || { x: 100, y: 100 },
      inputs: (node.input_ports || [])
        .filter((port: any) => port && port.name)
        .map((port: any) => ({
          id: port.name,
          label: port.display_name || port.name,
          type: port.type || 'universal',
          description: port.description || '',
          required: port.required !== false
        })),
      outputs: (node.output_ports || [])
        .filter((port: any) => port && port.name)
        .map((port: any) => ({
          id: port.name,
          label: port.display_name || port.name,
          type: port.type || 'universal',
          description: port.description || '',
          required: port.required !== false
        })),
      config: node.config || {},
      status: 'idle',
      icon: node.icon,
      share_output_to_variables: node.share_output_to_variables || false,
      variable_name: node.variable_name || undefined,
      flipped: node.flipped || false
    }));
    setCanvasNodes(canvas);
    
    // Load canvas objects (groups and text annotations)
    setCanvasObjects(workflow.canvas_objects || []);
    
    // Mark as dirty so it gets saved on next run or auto-save
    // If we mark it as dirty, the auto-save effect will kick in after 1s and save it to backend.
    // This solves the "I need to save as first" problem.
    setIsDirty(true);
    setSidebarNodeCount(0);
  };
  
  // Handle "Save As" with name/description prompt
  const handleSaveAs = () => {
    setSaveMode('save_as');
    setShowSaveAsModal(true);
  };
  
  // Handle "Save a Copy" with auto-incremented name
  const handleSaveCopy = async () => {
    try {
      // Find an available name with (N) suffix
      let copyNumber = 1;
      let newName = `${workflowName} (${copyNumber})`;
      
      // Check if name exists
      const workflows = await listWorkflows();
      const existingNames = new Set(workflows.map((w: any) => w.name));
      
      while (existingNames.has(newName)) {
        copyNumber++;
        newName = `${workflowName} (${copyNumber})`;
      }
      
      const newId = generateUUID();
      const workflowData = getWorkflowData(newId);
      workflowData.name = newName;
      
      addLog(`Saving copy: ${newName}...`);
      
      const created = await createWorkflow(workflowData);
      setWorkflowId(created.id);
      setWorkflowName(newName);
      
      // Update URL with new workflow ID
      router.push(`/editor-page?workflow=${created.id}`);
      
      setIsDirty(false);
      addLog(`✅ Created copy: ${newName}`);
    } catch (error) {
      addLog(`❌ Save copy failed: ${error}`);
      console.error('Save copy error:', error);
    }
  };
  
  // Confirm and execute save from modal
  const confirmSaveAs = async (newName: string, newDescription: string) => {
    try {
      const newId = generateUUID();
      const workflowData = getWorkflowData(newId);
      workflowData.name = newName;
      workflowData.description = newDescription;
      
      addLog(`Saving as: ${newName}...`);
      
      const created = await createWorkflow(workflowData);
      setWorkflowId(created.id);
      setWorkflowName(newName);
      setWorkflowDescription(newDescription);
      
      // Update URL with new workflow ID
      router.push(`/editor-page?workflow=${created.id}`);
      
      setIsDirty(false);
      setShowSaveAsModal(false);
      addLog(`✅ Saved as: ${newName}`);
    } catch (error) {
      addLog(`❌ Save as failed: ${error}`);
      console.error('Save as error:', error);
    }
  };
  
  async function handleSave(isAutoSave = false) {
    try {
      if (!isAutoSave) {
        addLog(`Saving workflow: ${workflowName}...`);
      }
      
      const workflowData = getWorkflowData(workflowId || undefined);
      
      console.log('Saving workflow:', workflowData.id);
      
      if (workflowId) {
        // Update existing workflow
        await updateWorkflow(workflowId, workflowData);
        
        // Update URL with workflow ID (in case it was loaded without URL parameter)
        router.push(`/editor-page?workflow=${workflowId}`);
        
        if (!isAutoSave) {
          addLog(`✅ Updated: ${workflowName}`);
        }
      } else {
        // Create new workflow
        const created = await createWorkflow(workflowData);
        setWorkflowId(created.id);
        
        // Update URL with workflow ID
        router.push(`/editor-page?workflow=${created.id}`);
        
        if (!isAutoSave) {
          addLog(`✅ Created: ${workflowName} (${created.id})`);
        }
      }
      setIsDirty(false);
    } catch (error) {
      if (!isAutoSave) {
        addLog(`❌ Save failed: ${error}`);
      }
      console.error('Save error:', error);
    }
  }

  // Auto-save effect
  useEffect(() => {
    if (isDirty) {
      const timer = setTimeout(() => {
        handleSave(true);
      }, 1000);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDirty, canvasNodes, connections, workflowName, workflowDescription, workflowId, canvasObjects]);
  
  async function handleLoad() {
    try {
      const workflows = await listWorkflows();
      setAvailableWorkflows(workflows);
      setShowLoadModal(true);
      addLog(`📂 Found ${workflows.length} workflows`);
    } catch (error) {
      addLog(`❌ Load failed: ${error}`);
    }
  }
  
  async function loadWorkflowById(id: string) {
    try {
      const workflow = await getWorkflow(id);
      setWorkflowId(workflow.id);
      setWorkflowName(workflow.name);
      setWorkflowDescription(workflow.description || "");
      setNodes(workflow.nodes);
      
      // Convert connections from backend format to frontend format
      const convertedConnections = workflow.connections.map((conn: any) => ({
        id: conn.connection_id || conn.id,
        connection_id: conn.connection_id || conn.id,
        source: {
          node_id: conn.source_node_id,
          port_id: conn.source_port
        },
        target: {
          node_id: conn.target_node_id,
          port_id: conn.target_port
        }
      }));
      setConnections(convertedConnections);
      
      // Backend returns node_id and node_type - use them as-is
      const canvas = workflow.nodes.map((node: any) => ({
        node_id: node.node_id,
        node_type: node.node_type,
        name: node.name || node.node_type,
        category: node.category || 'default',
        position: node.position || { x: 100, y: 100 },
        // Convert backend port format to frontend format
        inputs: (node.input_ports || [])
          .filter((port: any) => port && port.name) // Filter out invalid ports
          .map((port: any) => ({
            id: port.name,                     // Backend 'name' → Frontend 'id'
            label: port.display_name || port.name, // Backend 'display_name' → Frontend 'label'
            type: port.type || 'universal',
            description: port.description || '',
            required: port.required !== false
          })),
        outputs: (node.output_ports || [])
          .filter((port: any) => port && port.name) // Filter out invalid ports
          .map((port: any) => ({
            id: port.name,                     // Backend 'name' → Frontend 'id'
            label: port.display_name || port.name, // Backend 'display_name' → Frontend 'label'
            type: port.type || 'universal',
            description: port.description || '',
            required: port.required !== false
          })),
        config: node.config || {},
        status: 'idle',
        icon: node.icon,
        share_output_to_variables: node.share_output_to_variables || false,  // ✅ Load sharing setting
        variable_name: node.variable_name || undefined,  // ✅ Load custom variable name
        flipped: node.flipped || false  // ✅ Load flipped state
      }));
      
      setIsDirty(false);
      setShowLoadModal(false);
      setSidebarNodeCount(0); // Reset staircase counter for loaded workflows
      
      // Update URL with workflow ID
      router.push(`/editor-page?workflow=${workflow.id}`);
      
      setCanvasNodes(canvas);
      setCanvasObjects(workflow.canvas_objects || []); // Load canvas objects
      // Replace undo history with this loaded workflow snapshot
      replaceSnapshot({ canvasNodes: canvas, connections: convertedConnections, canvasObjects: workflow.canvas_objects || [], selectedNode: null });
      addLog(`✅ Loaded: ${workflow.name}`);
    } catch (error) {
      addLog(`❌ Failed to load: ${error}`);
    }
  }
  
  function handleClear(allowUndo: boolean = false) {
    setWorkflowId(null);
    setWorkflowName('Untitled Workflow');
    setWorkflowDescription('');
    setNodes([]);
    if (allowUndo) {
      // Use a producer to record the clear action so it can be undone
      pushProducer((draft: any) => {
        draft.canvasNodes = [];
        draft.connections = [];
        draft.canvasObjects = [];
        draft.selectedNode = null;
      });
      // Remove focus from Clear button so subsequent Ctrl+Z triggers undo rather than another clear
      if (clearButtonRef.current) clearButtonRef.current.blur();
    } else {
      setConnections([]);
      setCanvasNodes([]);
      setCanvasObjects([]);
    }
    setSidebarNodeCount(0); // Reset staircase counter
    setIsDirty(false);
    setLogs([]);
    
    // Clear URL by navigating to editor page without workflow parameter
    router.push('/editor-page');
    
    addLog('🗑️ Cleared');
    // If we didn't allow undo, replace the snapshot (reset history). Otherwise, we've pushed a patch and clear will be undoable.
    if (!allowUndo) {
      replaceSnapshot({ canvasNodes: [], connections: [], canvasObjects: [], selectedNode: null });
    }
  }
  
  const handleClearClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirmClear) {
      handleClear(true);
      setConfirmClear(false);
    } else {
      setConfirmClear(true);
    }
  };
  
  // ==================== Canvas Node Interaction ====================
  
  // ==================== Canvas Objects (Groups & Text) ====================
  
  function createGroup(x: number, y: number) {
    const newGroup = {
      id: generateUUID(),
      type: 'group',
      position: { x, y },
      size: { width: 400, height: 300 },
      color: '#fef3c7', // Light yellow
      title: 'New Group',
      zIndex: -1
    };
    
    pushProducer((draft: any) => {
      draft.canvasObjects = [...(draft.canvasObjects || []), newGroup];
    });
    setIsDirty(true);
    addLog(`➕ Added group: ${newGroup.title}`);
    return newGroup.id;
  }
  
  function createTextAnnotation(x: number, y: number) {
    const newText = {
      id: generateUUID(),
      type: 'text',
      position: { x, y },
      content: 'Type here...',
      fontSize: 16,
      color: '#374151',
      zIndex: 0
    };
    
    pushProducer((draft: any) => {
      draft.canvasObjects = [...(draft.canvasObjects || []), newText];
    });
    setIsDirty(true);
    addLog(`➕ Added text annotation`);
    
    // Automatically start editing the new text
    setTimeout(() => {
      setEditingText(newText.id);
      setSelectedObject(newText.id);
    }, 0);
    
    return newText.id;
  }
  
  function deleteCanvasObject(objectId: string) {
    const obj = canvasObjects.find(o => o.id === objectId);
    pushProducer((draft: any) => {
      draft.canvasObjects = (draft.canvasObjects || []).filter((o: any) => o.id !== objectId);
    });
    setIsDirty(true);
    addLog(`🗑️ Deleted ${obj?.type || 'object'}`);
    if (selectedObject === objectId) {
      setSelectedObject(null);
    }
  }
  
  function updateCanvasObject(objectId: string, updates: any) {
    pushProducer((draft: any) => {
      draft.canvasObjects = (draft.canvasObjects || []).map((o: any) =>
        o.id === objectId ? { ...o, ...updates } : o
      );
    });
    setIsDirty(true);
  }
  
  function handleObjectDragStart(objectId: string, e: React.MouseEvent) {
    e.stopPropagation();
    setIsDraggingObject(true);
    setSelectedObject(objectId);
    
    const obj = canvasObjects.find(o => o.id === objectId);
    if (obj && viewportRef.current) {
      const scale = canvasPanZoom.scale || 1;
      const canvasRect = viewportRef.current.getBoundingClientRect();
      const scrollLeft = viewportRef.current.scrollLeft;
      const scrollTop = viewportRef.current.scrollTop;
      
      const canvasX = (e.clientX - canvasRect.left + scrollLeft) / scale;
      const canvasY = (e.clientY - canvasRect.top + scrollTop) / scale;
      
      setDragOffset({
        x: canvasX - obj.position.x,
        y: canvasY - obj.position.y
      });
    }
  }
  
  function handleObjectDrag(e: React.MouseEvent) {
    if (!isDraggingObject || !selectedObject || !viewportRef.current) return;
    
    const scale = canvasPanZoom.scale || 1;
    const canvasRect = viewportRef.current.getBoundingClientRect();
    const scrollLeft = viewportRef.current.scrollLeft;
    const scrollTop = viewportRef.current.scrollTop;
    
    const canvasX = (e.clientX - canvasRect.left + scrollLeft) / scale;
    const canvasY = (e.clientY - canvasRect.top + scrollTop) / scale;
    
    const x = canvasX - dragOffset.x;
    const y = canvasY - dragOffset.y;
    
    setCanvasObjects(prev => prev.map(o => 
      o.id === selectedObject ? { ...o, position: { x, y } } : o
    ));
    setIsDirty(true);
  }
  
  function handleObjectDragEnd() {
    if (isDraggingObject && selectedObject) {
      const obj = canvasObjects.find(o => o.id === selectedObject);
      if (obj) {
        pushProducer((draft: any) => {
          const dobj = (draft.canvasObjects || []).find((o: any) => o.id === selectedObject);
          if (dobj) dobj.position = { ...obj.position };
        });
      }
    }
    setIsDraggingObject(false);
  }
  
  // Group resizing
  function handleGroupResizeStart(groupId: string, handle: string, e: React.MouseEvent) {
    e.stopPropagation();
    const group = canvasObjects.find(o => o.id === groupId && o.type === 'group');
    if (!group || !viewportRef.current) return;
    
    const scale = canvasPanZoom.scale || 1;
    const canvasRect = viewportRef.current.getBoundingClientRect();
    const scrollLeft = viewportRef.current.scrollLeft;
    const scrollTop = viewportRef.current.scrollTop;
    
    const canvasX = (e.clientX - canvasRect.left + scrollLeft) / scale;
    const canvasY = (e.clientY - canvasRect.top + scrollTop) / scale;
    
    setResizingGroup({
      id: groupId,
      handle,
      startX: canvasX,
      startY: canvasY,
      startSize: { ...group.size },
      startPos: { ...group.position }
    });
  }
  
  function handleGroupResize(e: React.MouseEvent) {
    if (!resizingGroup || !viewportRef.current) return;
    
    const scale = canvasPanZoom.scale || 1;
    const canvasRect = viewportRef.current.getBoundingClientRect();
    const scrollLeft = viewportRef.current.scrollLeft;
    const scrollTop = viewportRef.current.scrollTop;
    
    const canvasX = (e.clientX - canvasRect.left + scrollLeft) / scale;
    const canvasY = (e.clientY - canvasRect.top + scrollTop) / scale;
    
    const deltaX = canvasX - resizingGroup.startX;
    const deltaY = canvasY - resizingGroup.startY;
    
    const handle = resizingGroup.handle;
    let newSize = { ...resizingGroup.startSize };
    let newPos = { ...resizingGroup.startPos };
    
    // Handle different resize directions
    if (handle.includes('e')) {
      newSize.width = Math.max(200, resizingGroup.startSize.width + deltaX);
    }
    if (handle.includes('w')) {
      const newWidth = Math.max(200, resizingGroup.startSize.width - deltaX);
      if (newWidth > 200) {
        newPos.x = resizingGroup.startPos.x + deltaX;
        newSize.width = newWidth;
      }
    }
    if (handle.includes('s')) {
      newSize.height = Math.max(150, resizingGroup.startSize.height + deltaY);
    }
    if (handle.includes('n')) {
      const newHeight = Math.max(150, resizingGroup.startSize.height - deltaY);
      if (newHeight > 150) {
        newPos.y = resizingGroup.startPos.y + deltaY;
        newSize.height = newHeight;
      }
    }
    
    setCanvasObjects(prev => prev.map(o => 
      o.id === resizingGroup.id ? { ...o, size: newSize, position: newPos } : o
    ));
  }
  
  function handleGroupResizeEnd() {
    if (resizingGroup) {
      const group = canvasObjects.find(o => o.id === resizingGroup.id);
      if (group) {
        pushProducer((draft: any) => {
          const dobj = (draft.canvasObjects || []).find((o: any) => o.id === resizingGroup.id);
          if (dobj) {
            dobj.size = { ...group.size };
            dobj.position = { ...group.position };
          }
        });
      }
    }
    setResizingGroup(null);
  }
  
  function addNodeToCanvas(
    nodeType: string, 
    nodeName: string, 
    category: string, 
    position: { x: number, y: number }, 
    icon?: string,
    inputPorts?: any[],
    outputPorts?: any[]
  ) {
    // Generate UUID matching backend format
    const generateUUID = () => {
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
      });
    };
    
    const newNode = {
      node_id: generateUUID(),  // Use node_id (backend format)
      node_type: nodeType,       // Use node_type (backend format)
      name: nodeName,
      category: category,
      position: position,
      // Convert API port format to UI format
      inputs: (inputPorts || []).map((port: any) => ({
        id: port.name,
        label: port.display_name || port.name,
        type: port.type,
        required: port.required || false,
      })),
      outputs: (outputPorts || []).map((port: any) => ({
        id: port.name,
        label: port.display_name || port.name,
        type: port.type,
      })),
      config: {},
      status: 'idle' as const,
      icon: icon
    };
    
    // Use pushProducer so the change is applied with patches and recorded
    pushProducer((draft: any) => {
      draft.canvasNodes = [...(draft.canvasNodes || []), newNode];
    });
    setIsDirty(true);
    addLog(`➕ Added: ${nodeName}`);
  }
  
  function handleNodeSelect(nodeId: string, event?: React.MouseEvent) {
    // Only open config if we weren't just dragging
    if (!isDraggingNode && !isDraggingGroup) {
      // Check if Ctrl/Cmd is held for multi-selection
      if (event && (event.ctrlKey || event.metaKey)) {
        // Toggle node in multi-selection
        setSelectedNodes(prev => {
          const next = new Set(prev);
          if (next.has(nodeId)) {
            // Remove from selection
            next.delete(nodeId);
          } else {
            // Add to selection
            next.add(nodeId);
          }
          
          // Update visual selection on canvas nodes to match the Set
          setCanvasNodes(cnodes => cnodes.map(n => ({ 
            ...n, 
            selected: next.has(n.node_id)
          })));
          
          // Close config panel when multiple nodes are selected
          if (next.size > 1) {
            setSelectedNode(null);
            setIsConfigPanelOpen(false);
          } else if (next.size === 1) {
            // Only one node selected, open config for it
            const singleNodeId = Array.from(next)[0];
            setSelectedNode(singleNodeId);
            setIsConfigPanelOpen(true);
          } else {
            // No nodes selected
            setSelectedNode(null);
            setIsConfigPanelOpen(false);
          }
          
          return next;
        });
      } else {
        // Normal single selection (no Ctrl/Cmd)
        setSelectedNode(nodeId);
        setCanvasNodes(prev => prev.map(n => ({ ...n, selected: n.node_id === nodeId })));
        setIsConfigPanelOpen(true);
        // Clear multi-selection when selecting single node
        setSelectedNodes(new Set([nodeId]));
      }
    }
  }
  
  function handleNodeDelete(nodeId: string) {
    const nodeToDelete = canvasNodes.find(n => n.node_id === nodeId);
    const nodeName = nodeToDelete?.name || nodeId;
    
    // Apply delete via producer and record as patch-based history
    pushProducer((draft: any) => {
      draft.canvasNodes = (draft.canvasNodes || []).filter((n: any) => n.node_id !== nodeId);
      draft.connections = (draft.connections || []).filter((c: any) => c.source.node_id !== nodeId && c.target.node_id !== nodeId);
    });
    setIsDirty(true);
    addLog(`🗑️ Deleted node: ${nodeName}`);
    if (selectedNode === nodeId) {
      setSelectedNode(null);
      setIsConfigPanelOpen(false);
    }
    // Remove from multi-selection
    setSelectedNodes(prev => {
      const next = new Set(prev);
      next.delete(nodeId);
      return next;
    });
  }
  
  function handleNodeFlip(nodeId: string) {
    pushProducer((draft: any) => {
      const node = (draft.canvasNodes || []).find((n: any) => n.node_id === nodeId);
      if (node) {
        node.flipped = !node.flipped;
      }
    });
    setIsDirty(true);
    addLog(`🔄 Flipped node horizontally`);
  }
  
  function handleNodeContextMenu(nodeId: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    
    if (!viewportRef.current) return;
    
    const rect = viewportRef.current.getBoundingClientRect();
    const scale = canvasPanZoom.scale || 1;
    const scrollLeft = viewportRef.current.scrollLeft;
    const scrollTop = viewportRef.current.scrollTop;
    
    const canvasX = (e.clientX - rect.left + scrollLeft) / scale;
    const canvasY = (e.clientY - rect.top + scrollTop) / scale;
    
    setNodeContextMenu({ x: canvasX, y: canvasY, nodeId });
    setContextMenu(null); // Close canvas context menu if open
  }
  
  // ==================== Selection Box Management ====================
  
  function handleSelectionBoxStart(e: React.MouseEvent) {
    if (!viewportRef.current) return;
    
    // Don't start selection box if clicking on a node
    const target = e.target as HTMLElement;
    if (target.closest('.workflow-node') || target.closest('.canvas-group') || target.closest('.canvas-text')) return;
    
    // Handle right-click for context menu
    if (e.button === 2) {
      e.preventDefault();
      const rect = viewportRef.current.getBoundingClientRect();
      const scale = canvasPanZoom.scale || 1;
      const scrollLeft = viewportRef.current.scrollLeft;
      const scrollTop = viewportRef.current.scrollTop;
      
      const canvasX = (e.clientX - rect.left + scrollLeft) / scale;
      const canvasY = (e.clientY - rect.top + scrollTop) / scale;
      
      setContextMenu({ x: canvasX, y: canvasY });
      return;
    }
    
    // Don't start selection box if Ctrl is held (that's for panning)
    if (e.ctrlKey || e.metaKey) return;
    
    const rect = viewportRef.current.getBoundingClientRect();
    const scale = canvasPanZoom.scale || 1;
    const scrollLeft = viewportRef.current.scrollLeft;
    const scrollTop = viewportRef.current.scrollTop;
    
    const canvasX = (e.clientX - rect.left + scrollLeft) / scale;
    const canvasY = (e.clientY - rect.top + scrollTop) / scale;
    
    setSelectionBox({
      startX: canvasX,
      startY: canvasY,
      currentX: canvasX,
      currentY: canvasY,
    });
  }
  
  function handleSelectionBoxMove(e: React.MouseEvent) {
    if (!selectionBox || !viewportRef.current) return;
    
    const rect = viewportRef.current.getBoundingClientRect();
    const scale = canvasPanZoom.scale || 1;
    const scrollLeft = viewportRef.current.scrollLeft;
    const scrollTop = viewportRef.current.scrollTop;
    
    const canvasX = (e.clientX - rect.left + scrollLeft) / scale;
    const canvasY = (e.clientY - rect.top + scrollTop) / scale;
    
    setSelectionBox(prev => prev ? {
      ...prev,
      currentX: canvasX,
      currentY: canvasY,
    } : null);
    
    // Update selected nodes based on intersection with selection box
    const minX = Math.min(selectionBox.startX, canvasX);
    const maxX = Math.max(selectionBox.startX, canvasX);
    const minY = Math.min(selectionBox.startY, canvasY);
    const maxY = Math.max(selectionBox.startY, canvasY);
    
    const selectedNodeIds = new Set<string>();
    canvasNodes.forEach(node => {
      const nodeRight = node.position.x + 240; // Approximate node width
      const nodeBottom = node.position.y + 100; // Approximate node height
      
      // Check if node intersects with selection box
      if (
        node.position.x < maxX &&
        nodeRight > minX &&
        node.position.y < maxY &&
        nodeBottom > minY
      ) {
        selectedNodeIds.add(node.node_id);
      }
    });
    
    setSelectedNodes(selectedNodeIds);
  }
  
  function handleSelectionBoxEnd() {
    if (!selectionBox) return;
    
    // Check if this was just a click (no drag) by measuring the distance
    const dragDistance = Math.sqrt(
      Math.pow(selectionBox.currentX - selectionBox.startX, 2) +
      Math.pow(selectionBox.currentY - selectionBox.startY, 2)
    );
    
    // If drag distance is very small (less than 5 pixels), treat it as a click on empty space
    if (dragDistance < 5) {
      // Clear selection when clicking on empty canvas
      setSelectedNodes(new Set());
      setSelectedNode(null);
      setSelectedObject(null);
      setIsConfigPanelOpen(false);
    } else {
      // It was a drag, so handle the selection box result
      if (selectedNodes.size === 0) {
        setSelectedNode(null);
        setIsConfigPanelOpen(false);
      } else if (selectedNodes.size === 1) {
        // If only one node selected, treat it as single selection
        const nodeId = Array.from(selectedNodes)[0];
        setSelectedNode(nodeId);
        setIsConfigPanelOpen(true);
      } else {
        // Multiple nodes selected, close config panel
        setSelectedNode(null);
        setIsConfigPanelOpen(false);
      }
    }
    
    setSelectionBox(null);
  }
  
  // ==================== Group Dragging Management ====================
  
  function handleGroupDragStart(nodeId: string, e: React.MouseEvent) {
    e.stopPropagation();
    
    // If Ctrl/Cmd is held, don't start dragging - let the click handler deal with selection
    if (e.ctrlKey || e.metaKey) {
      return;
    }
    
    // If the clicked node is not in the selection, select only it
    if (!selectedNodes.has(nodeId)) {
      setSelectedNodes(new Set([nodeId]));
      setSelectedNode(nodeId);
    }
    
    setIsDraggingGroup(true);
    
    if (viewportRef.current) {
      const scale = canvasPanZoom.scale || 1;
      const canvasRect = viewportRef.current.getBoundingClientRect();
      const scrollLeft = viewportRef.current.scrollLeft;
      const scrollTop = viewportRef.current.scrollTop;
      
      const canvasX = (e.clientX - canvasRect.left + scrollLeft) / scale;
      const canvasY = (e.clientY - canvasRect.top + scrollTop) / scale;
      
      setGroupDragStart({ x: canvasX, y: canvasY });
      
      // Calculate offsets for all selected nodes
      const offsets = new Map<string, { x: number; y: number }>();
      const nodesToDrag = selectedNodes.has(nodeId) ? selectedNodes : new Set([nodeId]);
      
      nodesToDrag.forEach(id => {
        const node = canvasNodes.find(n => n.node_id === id);
        if (node) {
          offsets.set(id, {
            x: canvasX - node.position.x,
            y: canvasY - node.position.y
          });
        }
      });
      
      setGroupDragOffsets(offsets);
    }
  }
  
  function handleGroupDrag(e: React.MouseEvent) {
    if (!isDraggingGroup || !groupDragStart || !viewportRef.current) return;
    
    const scale = canvasPanZoom.scale || 1;
    const canvasRect = viewportRef.current.getBoundingClientRect();
    const scrollLeft = viewportRef.current.scrollLeft;
    const scrollTop = viewportRef.current.scrollTop;
    
    const canvasX = (e.clientX - canvasRect.left + scrollLeft) / scale;
    const canvasY = (e.clientY - canvasRect.top + scrollTop) / scale;
    
    // Move all selected nodes
    setCanvasNodes(prev => prev.map(node => {
      if (selectedNodes.has(node.node_id)) {
        const offset = groupDragOffsets.get(node.node_id);
        if (offset) {
          return {
            ...node,
            position: {
              x: canvasX - offset.x,
              y: canvasY - offset.y
            }
          };
        }
      }
      return node;
    }));
    
    setIsDirty(true);
  }
  
  function handleGroupDragEnd() {
    if (isDraggingGroup) {
      // Record final positions
      const movedNodes = canvasNodes.filter(n => selectedNodes.has(n.node_id));
      if (movedNodes.length > 0) {
        pushProducer((draft: any) => {
          movedNodes.forEach(moved => {
            const dnode = (draft.canvasNodes || []).find((n: any) => n.node_id === moved.node_id);
            if (dnode) dnode.position = { ...moved.position };
          });
        });
      }
    }
    
    setIsDraggingGroup(false);
    setGroupDragStart(null);
    setGroupDragOffsets(new Map());
    
    // Reset dragging flag after a small delay
    setTimeout(() => setIsDraggingNode(false), 100);
  }
  
  function handleConfigUpdate(nodeId: string, newConfig: { [key: string]: any }) {
    pushProducer((draft: any) => {
      draft.canvasNodes = (draft.canvasNodes || []).map((n: any) =>
        n.node_id === nodeId ? { ...n, config: newConfig } : n
      );
    });
    setIsDirty(true);
    addLog(`⚙️ Updated configuration for node`);
  }
  
  function handleNodeUpdate(nodeId: string, updates: Partial<any>) {
    pushProducer((draft: any) => {
      draft.canvasNodes = (draft.canvasNodes || []).map((n: any) =>
        n.node_id === nodeId ? { ...n, ...updates } : n
      );
    });
    setIsDirty(true);
    if (updates.share_output_to_variables !== undefined) {
      addLog(`📤 ${updates.share_output_to_variables ? 'Enabled' : 'Disabled'} output sharing for node`);
    }
  }
  
  function handleNodeDragStart(nodeId: string, e: React.MouseEvent) {
    // Use the new group drag functionality
    handleGroupDragStart(nodeId, e);
  }
  
  function handleNodeDrag(e: React.MouseEvent) {
    // Use the new group drag functionality
    handleGroupDrag(e);
  }
  
  function handleNodeDragEnd() {
    // Use the new group drag functionality
    handleGroupDragEnd();
  }

  // ==================== Copy / Paste ====================
  // Copy selected nodes (and internal connections between them) into clipboardRef
  function copySelectedNodes() {
    if (!selectedNodes || selectedNodes.size === 0) return;
    const nodesToCopy = canvasNodes.filter(n => selectedNodes.has(n.node_id));
    const connectionsToCopy = connections.filter(c => selectedNodes.has(c.source.node_id) && selectedNodes.has(c.target.node_id));
    clipboardRef.current = {
      nodes: deepClone(nodesToCopy),
      connections: deepClone(connectionsToCopy)
    };
    pasteOffsetRef.current = 0;
    addLog(`📋 Copied ${nodesToCopy.length} node(s)`);
  }

  // Paste nodes from clipboard, remapping IDs and offsetting positions
  function pasteClipboard() {
    const clip = clipboardRef.current;
    if (!clip || !clip.nodes || clip.nodes.length === 0) return;

    const remap = new Map<string, string>();

    // Compute paste target: center of viewport in canvas coordinates
    let centerX: number | null = null;
    let centerY: number | null = null;
    const scale = canvasPanZoom.scale || 1;
    if (viewportRef.current) {
      const rect = viewportRef.current.getBoundingClientRect();
      const scrollLeft = viewportRef.current.scrollLeft;
      const scrollTop = viewportRef.current.scrollTop;
      const centerClientX = rect.left + rect.width / 2;
      const centerClientY = rect.top + rect.height / 2;
      centerX = (centerClientX - rect.left + scrollLeft) / scale;
      centerY = (centerClientY - rect.top + scrollTop) / scale;
    }

    // Compute centroid of copied nodes to translate them so their center lands in viewport center
    let centroidX = 0;
    let centroidY = 0;
    const nodeCount = clip.nodes.length;
    if (nodeCount > 0) {
      clip.nodes.forEach((n: any) => {
        centroidX += (n.position?.x || 0);
        centroidY += (n.position?.y || 0);
      });
      centroidX /= nodeCount;
      centroidY /= nodeCount;
    }

    // If we couldn't compute viewport center, fall back to small offset behavior
    const baseOffset = 40;
    const incremental = pasteOffsetRef.current || 0;
    // Default bias to nudge pasted nodes slightly up and left (negative values)
    const DEFAULT_UP_LEFT_BIAS = -100;

    const dx = centerX !== null ? (centerX - centroidX + incremental + DEFAULT_UP_LEFT_BIAS) : baseOffset + incremental + DEFAULT_UP_LEFT_BIAS;
    const dy = centerY !== null ? (centerY - centroidY + incremental + DEFAULT_UP_LEFT_BIAS) : baseOffset + incremental + DEFAULT_UP_LEFT_BIAS;

    const newNodes = clip.nodes.map((n: any) => {
      const newId = generateUUID();
      remap.set(n.node_id, newId);
      const copied = deepClone(n);
      copied.node_id = newId;
      // Translate nodes so centroid moves to viewport center (or apply fallback offset)
      const origX = copied.position?.x || 0;
      const origY = copied.position?.y || 0;
      copied.position = { x: origX + dx, y: origY + dy };
      return copied;
    });

    const newConnections = (clip.connections || []).map((c: any) => {
      const newConn = deepClone(c);
      newConn.id = `conn_${Date.now()}_${Math.random().toString(36).substr(2,9)}`;
      newConn.connection_id = newConn.id;
      if (newConn.source && remap.has(newConn.source.node_id)) newConn.source.node_id = remap.get(newConn.source.node_id);
      if (newConn.target && remap.has(newConn.target.node_id)) newConn.target.node_id = remap.get(newConn.target.node_id);
      return newConn;
    });

    pushProducer((draft: any) => {
      draft.canvasNodes = [...(draft.canvasNodes || []), ...newNodes];
      draft.connections = [...(draft.connections || []), ...newConnections];
    });

    setIsDirty(true);
    // Select newly pasted nodes
    setSelectedNodes(new Set(newNodes.map(n => n.node_id)));
    setSelectedNode(newNodes[0]?.node_id || null);
    pasteOffsetRef.current = (pasteOffsetRef.current || 0) + 20; // next paste will offset further
    addLog(`📥 Pasted ${newNodes.length} node(s)`);
  }

  // Cut = copy + delete
  function cutSelectedNodes() {
    if (!selectedNodes || selectedNodes.size === 0) return;
    copySelectedNodes();
    // Remove nodes and any connections that reference them
    pushProducer((draft: any) => {
      draft.canvasNodes = (draft.canvasNodes || []).filter((n: any) => !selectedNodes.has(n.node_id));
      draft.connections = (draft.connections || []).filter((c: any) => !selectedNodes.has(c.source.node_id) && !selectedNodes.has(c.target.node_id));
    });
    setSelectedNodes(new Set());
    setSelectedNode(null);
    setIsDirty(true);
    addLog(`✂️ Cut selection`);
  }

  // Keyboard shortcuts for copy/paste/cut (Ctrl/Cmd + C / V / X)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const key = (e.key || '').toLowerCase();
      const isMod = e.ctrlKey || e.metaKey;
      if (!isMod) return;

      const active = document.activeElement as HTMLElement | null;
      const tag = active?.tagName?.toLowerCase();
      const isTyping = tag === 'input' || tag === 'textarea' || active?.isContentEditable;
      if (isTyping) return; // don't intercept when typing in fields

      if (key === 'c') {
        e.preventDefault();
        copySelectedNodes();
      } else if (key === 'v') {
        e.preventDefault();
        pasteClipboard();
      } else if (key === 'x') {
        e.preventDefault();
        cutSelectedNodes();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [canvasNodes, connections, selectedNodes]);
  
  // ==================== Connection Management ====================
  
  function handlePortMouseDown(nodeId: string, portId: string, portType: 'input' | 'output', e: React.MouseEvent) {
    e.stopPropagation();
    if (viewportRef.current) {
      const rect = viewportRef.current.getBoundingClientRect();
      const scrollLeft = viewportRef.current.scrollLeft;
      const scrollTop = viewportRef.current.scrollTop;
      
      // Get canvas scale from the hook
      const scale = canvasPanZoom.scale || 1;
      
      // Calculate mouse position relative to canvas, accounting for scale and scroll
      const mouseX = (e.clientX - rect.left + scrollLeft) / scale;
      const mouseY = (e.clientY - rect.top + scrollTop) / scale;
      
      setTempConnection({
        fromNode: nodeId,
        fromPort: portId,
        fromType: portType,
        currentX: mouseX,
        currentY: mouseY,
      });
    }
  }
  
  function handleConnectionMouseMove(e: React.MouseEvent) {
    if (tempConnection && viewportRef.current) {
      const rect = viewportRef.current.getBoundingClientRect();
      const scrollLeft = viewportRef.current.scrollLeft;
      const scrollTop = viewportRef.current.scrollTop;
      
      // Get canvas scale from the hook
      const scale = canvasPanZoom.scale || 1;
      
      // Calculate mouse position relative to canvas, accounting for scale and scroll
      const mouseX = (e.clientX - rect.left + scrollLeft) / scale;
      const mouseY = (e.clientY - rect.top + scrollTop) / scale;
      
      setTempConnection(prev => prev ? {
        ...prev,
        currentX: mouseX,
        currentY: mouseY,
      } : null);
    }
  }
  
  function handleConnectionMouseUp(e: React.MouseEvent) {
    if (!tempConnection) return;
    
    const target = e.target as HTMLElement;
    const portHandle = target.closest('.port-handle');
    
    if (portHandle) {
      const portElement = portHandle.parentElement;
      const nodeElement = portHandle.closest('.workflow-node');
      
      if (portElement && nodeElement) {
        const targetNodeId = nodeElement.getAttribute('data-node-id');
        const targetPortId = portElement.getAttribute('data-port');
        const targetPortType = portHandle.classList.contains('input-handle') ? 'input' : 'output';
        
        if (canCreateConnection(tempConnection, targetNodeId, targetPortId, targetPortType)) {
          createConnection(tempConnection, targetNodeId!, targetPortId!, targetPortType);
        }
      }
    }
    
    setTempConnection(null);
  }
  
  function canCreateConnection(from: any, toNodeId: string | null, toPortId: string | null, toType: string): boolean {
    if (!toNodeId || !toPortId) return false;
    
    const isValidDirection = 
      (from.fromType === 'output' && toType === 'input') ||
      (from.fromType === 'input' && toType === 'output');
    
    if (!isValidDirection) return false;
    
    const sourceNodeId = from.fromType === 'output' ? from.fromNode : toNodeId;
    const sourcePortId = from.fromType === 'output' ? from.fromPort : toPortId;
    const targetNodeId = from.fromType === 'output' ? toNodeId : from.fromNode;
    const targetPortId = from.fromType === 'output' ? toPortId : from.fromPort;
    
    return !connections.some(c =>
      c.source.node_id === sourceNodeId &&
      c.source.port_id === sourcePortId &&
      c.target.node_id === targetNodeId &&
      c.target.port_id === targetPortId
    );
  }
  
  function createConnection(from: any, toNodeId: string, toPortId: string, toType: string) {
    const sourceNodeId = from.fromType === 'output' ? from.fromNode : toNodeId;
    const sourcePortId = from.fromType === 'output' ? from.fromPort : toPortId;
    const targetNodeId = from.fromType === 'output' ? toNodeId : from.fromNode;
    const targetPortId = from.fromType === 'output' ? toPortId : from.fromPort;
    
    const newConnection = {
      id: `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      source: { node_id: sourceNodeId, port_id: sourcePortId },
      target: { node_id: targetNodeId, port_id: targetPortId },
    };
    
    // Get node names for logging
    const sourceNode = canvasNodes.find(n => n.node_id === sourceNodeId);
    const targetNode = canvasNodes.find(n => n.node_id === targetNodeId);
    const sourceNodeName = sourceNode?.name || sourceNodeId;
    const targetNodeName = targetNode?.name || targetNodeId;
    
    pushProducer((draft: any) => {
      draft.connections = [...(draft.connections || []), newConnection];
    });
    setIsDirty(true);
    addLog(`🔗 Connected: ${sourceNodeName}.${sourcePortId} → ${targetNodeName}.${targetPortId}`);
  }
  
  function handleConnectionClick(connectionId: string) {
    // Delete connection without confirmation (consistent with node deletion)
    pushProducer((draft: any) => {
      draft.connections = (draft.connections || []).filter((c: any) => c.id !== connectionId);
    });
    setIsDirty(true);
    addLog(`🗑️ Deleted connection`);
  }
  
  // Helper to add log entries
  function addLog(message: string) {
    setLogs(prev => [...prev, message]);
    setTimeout(() => {
      if (logBodyRef.current) {
        logBodyRef.current.scrollTop = logBodyRef.current.scrollHeight;
      }
    }, 10);
  }
  
  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => {
        setIsFullscreen(true);
      }).catch(err => {
        addLog(`❌ Fullscreen error: ${err}`);
      });
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      });
    }
  };
  
  // Zoom controls
  const handleZoomIn = () => {
    canvasPanZoom.zoomIn();
  };
  
  const handleZoomOut = () => {
    canvasPanZoom.zoomOut();
  };
  
  const handleZoomReset = () => {
    canvasPanZoom.zoomReset();
  };
  
  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Keyboard shortcuts: undo/redo
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const active = document.activeElement as HTMLElement | null;
      if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.isContentEditable)) return;

      const key = (e.key || '').toLowerCase();
      const isUndo = (e.ctrlKey || e.metaKey) && !e.shiftKey && key === 'z';
      const isRedo = (e.ctrlKey && key === 'y') || ((e.ctrlKey || e.metaKey) && e.shiftKey && key === 'z');
      const isDelete = key === 'delete' || key === 'backspace';
      const isEscape = key === 'escape';
      const isSelectAll = (e.ctrlKey || e.metaKey) && key === 'a';
      const isSave = (e.ctrlKey || e.metaKey) && key === 's';
      const isLoad = (e.ctrlKey || e.metaKey) && key === 'l';

      // If the Clear button is focused, intercept Ctrl+Z/Ctrl+Y to toggle/confirm clear
      const isClearButtonFocused = clearButtonRef.current && active === clearButtonRef.current;
      if (isClearButtonFocused && (isUndo || isRedo)) {
        if (process.env.NODE_ENV !== 'production') console.debug('[key] clear button shortcut pressed - immediate clear');
        e.preventDefault();
        // Immediately clear and make it undoable (keyboard-triggered clear should be undoable)
        handleClear(true);
        setConfirmClear(false);
        return;
      }

      if (isUndo && canUndo) {
        if (process.env.NODE_ENV !== 'production') console.debug('[key] undo pressed');
        e.preventDefault();
        isUndoRedoOperation.current = true;
        undo();
      } else if (isRedo && canRedo) {
        if (process.env.NODE_ENV !== 'production') console.debug('[key] redo pressed');
        e.preventDefault();
        isUndoRedoOperation.current = true;
        redo();
      } else if (isSave) {
        // Open save options modal
        e.preventDefault();
        setShowSaveOptionsModal(true);
      } else if (isLoad) {
        // Open load options modal
        e.preventDefault();
        setShowLoadOptionsModal(true);
      } else if (isDelete && selectedNodes.size > 0) {
        // Delete all selected nodes
        e.preventDefault();
        const nodesToDelete = Array.from(selectedNodes);
        pushProducer((draft: any) => {
          draft.canvasNodes = (draft.canvasNodes || []).filter((n: any) => !nodesToDelete.includes(n.node_id));
          draft.connections = (draft.connections || []).filter((c: any) => 
            !nodesToDelete.includes(c.source.node_id) && !nodesToDelete.includes(c.target.node_id)
          );
        });
        setIsDirty(true);
        setSelectedNodes(new Set());
        setSelectedNode(null);
        setIsConfigPanelOpen(false);
        addLog(`🗑️ Deleted ${nodesToDelete.length} node(s)`);
      } else if (isEscape) {
        // Clear selection on Escape
        e.preventDefault();
        setSelectedNodes(new Set());
        setSelectedNode(null);
        setIsConfigPanelOpen(false);
      } else if (isSelectAll) {
        // Select all nodes
        e.preventDefault();
        const allNodeIds = new Set(canvasNodes.map(n => n.node_id));
        setSelectedNodes(allNodeIds);
        setSelectedNode(null);
        setIsConfigPanelOpen(false);
      }
    };

    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [undo, redo, canUndo, canRedo, selectedNodes, canvasNodes]);
  
  // Update minimap viewport indicator - more responsive
  useEffect(() => {
    if (!viewportRef.current) return;
    
    let animationFrameId: number;
    
    const updateMinimapViewport = () => {
      if (!viewportRef.current) return;
      
      const viewport = viewportRef.current;
      const scale = canvasPanZoom.scale || 1;
      const minimapScale = 0.04;
      
      // Cancel any pending animation frame
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      
      // Use requestAnimationFrame for smooth updates
      animationFrameId = requestAnimationFrame(() => {
        setMinimapViewport({
          x: (viewport.scrollLeft / scale) * minimapScale,
          y: (viewport.scrollTop / scale) * minimapScale,
          width: (viewport.clientWidth / scale) * minimapScale,
          height: (viewport.clientHeight / scale) * minimapScale,
        });
      });
        // Initialize previous scroll state if unset
        prevViewportScroll.current = { left: viewport.scrollLeft, top: viewport.scrollTop };
    };
    
    updateMinimapViewport();
    
    const viewport = viewportRef.current;
    // Add more event listeners for better responsiveness
    viewport.addEventListener('scroll', updateMinimapViewport);
    viewport.addEventListener('wheel', updateMinimapViewport);
    viewport.addEventListener('mousemove', updateMinimapViewport);
    window.addEventListener('resize', updateMinimapViewport);
    
    return () => {
      viewport.removeEventListener('scroll', updateMinimapViewport);
      viewport.removeEventListener('wheel', updateMinimapViewport);
      viewport.removeEventListener('mousemove', updateMinimapViewport);
      window.removeEventListener('resize', updateMinimapViewport);
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [canvasPanZoom.scale, viewportRef, canvasNodes]);

  // Reset paste offset when zoom changes so pasted nodes remain centered after zoom
  useEffect(() => {
    if (pasteOffsetRef) pasteOffsetRef.current = 0;
    if (process.env.NODE_ENV !== 'production') console.debug('[zoom] Reset paste offset due to zoom change');
  }, [canvasPanZoom.scale]);

  // Reset the sidebar cascade (staircase) when the viewport scrolls/pans
  useEffect(() => {
    if (!viewportRef.current) return;
    const viewport = viewportRef.current;

    // Throttle resets by a very small threshold to detect intentional viewport moves
    const SCROLL_RESET_THRESHOLD = 1; // px

    const handleViewportScroll = () => {
      const left = viewport.scrollLeft;
      const top = viewport.scrollTop;
      const prev = prevViewportScroll.current || { left: 0, top: 0 };
      const delta = Math.abs(left - prev.left) + Math.abs(top - prev.top);
      if (delta >= SCROLL_RESET_THRESHOLD) {
        // Reset staircase counter so next sidebar-added node anchors to the current viewport
        setSidebarNodeCount(0);
        // Reset paste offset so pasted nodes will center again after viewport move
        if (pasteOffsetRef) pasteOffsetRef.current = 0;
        // Update prev to avoid repeated resets while still scrolling
        prevViewportScroll.current = { left, top };
        // Debug/log for development ease
        if (process.env.NODE_ENV !== 'production') {
          console.debug('[viewport] Reset sidebar cascade due to scroll', { left, top });
          console.debug('[viewport] Reset paste offset due to scroll');
          // addLog('↩️ Reset node cascade due to viewport scroll');
        }
      }
    };

    // Initialize prev scroll
    prevViewportScroll.current = { left: viewport.scrollLeft, top: viewport.scrollTop };

    viewport.addEventListener('scroll', handleViewportScroll);
    viewport.addEventListener('wheel', handleViewportScroll);

    return () => {
      viewport.removeEventListener('scroll', handleViewportScroll);
      viewport.removeEventListener('wheel', handleViewportScroll);
    };
  }, [viewportRef]);
  
  // Auto-hide minimap when idle with smooth fade
  useEffect(() => {
    let hideTimer: NodeJS.Timeout;
    
    const showMinimapTemporarily = () => {
      setShowMinimap(true);
      clearTimeout(hideTimer);
      hideTimer = setTimeout(() => {
        setShowMinimap(false);
      }, 3000); // Hide after 3 seconds of inactivity
    };
    
    if (viewportRef.current) {
      const viewport = viewportRef.current;
      
      // Show minimap on various interactions
      viewport.addEventListener('scroll', showMinimapTemporarily);
      viewport.addEventListener('wheel', showMinimapTemporarily);
      viewport.addEventListener('mousedown', showMinimapTemporarily);
      document.addEventListener('keydown', showMinimapTemporarily);
      
      return () => {
        viewport.removeEventListener('scroll', showMinimapTemporarily);
        viewport.removeEventListener('wheel', showMinimapTemporarily);
        viewport.removeEventListener('mousedown', showMinimapTemporarily);
        document.removeEventListener('keydown', showMinimapTemporarily);
        clearTimeout(hideTimer);
      };
    }
  }, [viewportRef]);
  
  // Helper function to get node category color
  const getNodeCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      triggers: '#fbbf24',     // Amber
      actions: '#22c55e',      // Green
      ai: '#a855f7',           // Purple
      communication: '#3b82f6', // Blue
      processing: '#f97316',   // Orange
      workflow: '#6366f1',     // Indigo
      input: '#06b6d4',        // Cyan
      output: '#ec4899',       // Pink
      control: '#8b5cf6',      // Violet
      business: '#10b981',     // Emerald
      analytics: '#f43f5e',    // Rose
    };
    return colors[category.toLowerCase()] || '#9ca3af';
  };

  return (
    <div className="w-full h-full flex overflow-hidden" onClick={() => setConfirmClear(false)} style={{ background: 'var(--theme-background)' }}>
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar { width: 8px; height: 8px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: var(--theme-border); border-radius: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: var(--theme-text-muted); }
      `}</style>

      {/* Sidebar */}
      {!isSidebarCollapsed && (
        <div 
          className="border-r flex flex-col transition-all duration-300 shrink-0 w-90"
          style={{ 
            background: 'var(--theme-surface)', 
            borderColor: 'var(--theme-border)' 
          }}
        >
          <div
            className="flex items-center justify-between p-3 border-b shrink-0"
            style={{ borderColor: 'var(--theme-border)' }}
          >
              <h2 className="text-sm font-semibold flex items-center gap-2" style={{ color: 'var(--theme-text)' }}>
                <i className="fa-solid fa-cubes"></i><span>Nodes</span>
              </h2>
            <div className="flex items-center">
              {(() => {
                // Compute categories dynamically from loaded nodeCategories
                const allCategories = (nodeCategories || []).map((c: any) => c.name || '');
                const allCollapsed = allCategories.every(cat => collapsedCategories.has(normCategory(cat)));
                return (
                  <button
                    onClick={() => {
                      if (allCollapsed) {
                        // Expand all categories
                        setCollapsedCategories(new Set());
                      } else {
                        // Collapse all categories (store normalized keys)
                        setCollapsedCategories(new Set(allCategories.map(normCategory)));
                      }
                    }}
                    className="px-3 py-2 rounded transition-colors font-bold text-lg"
                    style={{
                      color: 'var(--theme-text-secondary)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'var(--theme-surface-hover)';
                      e.currentTarget.style.color = 'var(--theme-text)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--theme-text-secondary)';
                    }}
                    title={allCollapsed ? "Expand all categories" : "Collapse all categories"}
                  >
                    <i className={`fas fa-${allCollapsed ? 'plus' : 'minus'}`} style={{ fontSize: '12px' }}></i>
                  </button>
                );
              })()}
              <button
                onClick={() => setIsSidebarCollapsed(true)}
                className="px-4 py-3 rounded transition-colors font-black text-2xl"
                style={{
                  color: 'var(--theme-text-secondary)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--theme-surface-hover)';
                  e.currentTarget.style.color = 'var(--theme-text)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = 'var(--theme-text-secondary)';
                }}
                title="Collapse sidebar"
              >
                  ←
                </button>
            </div>
            </div>

            <div className="p-3 border-b shrink-0" style={{ borderColor: 'var(--theme-border)' }}>
              <input 
                type="text" 
                value={searchTerm} 
                onChange={(e) => setSearchTerm(e.target.value)} 
                className="w-full px-3 py-2 rounded text-sm border focus:outline-none" 
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: 'var(--theme-text)',
                  borderColor: 'var(--theme-border)',
                }}
                onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                placeholder="Search nodes..." 
              />
            </div>
            <div className="flex-1 overflow-y-auto p-2 custom-scrollbar" style={{ scrollbarGutter: 'stable' }}>
              {nodeCategories.map((category, idx) => {
                // Pre-filter nodes for this category based on search term
                const nodesForCategory = (category.nodes || []).filter((node: any) => {
                  const term = searchTerm.trim().toLowerCase();
                  if (!term) return true;
                  return (node.name && node.name.toLowerCase().includes(term)) || (node.description && node.description.toLowerCase().includes(term));
                });

                // If this category has no matching nodes, don't render it
                if (nodesForCategory.length === 0) {
                  return null;
                }

                const catKey = normCategory(category.name);
                const isCollapsed = collapsedCategories.has(catKey);
                const toggleCollapse = () => {
                  setCollapsedCategories(prev => {
                    const next = new Set(prev);
                    if (next.has(catKey)) {
                      next.delete(catKey);
                    } else {
                      next.add(catKey);
                    }
                    return next;
                  });
                };

                return (
                  <div key={idx} className="mb-2">
                    <div 
                      className="flex items-center justify-between px-2 py-1 text-xs font-semibold uppercase cursor-pointer rounded transition-colors" 
                      style={{ color: 'var(--theme-text-muted)' }}
                      onClick={toggleCollapse}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <div className="flex items-center gap-2">
                        <i className={category.icon} style={{ width: '15px' }}></i>
                        <span>{category.name}</span>
                      </div>
                      <i className={`fas fa-chevron-${isCollapsed ? 'right' : 'down'} text-xs transition-transform`}></i>
                    </div>
                    {!isCollapsed && (
                      <div className="space-y-1 mt-1">
                        {nodesForCategory.map((node: any, nodeIdx: number) => {
                      const nodeIconInfo = getNodeIcon(node.category || 'default');
                      const iconClass = node.icon || nodeIconInfo.icon;
                      return (
                        <div 
                          key={nodeIdx} 
                          className="px-3 py-2.5 rounded cursor-grab active:cursor-grabbing transition-colors border" 
                          style={{
                            background: 'var(--theme-surface-variant)',
                            borderColor: 'var(--theme-border)'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
                          draggable 
                          onDragStart={(e) => { 
                            e.dataTransfer.setData('application/node', JSON.stringify({ 
                              type: node.type, 
                              name: node.name, 
                              category: node.category, 
                              icon: node.icon, 
                              input_ports: node.input_ports, 
                              output_ports: node.output_ports 
                            })); 
                            e.dataTransfer.effectAllowed = 'copy'; 
                          }} 
                          onClick={() => { 
                            if (viewportRef.current) { 
                              const viewport = viewportRef.current;
                              const scale = canvasPanZoom.scale || 1;
                              
                              // Calculate top-left anchor of the current viewport in canvas coordinates
                              const marginLeft = 20; // left margin from the viewport
                              const marginTop = 20; // top margin from the viewport
                              const offsetY = 30; // Vertical spacing for each new node so they don't overlap (approx node height)
                              const offsetX = 15; // Small horizontal shift per node to the right (staircase)
                              const x = (viewport.scrollLeft + marginLeft + (sidebarNodeCount * offsetX)) / scale;
                              const y = (viewport.scrollTop + marginTop + (sidebarNodeCount * offsetY)) / scale;
                              
                              addNodeToCanvas(
                                node.type, 
                                node.name, 
                                node.category, 
                                { x, y }, 
                                node.icon, 
                                node.input_ports, 
                                node.output_ports
                              );
                              
                              // Increment staircase counter
                              setSidebarNodeCount(prev => prev + 1);
                            } 
                          }}
                        >
                          <div className="flex items-start gap-2">
                            <div className="flex-shrink-0 w-8 h-8 rounded flex items-center justify-center mt-0.5" style={{ background: nodeIconInfo.bgColor }}>
                              <i className={`${iconClass} text-sm`} style={{ color: nodeIconInfo.color }}></i>
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-semibold leading-tight" style={{ color: 'var(--theme-text)' }}>{node.name || 'Unnamed Node'}</div>
                              <div className="text-xs mt-0.5 leading-snug" style={{ color: 'var(--theme-text-muted)' }}>{node.description || 'No description'}</div>
                          </div>
                          </div>
                        </div>
                      );
                    })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Control Bar */}
        <div 
          className="flex items-center justify-between px-4 py-2 border-b shrink-0"
          style={{ 
            background: 'var(--theme-surface)', 
            borderColor: 'var(--theme-border)' 
          }}
        >
          <div className="flex items-center gap-2">
            {isSidebarCollapsed && (
              <button
                onClick={() => setIsSidebarCollapsed(false)}
                className="px-3 py-1 rounded text-sm transition-colors border flex items-center gap-1.5"
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: 'var(--theme-text)',
                  borderColor: 'var(--theme-border)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
                title="Expand sidebar"
              >
                <i className="fas fa-bars"></i>
                <span>Nodes</span>
              </button>
            )}
            <input 
              type="text" 
              className="px-3 py-1 rounded text-sm border focus:outline-none" 
              style={{
                background: 'var(--theme-surface-variant)',
                color: 'var(--theme-text)',
                borderColor: 'var(--theme-border)',
              }}
              onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
              onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
              placeholder="Untitled Workflow" 
              value={workflowName} 
              onChange={(e) => { setWorkflowName(e.target.value); setIsDirty(true); }} 
            />
            <input 
              type="text" 
              className="px-3 py-1 rounded text-sm border focus:outline-none" 
              style={{
                background: 'var(--theme-surface-variant)',
                color: 'var(--theme-text)',
                borderColor: 'var(--theme-border)',
                width: '500px',
              }}
              onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
              onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
              placeholder="Workflow description..." 
              value={workflowDescription} 
              maxLength={50}
              onChange={(e) => { setWorkflowDescription(e.target.value); setIsDirty(true); }} 
            />
            {isDirty && <span className="text-xs" style={{ color: 'var(--theme-warning)' }}>●</span>}
          </div>
          <div className="flex items-center gap-2">
            {/* Save button */}
            <button 
              onClick={() => setShowSaveOptionsModal(true)}
              className="px-3 py-1 text-white rounded text-sm transition-colors"
              style={{ background: 'var(--theme-success)' }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-success-hover)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-success)'}
              title="Save workflow (Ctrl+S)"
            >
              <i className=""></i>
              Save
            </button>
            
            {/* Load button */}
            <button 
              onClick={() => setShowLoadOptionsModal(true)}
              className="px-3 py-1 rounded text-sm transition-colors border"
              style={{
                background: 'var(--theme-surface-variant)',
                color: 'var(--theme-text)',
                borderColor: 'var(--theme-border)',
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
              title="Load workflow (Ctrl+L)"
            >
              <i className=""></i>
              Load
            </button>
            
            <div className="flex items-center gap-1">
              <button 
                ref={clearButtonRef}
                onClick={handleClearClick} 
                className="px-3 py-1 rounded text-sm transition-colors border"
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: confirmClear ? 'var(--theme-danger)' : 'var(--theme-text)',
                  borderColor: 'var(--theme-border)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
              >{confirmClear ? "Confirm?" : "Clear"}</button>

              <button
                onClick={() => {
                  isUndoRedoOperation.current = true;
                  undo();
                }}
                disabled={!canUndo}
                className="px-3 py-1 rounded text-sm transition-colors border mx-1"
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: canUndo ? 'var(--theme-text)' : 'var(--theme-text-muted)',
                  borderColor: 'var(--theme-border)'
                }}
                title={'Undo (Ctrl+Z/Cmd+Z)'}
              >
                <i className="fas fa-undo"></i>
              </button>
              <button
                onClick={() => {
                  isUndoRedoOperation.current = true;
                  redo();
                }}
                disabled={!canRedo}
                className="px-3 py-1 rounded text-sm transition-colors border"
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: canRedo ? 'var(--theme-text)' : 'var(--theme-text-muted)',
                  borderColor: 'var(--theme-border)'
                }}
                title={'Redo (Ctrl+Y / Cmd+Shift+Z)'}
              >
                <i className="fas fa-redo"></i>
              </button>
            </div>
            <div className="w-px h-6" style={{ background: 'var(--theme-border)' }} />
            {/* Execution control buttons - state machine */}
            {execution.isExecuting ? (
              /* RUNNING STATE: Show Pause/Resume + Stop */
              <>
                {!execution.isPaused ? (
                  <button 
                    onClick={execution.handlePause} 
                    className="px-3 py-1 text-white rounded text-sm transition-colors"
                    style={{ background: 'var(--theme-warning)' }}
                    onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
                    onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                  >Pause</button>
                ) : (
                  <button 
                    onClick={execution.handleResume} 
                    className="px-3 py-1 text-white rounded text-sm transition-colors"
                    style={{ background: 'var(--theme-success)' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-success-hover)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-success)'}
                  >Resume</button>
                )}
                <button 
                  onClick={execution.handleStop} 
                  className="px-3 py-1 text-white rounded text-sm transition-colors"
                  style={{ background: 'var(--theme-danger)' }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-danger-hover)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-danger)'}
                >Stop</button>
              </>
            ) : (execution.lastResult === 'failed' || execution.lastResult === 'stopped') ? (
              /* FAILED/STOPPED STATE: Show Retry + Restart */
              <>
                <button 
                  onClick={() => execution.handleRetry(false)}
                  className="px-3 py-1 text-white rounded text-sm font-medium transition-colors flex items-center gap-1"
                  style={{ background: 'var(--theme-warning)' }}
                  onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
                  onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                  title={execution.retryInfo ? `Retry from checkpoint - skip ${execution.retryInfo.completed_count || 0} completed node(s)` : 'Retry from checkpoint'}
                >
                  <i className="fas fa-redo text-xs"></i>
                  Retry
                  {execution.retryInfo?.completed_count != null && execution.retryInfo.completed_count > 0 && (
                    <span className="text-xs opacity-75">({execution.retryInfo.completed_count})</span>
                  )}
                </button>
                <button 
                  onClick={async () => {
                    if (isDirty) await handleSave(true);
                    execution.handleRestart();
                  }}
                  className="px-3 py-1 text-white rounded text-sm transition-colors"
                  style={{ background: 'var(--theme-primary)' }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-primary-hover)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-primary)'}
                  title="Run workflow from the beginning"
                >
                  Restart
                </button>
              </>
            ) : (
              /* IDLE/COMPLETED STATE: Show Run */
              <button 
                onClick={async () => {
                  if (isDirty) await handleSave(true);
                  execution.handleRun();
                }}
                className="px-4 py-1 text-white rounded text-sm font-medium transition-colors"
                style={{ background: 'var(--theme-primary)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-primary-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-primary)'}
              >Run</button>
            )}
            <div className="w-px h-6" style={{ background: 'var(--theme-border)' }} />
            
            {/* Zoom controls */}
            <div className="flex items-center gap-1 px-2 py-1 rounded border"
              style={{
                background: 'var(--theme-surface-variant)',
                borderColor: 'var(--theme-border)',
              }}
            >
              <button
                onClick={handleZoomOut}
                className="px-2 py-0.5 rounded text-xs transition-colors"
                style={{ color: 'var(--theme-text)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                title="Zoom out"
              >
                <i className="fas fa-minus"></i>
              </button>
              <span className="text-xs px-2" style={{ color: 'var(--theme-text-secondary)', minWidth: '45px', textAlign: 'center' }}>
                {zoomLevel}%
              </span>
              <button
                onClick={handleZoomIn}
                className="px-2 py-0.5 rounded text-xs transition-colors"
                style={{ color: 'var(--theme-text)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                title="Zoom in"
              >
                <i className="fas fa-plus"></i>
              </button>
              <button
                onClick={handleZoomReset}
                className="px-2 py-0.5 rounded text-xs transition-colors"
                style={{ color: 'var(--theme-text)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                title="Reset zoom"
              >
                <i className="fas fa-undo"></i>
              </button>
            </div>
            
            {/* Fullscreen button */}
            <button 
              onClick={toggleFullscreen}
              className="px-3 py-1 rounded text-sm transition-colors border"
              style={{
                background: 'var(--theme-surface-variant)',
                color: 'var(--theme-text)',
                borderColor: 'var(--theme-border)',
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
              title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
            >
              <i className={`fas fa-${isFullscreen ? 'compress' : 'expand'}`}></i>
            </button>
          </div>
        </div>

        {/* Canvas Area */}
        <div className="flex-1 overflow-hidden relative">
          <div 
            ref={viewportRef} 
            id="canvasViewport" 
            className="w-full h-full overflow-auto" 
            style={{ 
              background: 'var(--theme-background)',
              "--canvas-grid-size": `${gridSettings.gridSize}px`, 
              "--canvas-grid-color": "var(--theme-border)", 
              "--canvas-grid-opacity": gridSettings.enableGrid ? gridSettings.gridOpacity.toString() : "0"
            } as React.CSSProperties} 
            onMouseMove={(e) => { 
              handleNodeDrag(e); 
              handleConnectionMouseMove(e); 
              handleSelectionBoxMove(e);
              handleObjectDrag(e);
              handleGroupResize(e);
            }} 
            onMouseUp={(e) => { 
              handleNodeDragEnd(); 
              handleConnectionMouseUp(e); 
              handleSelectionBoxEnd();
              handleObjectDragEnd();
              handleGroupResizeEnd();
            }} 
            onMouseLeave={() => { 
              handleNodeDragEnd(); 
              setTempConnection(null); 
              handleSelectionBoxEnd();
              handleObjectDragEnd();
              handleGroupResizeEnd();
            }} 
            onMouseDown={(e) => {
              // Close context menu when clicking elsewhere
              if (contextMenu || nodeContextMenu) {
                const target = e.target as HTMLElement;
                if (!target.closest('.context-menu')) {
                  setContextMenu(null);
                  setNodeContextMenu(null);
                }
              }
              handleSelectionBoxStart(e);
            }}
            onContextMenu={(e) => {
              e.preventDefault(); // Prevent default browser context menu
            }}
            onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; }} 
            onDrop={(e) => { 
              e.preventDefault(); 
              const nodeData = e.dataTransfer.getData('application/node'); 
              if (nodeData && viewportRef.current) { 
                const node = JSON.parse(nodeData); 
                const rect = viewportRef.current.getBoundingClientRect(); 
                const scale = canvasPanZoom.scale || 1;
                
                // Calculate position relative to canvas, accounting for scroll and zoom
                const x = (e.clientX - rect.left + viewportRef.current.scrollLeft) / scale;
                const y = (e.clientY - rect.top + viewportRef.current.scrollTop) / scale;
                
                addNodeToCanvas(node.type, node.name, node.category, { x, y }, node.icon, node.input_ports, node.output_ports); 
              } 
            }}
          >
            {/* Render nodes and connections into the canvas div using portal */}
            {canvasPanZoom.canvasRef && createPortal(
              <>
                {/* Render groups first (behind everything) */}
                {canvasObjects
                  .filter(obj => obj.type === 'group')
                  .sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0))
                  .map(group => (
                    <div
                      key={group.id}
                      className={`canvas-group ${selectedObject === group.id ? 'selected' : ''}`}
                      style={{
                        position: 'absolute',
                        left: `${group.position.x}px`,
                        top: `${group.position.y}px`,
                        width: `${group.size.width}px`,
                        height: `${group.size.height}px`,
                        backgroundColor: group.color,
                        border: selectedObject === group.id ? '2px solid #3b82f6' : '2px solid rgba(0,0,0,0.1)',
                        borderRadius: '8px',
                        zIndex: group.zIndex || -1,
                        cursor: 'move',
                        opacity: 0.5,
                      }}
                      onMouseDown={(e) => {
                        const target = e.target as HTMLElement;
                        if (!target.classList.contains('resize-handle') && !target.closest('.group-controls')) {
                          handleObjectDragStart(group.id, e);
                        }
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedObject(group.id);
                      }}
                    >
                      {/* Title */}
                      <input
                        type="text"
                        value={group.title}
                        onChange={(e) => {
                          e.stopPropagation();
                          updateCanvasObject(group.id, { title: e.target.value });
                        }}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          position: 'absolute',
                          top: '8px',
                          left: '12px',
                          fontSize: '14px',
                          fontWeight: 600,
                          color: '#374151',
                          background: 'transparent',
                          border: selectedObject === group.id ? '1px dashed rgba(0,0,0,0.2)' : '1px solid transparent',
                          padding: '2px 4px',
                          borderRadius: '3px',
                          maxWidth: `${group.size.width - 100}px`,
                        }}
                      />
                      
                      {/* Controls */}
                      {selectedObject === group.id && (
                        <div className="group-controls" style={{ position: 'absolute', top: '8px', right: '8px', display: 'flex', gap: '4px' }}>
                          <input
                            type="color"
                            value={group.color}
                            onChange={(e) => {
                              e.stopPropagation();
                              updateCanvasObject(group.id, { color: e.target.value });
                            }}
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              width: '28px',
                              height: '28px',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                            }}
                            title="Change color"
                          />
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteCanvasObject(group.id);
                            }}
                            style={{
                              background: '#ef4444',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              cursor: 'pointer',
                              fontSize: '12px',
                            }}
                          >
                            <i className="fas fa-trash"></i>
                          </button>
                        </div>
                      )}
                      
                      {/* Resize handles */}
                      {selectedObject === group.id && (
                        <>
                          {/* Corner handles */}
                          {['nw', 'ne', 'sw', 'se'].map(handle => (
                            <div
                              key={handle}
                              className="resize-handle"
                              onMouseDown={(e) => handleGroupResizeStart(group.id, handle, e)}
                              style={{
                                position: 'absolute',
                                width: '12px',
                                height: '12px',
                                background: '#3b82f6',
                                border: '2px solid white',
                                borderRadius: '50%',
                                cursor: `${handle}-resize`,
                                zIndex: 10,
                                ...(handle === 'nw' && { top: '-6px', left: '-6px' }),
                                ...(handle === 'ne' && { top: '-6px', right: '-6px' }),
                                ...(handle === 'sw' && { bottom: '-6px', left: '-6px' }),
                                ...(handle === 'se' && { bottom: '-6px', right: '-6px' }),
                              }}
                            />
                          ))}
                          {/* Edge handles */}
                          {['n', 'e', 's', 'w'].map(handle => (
                            <div
                              key={handle}
                              className="resize-handle"
                              onMouseDown={(e) => handleGroupResizeStart(group.id, handle, e)}
                              style={{
                                position: 'absolute',
                                background: '#3b82f6',
                                border: '1px solid white',
                                cursor: `${handle === 'n' || handle === 's' ? 'ns' : 'ew'}-resize`,
                                zIndex: 10,
                                ...(handle === 'n' && { top: '-3px', left: '50%', transform: 'translateX(-50%)', width: '40px', height: '6px', borderRadius: '3px' }),
                                ...(handle === 's' && { bottom: '-3px', left: '50%', transform: 'translateX(-50%)', width: '40px', height: '6px', borderRadius: '3px' }),
                                ...(handle === 'e' && { right: '-3px', top: '50%', transform: 'translateY(-50%)', width: '6px', height: '40px', borderRadius: '3px' }),
                                ...(handle === 'w' && { left: '-3px', top: '50%', transform: 'translateY(-50%)', width: '6px', height: '40px', borderRadius: '3px' }),
                              }}
                            />
                          ))}
                        </>
                      )}
                    </div>
                  ))}
                
                {/* Render text annotations */}
                {canvasObjects
                  .filter(obj => obj.type === 'text')
                  .map(text => (
                    <div
                      key={text.id}
                      className={`canvas-text ${selectedObject === text.id ? 'selected' : ''}`}
                      style={{
                        position: 'absolute',
                        left: `${text.position.x}px`,
                        top: `${text.position.y}px`,
                        fontSize: `${text.fontSize}px`,
                        color: text.color,
                        zIndex: text.zIndex || 0,
                        cursor: editingText === text.id ? 'text' : 'move',
                        padding: '4px 8px',
                        border: selectedObject === text.id ? '2px dashed #3b82f6' : '2px dashed transparent',
                        borderRadius: '4px',
                        backgroundColor: selectedObject === text.id ? 'rgba(59, 130, 246, 0.05)' : 'transparent',
                        minWidth: '100px',
                        whiteSpace: 'pre-wrap',
                      }}
                      onMouseDown={(e) => {
                        if (editingText !== text.id) {
                          handleObjectDragStart(text.id, e);
                        }
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (editingText !== text.id) {
                          setSelectedObject(text.id);
                        }
                      }}
                      onDoubleClick={(e) => {
                        e.stopPropagation();
                        setEditingText(text.id);
                        setSelectedObject(text.id);
                        // Focus the contentEditable div
                        setTimeout(() => {
                          const el = document.getElementById(`text-edit-${text.id}`);
                          if (el) {
                            el.focus();
                            // Move cursor to end
                            const range = document.createRange();
                            const sel = window.getSelection();
                            range.selectNodeContents(el);
                            range.collapse(false);
                            sel?.removeAllRanges();
                            sel?.addRange(range);
                          }
                        }, 0);
                      }}
                    >
                      {editingText === text.id ? (
                        <div
                          id={`text-edit-${text.id}`}
                          contentEditable
                          suppressContentEditableWarning
                          onBlur={(e) => {
                            const newContent = e.currentTarget.textContent || '';
                            if (newContent.trim()) {
                              updateCanvasObject(text.id, { content: newContent });
                            }
                            setEditingText(null);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                              e.preventDefault();
                              const newContent = e.currentTarget.textContent || '';
                              if (newContent.trim()) {
                                updateCanvasObject(text.id, { content: newContent });
                              }
                              setEditingText(null);
                            }
                            if (e.key === 'Escape') {
                              setEditingText(null);
                            }
                            e.stopPropagation(); // Prevent keyboard shortcuts while editing
                          }}
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            outline: 'none',
                            minWidth: '100px',
                            whiteSpace: 'pre-wrap',
                          }}
                        >
                          {text.content}
                        </div>
                      ) : (
                        text.content
                      )}
                      {selectedObject === text.id && editingText !== text.id && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteCanvasObject(text.id);
                          }}
                          style={{
                            position: 'absolute',
                            top: '-10px',
                            right: '-10px',
                            background: '#ef4444',
                            color: 'white',
                            border: 'none',
                            borderRadius: '50%',
                            width: '20px',
                            height: '20px',
                            cursor: 'pointer',
                            fontSize: '10px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <i className="fas fa-times"></i>
                        </button>
                      )}
                    </div>
                  ))}
                
                <ConnectionsLayer connections={connections} nodes={canvasNodes} tempConnection={tempConnection} onConnectionClick={handleConnectionClick} />
                <NodesLayer 
                  nodes={canvasNodes} 
                  nodeStates={nodeStates} 
                  nodeExecutionData={nodeExecutionData} 
                  onNodeSelect={handleNodeSelect} 
                  onNodeDelete={handleNodeDelete} 
                  onNodeDragStart={handleNodeDragStart} 
                  onPortMouseDown={handlePortMouseDown}
                  onNodeContextMenu={handleNodeContextMenu}
                  selectedNodes={selectedNodes}
                />
                {/* Selection box visualization */}
                {selectionBox && (
                  <div
                    style={{
                      position: 'absolute',
                      left: `${Math.min(selectionBox.startX, selectionBox.currentX)}px`,
                      top: `${Math.min(selectionBox.startY, selectionBox.currentY)}px`,
                      width: `${Math.abs(selectionBox.currentX - selectionBox.startX)}px`,
                      height: `${Math.abs(selectionBox.currentY - selectionBox.startY)}px`,
                      border: '2px dashed var(--theme-primary)',
                      background: 'rgba(59, 130, 246, 0.1)',
                      pointerEvents: 'none',
                      zIndex: 1000,
                    }}
                  />
                )}
                
                {/* Context menu */}
                {contextMenu && (
                  <div
                    className="context-menu"
                    style={{
                      position: 'absolute',
                      left: `${contextMenu.x}px`,
                      top: `${contextMenu.y}px`,
                      background: 'var(--theme-surface)',
                      border: '1px solid var(--theme-border)',
                      borderRadius: '8px',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                      zIndex: 2000,
                      minWidth: '180px',
                      padding: '4px',
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        createGroup(contextMenu.x, contextMenu.y);
                        setContextMenu(null);
                      }}
                      className="w-full text-left px-3 py-2 text-sm rounded transition-colors flex items-center gap-2"
                      style={{ color: 'var(--theme-text)' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <i className="fas fa-object-group w-4"></i>
                      <span>Add Group</span>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        createTextAnnotation(contextMenu.x, contextMenu.y);
                        setContextMenu(null);
                      }}
                      className="w-full text-left px-3 py-2 text-sm rounded transition-colors flex items-center gap-2"
                      style={{ color: 'var(--theme-text)' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <i className="fas fa-font w-4"></i>
                      <span>Add Text</span>
                    </button>
                  </div>
                )}
                
                {/* Node context menu */}
                {nodeContextMenu && (
                  <div
                    className="context-menu"
                    style={{
                      position: 'absolute',
                      left: `${nodeContextMenu.x}px`,
                      top: `${nodeContextMenu.y}px`,
                      background: 'var(--theme-surface)',
                      border: '1px solid var(--theme-border)',
                      borderRadius: '8px',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                      zIndex: 2000,
                      minWidth: '180px',
                      padding: '4px',
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleNodeFlip(nodeContextMenu.nodeId);
                        setNodeContextMenu(null);
                      }}
                      className="w-full text-left px-3 py-2 text-sm rounded transition-colors flex items-center gap-2"
                      style={{ color: 'var(--theme-text)' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <i className="fas fa-left-right w-4"></i>
                      <span>Flip Horizontally</span>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleNodeDelete(nodeContextMenu.nodeId);
                        setNodeContextMenu(null);
                      }}
                      className="w-full text-left px-3 py-2 text-sm rounded transition-colors flex items-center gap-2"
                      style={{ color: '#ef4444' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <i className="fas fa-trash w-4"></i>
                      <span>Delete</span>
                    </button>
                  </div>
                )}
              </>,
              canvasPanZoom.canvasRef
            )}
          </div>
          
          {/* Minimap - positioned outside canvas viewport, overlaid on top */}
          <div 
            className="absolute bottom-4 right-4 rounded shadow-lg border overflow-hidden"
            style={{
              width: '200px',
              height: '150px',
              background: 'var(--theme-surface)',
              borderColor: 'var(--theme-border)',
              zIndex: 30,
              opacity: showMinimap ? 1 : 0,
              pointerEvents: showMinimap ? 'auto' : 'none',
              transition: 'opacity 0.5s ease-in-out',
              cursor: isDraggingMinimap ? 'grabbing' : 'grab',
            }}
            onMouseDown={(e) => {
              if (!viewportRef.current) return;
              
              // Start dragging minimap
              setIsDraggingMinimap(true);
              e.preventDefault();
              e.stopPropagation();
              
              // Immediately update position on mousedown
              const minimapRect = e.currentTarget.getBoundingClientRect();
              const clickX = e.clientX - minimapRect.left;
              const clickY = e.clientY - minimapRect.top;
              
              const minimapScale = 0.04;
              const scale = canvasPanZoom.scale || 1;
              
              // Convert minimap coordinates to canvas coordinates
              const canvasX = clickX / minimapScale;
              const canvasY = clickY / minimapScale;
              
              // Center the viewport on the clicked position
              const viewport = viewportRef.current;
              const scrollX = (canvasX * scale) - (viewport.clientWidth / 2);
              const scrollY = (canvasY * scale) - (viewport.clientHeight / 2);
              
              viewport.scrollTo({
                left: scrollX,
                top: scrollY,
                behavior: 'auto'
              });
            }}
            onMouseMove={(e) => {
              if (!isDraggingMinimap || !viewportRef.current) return;
              
              e.preventDefault();
              e.stopPropagation();
              
              const minimapRect = e.currentTarget.getBoundingClientRect();
              const clickX = e.clientX - minimapRect.left;
              const clickY = e.clientY - minimapRect.top;
              
              const minimapScale = 0.04;
              const scale = canvasPanZoom.scale || 1;
              
              // Convert minimap coordinates to canvas coordinates
              const canvasX = clickX / minimapScale;
              const canvasY = clickY / minimapScale;
              
              // Center the viewport on the dragged position
              const viewport = viewportRef.current;
              const scrollX = (canvasX * scale) - (viewport.clientWidth / 2);
              const scrollY = (canvasY * scale) - (viewport.clientHeight / 2);
              
              viewport.scrollTo({
                left: scrollX,
                top: scrollY,
                behavior: 'auto'
              });
            }}
            onMouseUp={() => {
              setIsDraggingMinimap(false);
            }}
            onMouseLeave={() => {
              setIsDraggingMinimap(false);
            }}
          >
            <div className="w-full h-full relative" style={{ background: 'var(--theme-background)' }}>
              {/* Minimap nodes */}
              {canvasNodes.map((node) => {
                const minimapScale = 0.04;
                const x = node.position.x * minimapScale;
                const y = node.position.y * minimapScale;
                const width = 240 * minimapScale;
                const height = 100 * minimapScale;
                
                return (
                  <div
                    key={node.node_id}
                    className="absolute rounded"
                    style={{
                      left: `${x}px`,
                      top: `${y}px`,
                      width: `${width}px`,
                      height: `${height}px`,
                      background: getNodeCategoryColor(node.category),
                      opacity: 0.8,
                    }}
                  />
                );
              })}
              
              {/* Viewport indicator - moves with scroll */}
              <div
                className="absolute border-2 pointer-events-none"
                style={{
                  borderColor: 'var(--theme-primary)',
                  left: `${minimapViewport.x}px`,
                  top: `${minimapViewport.y}px`,
                  width: `${minimapViewport.width}px`,
                  height: `${minimapViewport.height}px`,
                  backgroundColor: 'rgba(59, 130, 246, 0.15)',
                  transition: 'none', // Remove transition for instant updates
                }}
              />
            </div>
          </div>
        </div>

          {/* Bottom Log Panel */}
        <div 
          ref={logPanelRef} 
          className="border-t flex flex-col shrink-0 relative" 
          style={{ 
            background: 'var(--theme-surface)', 
            borderColor: 'var(--theme-border)',
            height: isLogCollapsed ? "32px" : `${logHeight}px`, 
            minHeight: "32px", 
            maxHeight: "60vh" 
          }}
        >
          {!isLogCollapsed && (
            <div 
              className="h-2 cursor-ns-resize transition-colors absolute -top-1 left-0 right-0 z-10" 
              style={{
                background: 'transparent'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-primary)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              onMouseDown={handleResizeStart} 
              title="Drag to resize" 
            />
          )}
          <div 
            className="flex items-center justify-between px-3 py-1.5 border-b shrink-0"
            style={{ borderColor: 'var(--theme-border)' }}
          >
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold" style={{ color: 'var(--theme-text-secondary)' }}>Workflow Log</span>
            </div>
              <div className="flex items-center gap-2">
              {!isLogCollapsed && (
                <span className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>Drag top edge to resize</span>
              )}
              <button 
                onClick={() => setIsLogCollapsed(!isLogCollapsed)} 
                className="p-1 rounded transition-colors text-xs" 
                style={{ color: 'var(--theme-text-secondary)' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--theme-surface-hover)';
                  e.currentTarget.style.color = 'var(--theme-text)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = 'var(--theme-text-secondary)';
                }}
                title={isLogCollapsed ? "Expand log panel" : "Collapse log panel"}
              >
                {isLogCollapsed ? "↑" : "↓"}
              </button>
              </div>
          </div>
          {!isLogCollapsed && (
            <div 
              ref={logBodyRef} 
              className="flex-1 p-3 text-xs space-y-1 custom-scrollbar" 
              style={{ 
                overflowY: "scroll", 
                minHeight: "100px",
                color: 'var(--theme-text)'
              }}
            >
              {logs.length === 0 ? (
                <div className="text-center py-8" style={{ color: 'var(--theme-text-muted)' }}>
                  No logs yet. Run a workflow to see execution logs.
                </div>
              ) : (
                logs.map((log, idx) => (
                  <div key={idx} className="whitespace-pre-wrap">{log}</div>
                ))
              )}
            </div>
          )}
              </div>
            </div>

      {/* Configuration Panel - Slides in from right */}
      <div 
        className={`fixed top-1/2 -translate-y-1/2 transition-transform duration-300 ease-in-out z-40 rounded-l-lg overflow-hidden shadow-2xl ${
          isConfigPanelOpen ? 'right-5' : '-right-96'
        }`}
        style={{ height: '70vh', width: '384px' }}
      >
        <ConfigPanel
          selectedNode={canvasNodes.find(n => n.node_id === selectedNode) || null}
          nodeDefinition={
            selectedNode && canvasNodes.find(cn => cn.node_id === selectedNode)
              ? nodeDefinitions.find(n => {
                  const canvasNode = canvasNodes.find(cn => cn.node_id === selectedNode);
                  // Try exact match first, then try with underscores replaced
                  return n.node_type === canvasNode?.node_type || 
                         n.node_type.replace(/_/g, '') === canvasNode?.node_type.replace(/_/g, '');
                })
              : null
          }
          onConfigUpdate={handleConfigUpdate}
          onNodeUpdate={handleNodeUpdate}
          workflowNodes={canvasNodes}
          workflowConnections={connections}
          nodeDefinitions={nodeDefinitions}
          nodeExecutionData={nodeExecutionData}
          onClose={() => {
            setIsConfigPanelOpen(false);
            setSelectedNode(null);
            setCanvasNodes(prev => prev.map(n => ({ ...n, selected: false })));
          }}
        />
      </div>

      {/* Save As Modal */}
      {showSaveAsModal && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(0, 0, 0, 0.5)' }}>
          <div 
            className="rounded-lg shadow-xl w-full max-w-md"
            style={{ background: 'var(--theme-surface)' }}
          >
            <div 
              className="flex items-center justify-between p-4 border-b"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <h2 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>Save As New Workflow</h2>
              <button 
                onClick={() => setShowSaveAsModal(false)} 
                style={{ color: 'var(--theme-text-secondary)' }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--theme-text)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--theme-text-secondary)'}
              >✕</button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>
                  Workflow Name <span style={{ color: 'var(--theme-danger)' }}>*</span>
                </label>
                <input
                  type="text"
                  defaultValue={workflowName}
                  id="saveAsName"
                  className="w-full px-3 py-2 border rounded text-sm focus:outline-none"
                  style={{
                    background: 'var(--theme-surface-variant)',
                    color: 'var(--theme-text)',
                    borderColor: 'var(--theme-border)',
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                  onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                  placeholder="Enter workflow name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>
                  Description
                </label>
                <textarea
                  defaultValue={workflowDescription}
                  id="saveAsDescription"
                  rows={3}
                  className="w-full px-3 py-2 border rounded text-sm resize-y focus:outline-none"
                  style={{
                    background: 'var(--theme-surface-variant)',
                    color: 'var(--theme-text)',
                    borderColor: 'var(--theme-border)',
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                  onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                  placeholder="Enter workflow description"
                />
              </div>
            </div>
            <div 
              className="flex items-center justify-end gap-2 p-4 border-t"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <button 
                onClick={() => setShowSaveAsModal(false)} 
                className="px-4 py-2 rounded"
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: 'var(--theme-text)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
              >Cancel</button>
              <button 
                onClick={() => {
                  const nameInput = document.getElementById('saveAsName') as HTMLInputElement;
                  const descInput = document.getElementById('saveAsDescription') as HTMLTextAreaElement;
                  if (nameInput && nameInput.value.trim()) {
                    confirmSaveAs(nameInput.value.trim(), descInput?.value || '');
                  } else {
                    alert('Please enter a workflow name');
                  }
                }}
                className="px-4 py-2 text-white rounded"
                style={{ background: 'var(--theme-success)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-success-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-success)'}
              >Save</button>
            </div>
          </div>
        </div>
      )}

      {/* Save Options Modal */}
      {showSaveOptionsModal && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(0, 0, 0, 0.5)' }} onClick={() => setShowSaveOptionsModal(false)}>
          <div 
            className="rounded-lg shadow-xl w-full max-w-sm"
            style={{ background: 'var(--theme-surface)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div 
              className="flex items-center justify-between p-4 border-b"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <h2 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>
                <i className="fas fa-save mr-2"></i>
                Save Workflow
              </h2>
              <button 
                onClick={() => setShowSaveOptionsModal(false)} 
                style={{ color: 'var(--theme-text-secondary)' }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--theme-text)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--theme-text-secondary)'}
              >✕</button>
            </div>
            <div className="p-2">
              <button
                onClick={() => {
                  setShowSaveOptionsModal(false);
                  handleSaveAs();
                }}
                className="w-full text-left px-4 py-3 text-sm rounded transition-colors flex items-center gap-3"
                style={{ color: 'var(--theme-text)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <i className="fas fa-edit w-5"></i>
                <div>
                  <div className="font-medium">Save As...</div>
                  <div className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>Save with a new name</div>
                </div>
              </button>
              <button
                onClick={() => {
                  setShowSaveOptionsModal(false);
                  handleSaveCopy();
                }}
                className="w-full text-left px-4 py-3 text-sm rounded transition-colors flex items-center gap-3"
                style={{ color: 'var(--theme-text)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <i className="fas fa-copy w-5"></i>
                <div>
                  <div className="font-medium">Save a Copy</div>
                  <div className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>Create a duplicate with auto-naming</div>
                </div>
              </button>
              <div className="border-t my-2" style={{ borderColor: 'var(--theme-border)' }} />
              <button
                onClick={() => {
                  setShowSaveOptionsModal(false);
                  handleDownloadJSON();
                }}
                className="w-full text-left px-4 py-3 text-sm rounded transition-colors flex items-center gap-3"
                style={{ color: 'var(--theme-text)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <i className="fas fa-download w-5"></i>
                <div>
                  <div className="font-medium">Download JSON</div>
                  <div className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>Export workflow to file</div>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Load Options Modal */}
      {showLoadOptionsModal && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(0, 0, 0, 0.5)' }} onClick={() => setShowLoadOptionsModal(false)}>
          <div 
            className="rounded-lg shadow-xl w-full max-w-sm"
            style={{ background: 'var(--theme-surface)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div 
              className="flex items-center justify-between p-4 border-b"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <h2 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>
                <i className="fas fa-folder-open mr-2"></i>
                Load Workflow
              </h2>
              <button 
                onClick={() => setShowLoadOptionsModal(false)} 
                style={{ color: 'var(--theme-text-secondary)' }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--theme-text)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--theme-text-secondary)'}
              >✕</button>
            </div>
            <div className="p-2">
              <button
                onClick={() => {
                  setShowLoadOptionsModal(false);
                  handleLoad();
                }}
                className="w-full text-left px-4 py-3 text-sm rounded transition-colors flex items-center gap-3"
                style={{ color: 'var(--theme-text)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <i className="fas fa-database w-5"></i>
                <div>
                  <div className="font-medium">From Database</div>
                  <div className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>Load from saved workflows</div>
                </div>
              </button>
              <button
                onClick={() => {
                  setShowLoadOptionsModal(false);
                  setShowLoadFromFileModal(true);
                }}
                className="w-full text-left px-4 py-3 text-sm rounded transition-colors flex items-center gap-3"
                style={{ color: 'var(--theme-text)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <i className="fas fa-file-upload w-5"></i>
                <div>
                  <div className="font-medium">From File</div>
                  <div className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>Import JSON workflow file</div>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Load from File Modal */}
      {showLoadFromFileModal && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(0, 0, 0, 0.5)' }}>
          <div 
            className="rounded-lg shadow-xl w-full max-w-md"
            style={{ background: 'var(--theme-surface)' }}
          >
            <div 
              className="flex items-center justify-between p-4 border-b"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <h2 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>Load Workflow from File</h2>
              <button 
                onClick={() => setShowLoadFromFileModal(false)} 
                style={{ color: 'var(--theme-text-secondary)' }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--theme-text)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--theme-text-secondary)'}
              >✕</button>
            </div>
            <div className="p-4">
              <p className="text-sm mb-4" style={{ color: 'var(--theme-text-secondary)' }}>
                Select a JSON workflow file to load
              </p>
              <input
                type="file"
                accept=".json,application/json"
                onChange={handleLoadFromFile}
                className="w-full px-3 py-2 border rounded text-sm"
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: 'var(--theme-text)',
                  borderColor: 'var(--theme-border)',
                }}
              />
            </div>
            <div 
              className="flex items-center justify-end gap-2 p-4 border-t"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <button 
                onClick={() => setShowLoadFromFileModal(false)} 
                className="px-4 py-2 rounded"
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: 'var(--theme-text)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
              >Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Load Workflow Modal */}
      {showLoadModal && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(0, 0, 0, 0.5)' }}>
          <div 
            className="rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col"
            style={{ background: 'var(--theme-surface)' }}
          >
            <div 
              className="flex items-center justify-between p-4 border-b"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <h2 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>Load Workflow</h2>
              <button 
                onClick={() => setShowLoadModal(false)} 
                style={{ color: 'var(--theme-text-secondary)' }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--theme-text)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--theme-text-secondary)'}
              >✕</button>
                  </div>
            <div className="flex-1 overflow-y-auto p-4">
              {availableWorkflows.length === 0 ? (
                <div className="text-center py-8" style={{ color: 'var(--theme-text-muted)' }}>No workflows saved yet.</div>
              ) : (
                <div className="space-y-2">
                  {availableWorkflows.map((workflow) => (
                    <div 
                      key={workflow.id} 
                      onClick={() => loadWorkflowById(workflow.id)} 
                      className="p-3 rounded cursor-pointer transition-colors"
                      style={{ background: 'var(--theme-surface-variant)' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium" style={{ color: 'var(--theme-text)' }}>{workflow.name}</div>
                          <div className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>
                            {workflow.node_count || 0} nodes • Updated {new Date(workflow.updated_at).toLocaleDateString()}
                          </div>
                        </div>
                        <button 
                          className="px-3 py-1 text-white rounded text-sm"
                          style={{ background: 'var(--theme-primary)' }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-primary-hover)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-primary)'}
                        >Load</button>
                      </div>
                    </div>
                  ))}
                </div>
                )}
              </div>
            <div 
              className="flex items-center justify-end gap-2 p-4 border-t"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <button 
                onClick={() => setShowLoadModal(false)} 
                className="px-4 py-2 rounded"
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: 'var(--theme-text)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
              >Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Retry Warning Modal */}
      {execution.showRetryWarning && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(0, 0, 0, 0.5)' }}>
          <div 
            className="rounded-lg shadow-xl w-full max-w-lg"
            style={{ background: 'var(--theme-surface)' }}
          >
            <div 
              className="flex items-center justify-between p-4 border-b"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--theme-warning)' }}>
                <i className="fas fa-exclamation-triangle"></i>
                Workflow Structure Changed
              </h2>
              <button 
                onClick={execution.handleRetryCancel}
                style={{ color: 'var(--theme-text-secondary)' }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--theme-text)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--theme-text-secondary)'}
              >✕</button>
            </div>
            <div className="p-4 space-y-4">
              <p className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
                The workflow has been modified since the last execution. Retrying may produce unexpected results.
              </p>
              
              {/* List of warnings */}
              <div 
                className="rounded p-3 space-y-2 max-h-48 overflow-y-auto"
                style={{ background: 'var(--theme-surface-variant)' }}
              >
                {execution.retryWarnings.map((warning, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <i className="fas fa-info-circle mt-0.5" style={{ color: 'var(--theme-warning)' }}></i>
                    <span style={{ color: 'var(--theme-text)' }}>{warning}</span>
                  </div>
                ))}
              </div>

              <div 
                className="rounded p-3 text-sm"
                style={{ background: 'var(--theme-info-bg)', color: 'var(--theme-info)' }}
              >
                <strong>Tip:</strong> If you've fixed the failing node, you can safely retry. 
                Use "Restart" to run the entire workflow from scratch.
              </div>
            </div>
            <div 
              className="flex items-center justify-end gap-2 p-4 border-t"
              style={{ borderColor: 'var(--theme-border)' }}
            >
              <button 
                onClick={execution.handleRetryCancel}
                className="px-4 py-2 rounded text-sm"
                style={{
                  background: 'var(--theme-surface-variant)',
                  color: 'var(--theme-text)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
              >Cancel</button>
              <button 
                onClick={async () => {
                  if (isDirty) await handleSave(true);
                  execution.handleRestart();
                }}
                className="px-4 py-2 rounded text-sm border"
                style={{
                  background: 'var(--theme-surface)',
                  color: 'var(--theme-text)',
                  borderColor: 'var(--theme-border)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface)'}
              >Restart Instead</button>
              <button 
                onClick={execution.handleRetryForce}
                className="px-4 py-2 text-white rounded text-sm font-medium"
                style={{ background: 'var(--theme-warning)' }}
                onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
              >Retry Anyway</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function WorkflowEditor() {
  return (
    <Suspense fallback={<div>Loading workflow editor...</div>}>
      <WorkflowEditorInner />
    </Suspense>
  );
}


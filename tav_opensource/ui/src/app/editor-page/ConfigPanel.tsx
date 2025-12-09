/**
 * Configuration Panel Component
 * 
 * Displays and allows editing of node configuration when a node is selected.
 */

import React, { useState, useEffect, useRef } from 'react';
import { VariableOrTextInput } from './VariableOrTextInput';
import { getAvailableVariables, shouldUseVariableInput } from './utils/variableUtils';
import { FilePicker } from '@/components/FilePicker';
import { FolderPicker } from '@/components/FolderPicker';
import PasswordInput from '@/components/PasswordInput';
import CredentialPicker from '@/components/CredentialPicker';
import HuggingFaceModelBrowser from '@/components/HuggingFaceModelBrowser';
import { MediaViewerConfig } from '@/components/MediaViewerConfig';
import { MediaOutputViewer, hasMediaFormat, type MediaFormat } from '@/components/MediaOutputViewer';
import { MediaFullScreenModal, type AnnotationData } from '@/components/MediaFullScreenModal';
import type { FileCategory } from '@/lib/files';
import type { ModelDetails } from '@/lib/huggingface-api';
import { getApiBaseUrl } from '@/lib/api-config';

// ==================== KeyValue Editor Component ====================

interface KeyValueEditorProps {
  value: Record<string, string>;
  onChange: (value: Record<string, string>) => void;
  placeholder?: string;
}

function KeyValueEditor({ value, onChange, placeholder }: KeyValueEditorProps) {
  const [pairs, setPairs] = useState<Array<{ key: string; value: string; id: string }>>([]);

  // Initialize pairs from value - update when value prop changes
  useEffect(() => {
    if (value && Object.keys(value).length > 0) {
      const newPairs = Object.entries(value).map(([k, v], idx) => ({
        key: k,
        value: v,
        id: `${idx}-${k}-${Date.now()}`
      }));
      setPairs(newPairs);
    } else if (pairs.length === 0) {
      // Start with one empty pair only if no pairs exist
      setPairs([{ key: '', value: '', id: `empty-${Date.now()}` }]);
    }
  }, [value]); // Re-run when value changes

  const updatePairs = (newPairs: Array<{ key: string; value: string; id: string }>) => {
    setPairs(newPairs);
    
    // Convert to object, filter out empty keys
    const obj: Record<string, string> = {};
    newPairs.forEach(pair => {
      if (pair.key.trim()) {
        obj[pair.key] = pair.value;
      }
    });
    
    // Always call onChange to persist data
    onChange(obj);
  };

  const addPair = () => {
    updatePairs([...pairs, { key: '', value: '', id: `${Date.now()}` }]);
  };

  const removePair = (id: string) => {
    updatePairs(pairs.filter(p => p.id !== id));
  };

  const updatePair = (id: string, field: 'key' | 'value', newValue: string) => {
    updatePairs(pairs.map(p => p.id === id ? { ...p, [field]: newValue } : p));
  };

  return (
    <div className="space-y-2">
      {pairs.map((pair, idx) => (
        <div key={pair.id} className="flex gap-2">
          <input
            type="text"
            value={pair.key}
            onChange={(e) => updatePair(pair.id, 'key', e.target.value)}
            placeholder={idx === 0 && placeholder ? "Key" : "Key"}
            className="flex-1 px-3 py-2 border rounded text-sm focus:outline-none"
            style={{
              background: 'var(--theme-surface-variant)',
              color: 'var(--theme-text)',
              borderColor: 'var(--theme-border)',
            }}
            onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
            onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
          />
          <input
            type="text"
            value={pair.value}
            onChange={(e) => updatePair(pair.id, 'value', e.target.value)}
            placeholder="Value"
            className="flex-1 px-3 py-2 border rounded text-sm focus:outline-none"
            style={{
              background: 'var(--theme-surface-variant)',
              color: 'var(--theme-text)',
              borderColor: 'var(--theme-border)',
            }}
            onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
            onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
          />
          <button
            onClick={() => removePair(pair.id)}
            className="px-2 py-2 rounded text-sm hover:opacity-70 transition-opacity"
            style={{ color: 'var(--theme-danger)' }}
            title="Remove"
            disabled={pairs.length === 1}
          >
            <i className="fas fa-times"></i>
          </button>
        </div>
      ))}
      <button
        onClick={addPair}
        className="w-full px-3 py-2 border-2 border-dashed rounded text-sm hover:opacity-70 transition-opacity"
        style={{
          borderColor: 'var(--theme-border)',
          color: 'var(--theme-text-secondary)'
        }}
      >
        <i className="fas fa-plus mr-2"></i>
        Add {placeholder || 'Pair'}
      </button>
    </div>
  );
}

// ==================== Credential Picker Component ====================

interface LocalCredentialPickerProps {
  value: string | number;
  onChange: (value: number) => void;
  filter?: {
    service_type?: string;
    auth_type?: string;
  };
}

function LocalCredentialPicker({ value, onChange, filter }: LocalCredentialPickerProps) {
  const [credentials, setCredentials] = useState<Array<{
    id: number;
    name: string;
    service_type: string;
    auth_type: string;
  }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch credentials from backend
    fetch(`${getApiBaseUrl()}/api/v1/credentials`, {
      credentials: 'include'
    })
      .then(res => res.json())
      .then(data => {
        let creds = data.credentials || [];
        
        // Filter by service_type or auth_type if specified
        if (filter) {
          if (filter.service_type) {
            creds = creds.filter((c: any) => c.service_type === filter.service_type);
          }
          if (filter.auth_type) {
            creds = creds.filter((c: any) => c.auth_type === filter.auth_type);
          }
        }
        
        setCredentials(creds);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch credentials:', err);
        setLoading(false);
      });
  }, [filter]);

  if (loading) {
    return (
      <div className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
        Loading credentials...
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <select
        value={value || ''}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full px-3 py-2 border rounded text-sm focus:outline-none"
        style={{
          background: 'var(--theme-surface-variant)',
          color: 'var(--theme-text)',
          borderColor: 'var(--theme-border)',
        }}
        onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
        onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
      >
        <option value="">Select credential...</option>
        {credentials.map((cred) => (
          <option key={cred.id} value={cred.id}>
            {cred.name} ({cred.service_type})
          </option>
        ))}
      </select>
      
      {credentials.length === 0 && (
        <p className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>
          No credentials found. Create one in Settings → Credentials.
        </p>
      )}
      
      <button
        onClick={() => window.open('/credentials', '_blank')}
        className="text-xs hover:underline"
        style={{ color: 'var(--theme-primary)' }}
      >
        <i className="fas fa-plus mr-1"></i>
        Create new credential
      </button>
    </div>
  );
}

// ==================== Provider & Model Select Components ====================

interface ProviderSelectProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

function ProviderSelect({ value, onChange, placeholder }: ProviderSelectProps) {
  const [providers, setProviders] = useState<Array<{ 
    name: string; 
    provider_type: string;
    display_name: string; 
    enabled: boolean 
  }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch enabled providers from backend
    fetch(`${getApiBaseUrl()}/api/v1/ai/providers`)
      .then(res => res.json())
      .then(data => {
        // Filter to only enabled providers and convert to array
        const enabledProviders = data.providers 
          ? Object.values(data.providers).filter((p: any) => p.enabled) as Array<{ 
              name: string; 
              provider_type: string;
              display_name: string; 
              enabled: boolean 
            }>
          : [];
        setProviders(enabledProviders);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch providers:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
        Loading providers...
      </div>
    );
  }

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 border rounded text-sm focus:outline-none"
      style={{
        background: 'var(--theme-surface-variant)',
        color: 'var(--theme-text)',
        borderColor: 'var(--theme-border)',
      }}
      onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
      onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
    >
      <option value="">{placeholder || 'Default from settings'}</option>
      {providers.map((p) => (
        <option key={p.provider_type} value={p.provider_type}>
          {p.display_name}
        </option>
      ))}
    </select>
  );
}

interface ModelSelectProps {
  provider: string | null;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

function ModelSelect({ provider, value, onChange, placeholder }: ModelSelectProps) {
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!provider) {
      setModels([]);
      return;
    }

    setLoading(true);
    // Fetch available models for selected provider
    fetch(`${getApiBaseUrl()}/api/v1/ai/providers/${provider}/models`)
      .then(res => res.json())
      .then(data => {
        // Extract model IDs from the response
        const modelList = data.models?.map((m: any) => m.id || m) || [];
        setModels(modelList);
        setLoading(false);
      })
      .catch(err => {
        console.error(`Failed to fetch models for ${provider}:`, err);
        setModels([]);
        setLoading(false);
      });
  }, [provider]);

  if (!provider) {
    return (
      <div className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
        Select a provider first
      </div>
    );
  }

  if (loading) {
    return (
      <div className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
        Loading models...
      </div>
    );
  }

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 border rounded text-sm focus:outline-none"
      style={{
        background: 'var(--theme-surface-variant)',
        color: 'var(--theme-text)',
        borderColor: 'var(--theme-border)',
      }}
      onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
      onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
    >
      <option value="">{placeholder || 'Default from provider settings'}</option>
      {models.map((m) => (
        <option key={m} value={m}>
          {m}
        </option>
      ))}
    </select>
  );
}

// ====================================================================================

interface ConfigField {
  type: 'string' | 'integer' | 'float' | 'boolean' | 'select' | 'file_picker' | 'keyvalue' | 'credential' | 'object';
  label: string;
  description?: string;
  required?: boolean;
  default?: any;
  widget?: 'text' | 'textarea' | 'number' | 'checkbox' | 'select' | 'color' | 'date' | 'password' | 'provider_select' | 'model_select' | 'slider' | 'file_picker' | 'keyvalue' | 'credential' | 'huggingface_model_browser' | 'hidden';
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
  options?: Array<{ value: any; label: string }>;
  depends_on?: string;  // For dynamic fields that depend on other fields (e.g., model depends on provider)
  show_if?: Record<string, any>;  // Conditional visibility based on other field values
  visible_when?: Record<string, any>;  // Alternative to show_if (same behavior)
  group?: string;  // For grouping related fields
  allow_template?: boolean;  // Explicitly enable/disable variable/template support (overrides auto-detection)
  // File picker specific fields
  accept?: string;
  max_size_mb?: number;
  file_category?: string;
  // Credential picker specific fields
  filter?: {
    service_type?: string;
    auth_type?: string;
  };
  // Credential picker specific fields
  credential_types?: string[];  // Which credential types to show (e.g., ['api_key', 'bearer_token'])
}

interface ConfigSchema {
  [key: string]: ConfigField;
}

interface WorkflowNode {
  node_id: string;  // Changed from 'id' to match backend format
  node_type: string; // Changed from 'type' to match backend format
  name: string;
  category: string;
  config: { [key: string]: any };
  share_output_to_variables?: boolean; // Shared space feature
  variable_name?: string; // Custom variable name for shared space
  status?: string; // Node execution status
  inputs?: Array<{ id: string; label: string; type: string; required?: boolean }>;
  outputs?: Array<{ id: string; label: string; type: string }>;
}

interface NodeDefinition {
  node_type: string;
  display_name: string;
  description: string;
  category: string;
  icon?: string;
  config_schema: ConfigSchema;
}

interface ConfigPanelProps {
  selectedNode: WorkflowNode | null;
  nodeDefinition: NodeDefinition | null;
  onConfigUpdate: (nodeId: string, newConfig: { [key: string]: any }) => void;
  onNodeUpdate: (nodeId: string, updates: Partial<WorkflowNode>) => void; // For updating node-level fields
  onClose: () => void;
  // Workflow data for variable detection
  workflowNodes?: WorkflowNode[];
  workflowConnections?: Array<{ source_node_id: string; target_node_id: string }>;
  nodeDefinitions?: any[];
  nodeExecutionData?: Record<string, any>; // Add execution data
}

export function ConfigPanel({
  selectedNode,
  nodeDefinition,
  onConfigUpdate,
  onNodeUpdate,
  onClose,
  workflowNodes = [],
  workflowConnections = [],
  nodeDefinitions = [],
  nodeExecutionData = {},
}: ConfigPanelProps) {
  const [configValues, setConfigValues] = useState<{ [key: string]: any }>({});
  const [shareOutputs, setShareOutputs] = useState(false);
  const [variableName, setVariableName] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [activeTab, setActiveTab] = useState<'config' | 'output' | 'info'>('config');
  const [outputViewMode, setOutputViewMode] = useState<'formatted' | 'json'>('formatted'); // View mode for output tab
  const [isSaving, setIsSaving] = useState(false); // Track auto-save status
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastSavedNodeIdRef = useRef<string | null>(null); // Track which node we're editing
  
  // Dynamic HuggingFace task-specific config
  const [dynamicTaskConfig, setDynamicTaskConfig] = useState<Record<string, any> | null>(null);
  const [loadingTaskConfig, setLoadingTaskConfig] = useState(false);
  
  // Modal state for full-screen media viewer
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMedia, setModalMedia] = useState<MediaFormat | MediaFormat[] | null>(null);
  const [modalMode, setModalMode] = useState<'view' | 'edit'>('view');
  const [modalIndex, setModalIndex] = useState(0);
  

  
  // Handlers for opening modal
  const handleMediaClick = (media: MediaFormat | MediaFormat[], mode: 'view' | 'edit', index = 0) => {
    setModalMedia(media);
    setModalMode(mode);
    setModalIndex(index);
    setIsModalOpen(true);
  };
  
  const handleModalSave = (annotations: AnnotationData[]) => {
    // TODO: Save annotations to node config
    // For now, just close modal
    setIsModalOpen(false);
  };
  
  // Get available variables for this node
  const availableVariables = selectedNode
    ? getAvailableVariables(workflowNodes, workflowConnections, selectedNode.node_id, nodeDefinitions)
    : [];
  
  // Load dynamic task-specific config for HuggingFace nodes
  useEffect(() => {
    const loadDynamicTaskConfig = async () => {
      // Only for HuggingFace nodes (node_type: huggingface_inference)
      if (selectedNode?.node_type !== 'huggingface_inference') {
        setDynamicTaskConfig(null);
        return;
      }
      
      const marketplace = configValues.huggingface_marketplace;
      const task = marketplace?.task;
    
      
      if (!task) {
        setDynamicTaskConfig(null);
        return;
      }
      
      setLoadingTaskConfig(true);
      try {
        const { getTaskConfigSchema } = await import('@/lib/huggingface-api');
        const taskConfig = await getTaskConfigSchema(task);
        setDynamicTaskConfig(taskConfig.parameters);
      } catch (err) {
        setDynamicTaskConfig(null);
      } finally {
        setLoadingTaskConfig(false);
      }
    };
    
    loadDynamicTaskConfig();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNode?.node_type, JSON.stringify(configValues.huggingface_marketplace)]);
  
  // Debug logging
  useEffect(() => {
    if (selectedNode) {
      // Disabled debug logs
    }
  }, [selectedNode, availableVariables]);

  // Initialize config values when node is selected (but not when config updates from parent)
  useEffect(() => {
    if (selectedNode && nodeDefinition) {
      const currentNodeId = selectedNode.node_id;
      
      // Only reinitialize if switching to a different node
      if (lastSavedNodeIdRef.current !== currentNodeId) {
        lastSavedNodeIdRef.current = currentNodeId;
        
        // Merge default values with current config
        const initialConfig: { [key: string]: any } = {};
        const schema = nodeDefinition.config_schema || {};
        
        Object.keys(schema).forEach(key => {
          const field = schema[key];
          initialConfig[key] = selectedNode.config[key] ?? field.default ?? getDefaultValueForType(field.type);
        });
        
        setConfigValues(initialConfig);
        setShareOutputs(selectedNode.share_output_to_variables ?? false);
        setVariableName(selectedNode.variable_name ?? '');
        setHasChanges(false);
      }
    } else {
      // Reset when no node is selected
      lastSavedNodeIdRef.current = null;
    }
  }, [selectedNode, nodeDefinition]);

  const getDefaultValueForType = (type: string): any => {
    switch (type) {
      case 'boolean': return false;
      case 'integer':
      case 'float': return 0;
      case 'string': return '';
      default: return null;
    }
  };

  // Auto-save functionality with debouncing
  useEffect(() => {
    // Only auto-save if there are changes and we have a valid node
    if (!hasChanges || !selectedNode?.node_id) {
      return;
    }

    // Clear any existing timer
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    // Capture current values for the closure
    const nodeIdToSave = selectedNode.node_id;
    const configToSave = configValues;
    const shareOutputsToSave = shareOutputs;
    const variableNameToSave = variableName;

    // Set up a new timer to auto-save after 500ms of inactivity
    autoSaveTimerRef.current = setTimeout(() => {
      setIsSaving(true);
      
      // Use the captured values from closure to avoid stale references
      onConfigUpdate(nodeIdToSave, configToSave);
      onNodeUpdate(nodeIdToSave, {
        share_output_to_variables: shareOutputsToSave,
        variable_name: variableNameToSave || undefined,
      });
      
      setHasChanges(false);
      
      // Show saving indicator briefly
      setTimeout(() => setIsSaving(false), 300);
    }, 500);

    // Cleanup function
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
    // Only depend on the actual data values, not the callback functions
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configValues, shareOutputs, variableName, hasChanges]);

  const handleValueChange = (key: string, value: any) => {
    setConfigValues(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleReset = () => {
    if (selectedNode && nodeDefinition) {
      const schema = nodeDefinition.config_schema || {};
      const resetConfig: { [key: string]: any } = {};
      
      Object.keys(schema).forEach(key => {
        const field = schema[key];
        resetConfig[key] = field.default ?? getDefaultValueForType(field.type);
      });
      
      setConfigValues(resetConfig);
      setHasChanges(true);
    }
  };

  if (!selectedNode || !nodeDefinition) {
    // Debug logging
    
    return (
      <div 
        className="w-96 h-full flex flex-col shadow-2xl"
        style={{ background: 'var(--theme-surface)' }}
      >
        {/* Header with close button even when no node */}
        <div 
          className="flex items-center justify-between px-4 py-3 border-b"
          style={{ 
            borderColor: 'var(--theme-border)',
            background: 'var(--theme-surface-variant)'
          }}
        >
          <div className="flex items-center gap-2">
            <i className="fas fa-cog" style={{ color: 'var(--theme-text-secondary)' }}></i>
            <h2 className="text-sm font-semibold" style={{ color: 'var(--theme-text)' }}>Configuration</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded transition-colors"
            style={{ color: 'var(--theme-text-secondary)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--theme-surface-hover)';
              e.currentTarget.style.color = 'var(--theme-text)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--theme-text-secondary)';
            }}
            title="Close panel"
          >
            <i className="fas fa-times text-lg"></i>
          </button>
        </div>
        
        <div 
          className="flex-1 flex items-center justify-center p-4 text-center"
          style={{ color: 'var(--theme-text-muted)' }}
        >
          <div>
            <i className="fas fa-mouse-pointer text-4xl mb-3"></i>
            <p className="text-sm">Select a node to configure</p>
            {selectedNode && !nodeDefinition && (
              <p className="text-xs mt-2" style={{ color: 'var(--theme-danger)' }}>
                Debug: Node selected but definition not found
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  const schema = nodeDefinition.config_schema || {};
  const hasFields = Object.keys(schema).length > 0;

  return (
    <div 
      className="w-96 h-full flex flex-col shadow-2xl"
      style={{ background: 'var(--theme-surface)' }}
    >
      {/* Header */}
      <div 
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ 
          borderColor: 'var(--theme-border)',
          background: 'var(--theme-surface-variant)'
        }}
      >
        <div className="flex items-center gap-2">
          <i className="fas fa-cog" style={{ color: 'var(--theme-text-secondary)' }}></i>
          <h2 className="text-sm font-semibold" style={{ color: 'var(--theme-text)' }}>Configuration</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded transition-colors"
          style={{ color: 'var(--theme-text-secondary)' }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--theme-surface-hover)';
            e.currentTarget.style.color = 'var(--theme-text)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'var(--theme-text-secondary)';
          }}
          title="Close panel"
        >
          <i className="fas fa-times text-lg"></i>
        </button>
      </div>

      {/* Node Info */}
      <div 
        className="px-4 py-3 border-b"
        style={{ 
          background: 'var(--theme-surface-variant)',
          borderColor: 'var(--theme-border)'
        }}
      >
        <div className="flex items-start gap-3">
          {nodeDefinition.icon && (
            <div 
              className="flex-shrink-0 w-10 h-10 rounded flex items-center justify-center"
              style={{ background: 'var(--theme-primary-muted)' }}
            >
              <i className={nodeDefinition.icon} style={{ color: 'var(--theme-primary)' }}></i>
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold truncate" style={{ color: 'var(--theme-text)' }}>
              {selectedNode.name}
            </h3>
            <p className="text-xs mt-0.5" style={{ color: 'var(--theme-text-secondary)' }}>
              {nodeDefinition.description}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div 
        className="flex border-b"
        style={{ 
          borderColor: 'var(--theme-border)',
          background: 'var(--theme-surface-variant)'
        }}
      >
        <button
          onClick={() => setActiveTab('config')}
          className="flex-1 px-4 py-2.5 text-sm font-medium transition-colors relative"
          style={{ 
            color: activeTab === 'config' ? 'var(--theme-primary)' : 'var(--theme-text-secondary)',
            borderBottom: activeTab === 'config' ? '2px solid var(--theme-primary)' : '2px solid transparent',
          }}
          onMouseEnter={(e) => {
            if (activeTab !== 'config') {
              e.currentTarget.style.color = 'var(--theme-text)';
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== 'config') {
              e.currentTarget.style.color = 'var(--theme-text-secondary)';
            }
          }}
        >
          <i className="fas fa-cog mr-1.5"></i>
          Config
        </button>
        <button
          onClick={() => setActiveTab('output')}
          className="flex-1 px-4 py-2.5 text-sm font-medium transition-colors relative"
          style={{ 
            color: activeTab === 'output' ? 'var(--theme-primary)' : 'var(--theme-text-secondary)',
            borderBottom: activeTab === 'output' ? '2px solid var(--theme-primary)' : '2px solid transparent',
          }}
          onMouseEnter={(e) => {
            if (activeTab !== 'output') {
              e.currentTarget.style.color = 'var(--theme-text)';
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== 'output') {
              e.currentTarget.style.color = 'var(--theme-text-secondary)';
            }
          }}
        >
          <i className="fas fa-chart-bar mr-1.5"></i>
          Output
        </button>
        <button
          onClick={() => setActiveTab('info')}
          className="flex-1 px-4 py-2.5 text-sm font-medium transition-colors relative"
          style={{ 
            color: activeTab === 'info' ? 'var(--theme-primary)' : 'var(--theme-text-secondary)',
            borderBottom: activeTab === 'info' ? '2px solid var(--theme-primary)' : '2px solid transparent',
          }}
          onMouseEnter={(e) => {
            if (activeTab !== 'info') {
              e.currentTarget.style.color = 'var(--theme-text)';
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== 'info') {
              e.currentTarget.style.color = 'var(--theme-text-secondary)';
            }
          }}
        >
          <i className="fas fa-info-circle mr-1.5"></i>
          Info
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'config' && (
        <>
      <div 
        className="px-4 py-3 border-b space-y-3"
        style={{ 
          borderColor: 'var(--theme-border)',
          background: 'var(--theme-surface)'
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={shareOutputs}
                onChange={(e) => {
                  setShareOutputs(e.target.checked);
                  setHasChanges(true);
                }}
                className="w-4 h-4 border rounded"
                style={{
                  accentColor: 'var(--theme-primary)'
                }}
              />
              <span className="text-sm font-medium" style={{ color: 'var(--theme-text)' }}>
                Share output to variables
              </span>
            </label>
            <p className="text-xs mt-1 ml-6" style={{ color: 'var(--theme-text-muted)' }}>
              Make node outputs available to all subsequent nodes
            </p>
          </div>
        </div>

        {shareOutputs && (
          <div className="ml-6 space-y-1">
            <label className="block text-xs font-medium" style={{ color: 'var(--theme-text-secondary)' }}>
              Variable Name (optional)
            </label>
            <input
              type="text"
              value={variableName}
              onChange={(e) => {
                setVariableName(e.target.value);
                setHasChanges(true);
              }}
              placeholder={selectedNode?.node_id || 'node_id'}
              className="w-full px-2 py-1.5 border rounded text-xs focus:outline-none"
              style={{
                background: 'var(--theme-surface-variant)',
                color: 'var(--theme-text)',
                borderColor: 'var(--theme-border)',
              }}
              onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
              onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
            />
            <p className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>
              Custom identifier for accessing this node's data. Defaults to node ID.
            </p>
          </div>
        )}
      </div>

      {/* Config Fields */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {!hasFields ? (
          <div className="p-4 text-center" style={{ color: 'var(--theme-text-muted)' }}>
            <i className="fas fa-info-circle text-2xl mb-2"></i>
            <p className="text-sm">This node has no configuration options</p>
          </div>
        ) : (
          <div className="p-4 space-y-4">
            {Object.entries(schema).map(([key, field]) => {
              // Check if field should be visible based on show_if conditions
              const shouldShow = checkShowIf(field, configValues);
              
              // Skip hidden fields (these are rendered dynamically elsewhere)
              if (field.widget === 'hidden' || !shouldShow) {
                return null;
              }
              
              return (
                <div key={key} className="space-y-1">
                  <label className="block text-sm font-medium" style={{ color: 'var(--theme-text)' }}>
                    {field.label}
                    {field.required && <span className="ml-1" style={{ color: 'var(--theme-danger)' }}>*</span>}
                  </label>
                  
                  {field.description && (
                    <p className="text-xs mb-2" style={{ color: 'var(--theme-text-muted)' }}>
                      {field.description}
                    </p>
                  )}

                  {/* Use VariableOrTextInput for string fields if variables are available */}
                  {(() => {
                    const useVariableInput = shouldUseVariableInput(field);
                    const hasVars = availableVariables.length > 0;
                    
                    
                    if (useVariableInput && hasVars) {
                      return (
                        <VariableOrTextInput
                          label={field.label}
                          value={configValues[key]}
                          onChange={(value) => handleValueChange(key, value)}
                          availableVariables={availableVariables}
                          widget={field.widget as 'text' | 'textarea' | 'password'}
                          placeholder={field.placeholder}
                          required={field.required}
                          description={field.description}
                        />
                      );
                    } else {
                      return renderField(key, field, configValues[key], handleValueChange, configValues, handleMediaClick);
                    }
                  })()}
                </div>
              );
            })}
            
            {/* Dynamic Task-Specific Configuration */}
            {selectedNode?.node_type === 'huggingface_inference' && dynamicTaskConfig && (
              <div className="border-t pt-4 mt-4" style={{ borderColor: 'var(--theme-border)' }}>
                <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--theme-text)' }}>
                  <i className="fas fa-sliders-h mr-2" style={{ color: 'var(--theme-primary)' }}></i>
                  Task-Specific Parameters ({configValues.huggingface_marketplace?.task})
                </h4>
                
                {Object.entries(dynamicTaskConfig).map(([paramKey, paramField]: [string, any]) => (
                  <div key={paramKey} className="space-y-1 mb-3">
                    <label className="block text-sm font-medium" style={{ color: 'var(--theme-text)' }}>
                      {paramField.label}
                      {paramField.required && <span className="ml-1" style={{ color: 'var(--theme-danger)' }}>*</span>}
                    </label>
                    
                    {paramField.description && (
                      <p className="text-xs mb-2" style={{ color: 'var(--theme-text-muted)' }}>
                        {paramField.description}
                      </p>
                    )}
                    
                    {renderField(
                      paramKey,
                      paramField,
                      configValues.common_parameters?.[paramKey] || configValues.task_specific_parameters?.[paramKey],
                      (key, value) => {
                        // Store in the appropriate nested object
                        const targetObj = paramField.applicable_tasks ? 'common_parameters' : 'task_specific_parameters';
                        setConfigValues(prev => ({
                          ...prev,
                          [targetObj]: {
                            ...prev[targetObj],
                            [key]: value
                          }
                        }));
                        setHasChanges(true);
                      },
                      configValues,
                      handleMediaClick
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {loadingTaskConfig && (
              <div className="text-center py-3" style={{ color: 'var(--theme-text-muted)' }}>
                <i className="fas fa-spinner fa-spin mr-2"></i>
                Loading task-specific configuration...
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Status - No manual save button needed with auto-save */}
      {hasFields && (
        <div 
          className="px-4 py-3 border-t"
          style={{ 
            borderColor: 'var(--theme-border)',
            background: 'var(--theme-surface-variant)'
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              {isSaving ? (
                <p className="text-xs flex items-center gap-2" style={{ color: 'var(--theme-success)' }}>
                  <i className="fas fa-check-circle"></i>
                  <span>Changes saved</span>
                </p>
              ) : hasChanges ? (
                <p className="text-xs flex items-center gap-2" style={{ color: 'var(--theme-info)' }}>
                  <i className="fas fa-circle-notch fa-spin"></i>
                  <span>Saving changes...</span>
                </p>
              ) : (
                <p className="text-xs flex items-center gap-2" style={{ color: 'var(--theme-text-muted)' }}>
                  <i className="fas fa-info-circle"></i>
                  <span>Changes auto-save</span>
                </p>
              )}
            </div>
            <button
              onClick={handleReset}
              className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
              style={{
                background: 'var(--theme-surface-hover)',
                color: 'var(--theme-text-secondary)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--theme-surface)';
                e.currentTarget.style.color = 'var(--theme-text)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--theme-surface-hover)';
                e.currentTarget.style.color = 'var(--theme-text-secondary)';
              }}
              title="Reset to defaults"
            >
              <i className="fas fa-undo mr-1"></i>
              Reset
            </button>
          </div>
        </div>
      )}
      </>
      )}

      {/* Output Tab */}
      {activeTab === 'output' && (
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {(() => {
              const executionData = nodeExecutionData[selectedNode.node_id];
              
              if (!executionData) {
                return (
                  <div className="text-center py-8 px-4" style={{ color: 'var(--theme-text-muted)' }}>
                    <i className="fas fa-chart-bar text-4xl mb-3" style={{ opacity: 0.5 }}></i>
                    <p className="text-sm">Node output will appear here after execution</p>
                    <p className="text-xs mt-2">Run the workflow to see the results</p>
                  </div>
                );
              }

              return (
                <div className="p-4 space-y-4">
                  {/* Execution Status */}
                  <div className="pb-3 border-b" style={{ borderColor: 'var(--theme-border)' }}>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-semibold" style={{ color: 'var(--theme-text)' }}>
                        Execution Status
                      </h4>
                      <span 
                        className="px-2 py-1 rounded text-xs font-medium"
                        style={{
                          background: executionData.success ? 'var(--theme-success-muted)' : 'var(--theme-danger-muted)',
                          color: executionData.success ? 'var(--theme-success)' : 'var(--theme-danger)'
                        }}
                      >
                        {executionData.success ? 'Success' : 'Failed'}
                      </span>
                    </div>
                    {executionData.error && (
                      <div 
                        className="text-xs p-2 rounded mt-2"
                        style={{ 
                          background: 'var(--theme-danger-muted)', 
                          color: 'var(--theme-danger)' 
                        }}
                      >
                        <i className="fas fa-exclamation-triangle mr-1"></i>
                        {executionData.error}
                      </div>
                    )}
                  </div>

                  {/* Input Data */}
                  {executionData.inputs && Object.keys(executionData.inputs).length > 0 && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-semibold" style={{ color: 'var(--theme-text)' }}>
                          <i className="fas fa-sign-in-alt mr-1.5" style={{ color: 'var(--theme-primary)' }}></i>
                          Input Data
                        </h4>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(JSON.stringify(executionData.inputs, null, 2));
                          }}
                          className="text-xs px-2 py-1 rounded transition-colors"
                          style={{ 
                            background: 'var(--theme-surface-variant)',
                            color: 'var(--theme-text-secondary)'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
                          title="Copy to clipboard"
                        >
                          <i className="fas fa-copy mr-1"></i>
                          Copy
                        </button>
                      </div>
                      <pre 
                        className="text-xs p-3 rounded overflow-x-auto font-mono"
                        style={{ 
                          background: 'var(--theme-surface-variant)',
                          color: 'var(--theme-text)',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          overflowWrap: 'break-word'
                        }}
                      >
                        {JSON.stringify(executionData.inputs, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Output Data */}
                  {executionData.outputs && Object.keys(executionData.outputs).length > 0 && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-semibold" style={{ color: 'var(--theme-text)' }}>
                          <i className="fas fa-sign-out-alt mr-1.5" style={{ color: 'var(--theme-success)' }}></i>
                          Output Data
                        </h4>
                        <div className="flex gap-2">
                          {/* Toggle between formatted and JSON view */}
                          <button
                            onClick={() => setOutputViewMode(outputViewMode === 'formatted' ? 'json' : 'formatted')}
                            className="text-xs px-2 py-1 rounded transition-colors"
                            style={{ 
                              background: 'var(--theme-surface-variant)',
                              color: 'var(--theme-text-secondary)'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
                            title={outputViewMode === 'formatted' ? 'Show JSON' : 'Show formatted view'}
                          >
                            <i className={`fas fa-${outputViewMode === 'formatted' ? 'code' : 'eye'} mr-1`}></i>
                            {outputViewMode === 'formatted' ? 'JSON' : 'Formatted'}
                          </button>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(JSON.stringify(executionData.outputs, null, 2));
                            }}
                            className="text-xs px-2 py-1 rounded transition-colors"
                            style={{ 
                              background: 'var(--theme-surface-variant)',
                              color: 'var(--theme-text-secondary)'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
                            title="Copy to clipboard"
                          >
                            <i className="fas fa-copy mr-1"></i>
                            Copy
                          </button>
                        </div>
                      </div>

                      {outputViewMode === 'json' ? (
                        <pre 
                          className="text-xs p-3 rounded overflow-x-auto font-mono"
                          style={{ 
                            background: 'var(--theme-surface-variant)',
                            color: 'var(--theme-text)',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            overflowWrap: 'break-word'
                          }}
                        >
                          {JSON.stringify(executionData.outputs, null, 2)}
                        </pre>
                      ) : (
                        <div className="space-y-3">
                          {Object.entries(executionData.outputs).map(([portName, portData]) => {
                            // Try to render as MediaFormat first
                            const hasMedia = hasMediaFormat(portData);
                            
                            if (hasMedia) {
                              return (
                                <div key={portName} className="p-3 rounded" style={{ background: 'var(--theme-surface-variant)' }}>
                                  <MediaOutputViewer 
                                    data={portData} 
                                    portName={portName}
                                    onMediaClick={(media, index) => handleMediaClick(media, 'view', index)}
                                  />
                                </div>
                              );
                            }
                            
                            // Otherwise show as JSON
                            return (
                              <div key={portName}>
                                <div className="text-xs font-semibold mb-2" style={{ color: 'var(--theme-text-secondary)' }}>
                                  {portName}:
                                </div>
                                <pre 
                                  className="text-xs p-3 rounded overflow-x-auto font-mono"
                                  style={{ 
                                    background: 'var(--theme-surface-variant)',
                                    color: 'var(--theme-text)',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    overflowWrap: 'break-word'
                                  }}
                                >
                                  {typeof portData === 'string' 
                                    ? portData 
                                    : JSON.stringify(portData, null, 2)
                                  }
                                </pre>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Preview Data (if available) */}
                  {executionData.outputs?.preview_data && (
                    <div>
                      <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--theme-text)' }}>
                        <i className="fas fa-eye mr-1.5" style={{ color: 'var(--theme-info)' }}></i>
                        Preview
                      </h4>
                      <div 
                        className="text-sm p-3 rounded"
                        style={{ 
                          background: 'var(--theme-surface-variant)',
                          color: 'var(--theme-text)',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          overflowWrap: 'break-word'
                        }}
                      >
                        {typeof executionData.outputs.preview_data === 'string' 
                          ? executionData.outputs.preview_data 
                          : JSON.stringify(executionData.outputs.preview_data, null, 2)
                        }
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* Info Tab */}
      {activeTab === 'info' && (
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--theme-text)' }}>
                Node Information
              </h4>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--theme-border)' }}>
                  <span style={{ color: 'var(--theme-text-secondary)' }}>Node ID:</span>
                  <span style={{ color: 'var(--theme-text)' }} className="font-mono text-xs truncate ml-2 max-w-[200px]" title={selectedNode.node_id}>
                    {selectedNode.node_id}
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--theme-border)' }}>
                  <span style={{ color: 'var(--theme-text-secondary)' }}>Node Type:</span>
                  <span style={{ color: 'var(--theme-text)' }}>{selectedNode.node_type}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--theme-border)' }}>
                  <span style={{ color: 'var(--theme-text-secondary)' }}>Category:</span>
                  <span style={{ color: 'var(--theme-text)' }}>{selectedNode.category}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--theme-border)' }}>
                  <span style={{ color: 'var(--theme-text-secondary)' }}>Status:</span>
                  <span style={{ color: 'var(--theme-text)' }}>{selectedNode.status || 'idle'}</span>
                </div>
              </div>
            </div>

            {(selectedNode.inputs && selectedNode.inputs.length > 0) && (
              <div>
                <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--theme-text)' }}>
                  Input Ports ({selectedNode.inputs.length})
                </h4>
                <div className="space-y-1">
                  {selectedNode.inputs.map((input: any) => (
                    <div key={input.id} className="text-xs px-2 py-1.5 rounded" style={{ background: 'var(--theme-surface-variant)' }}>
                      <div className="font-medium" style={{ color: 'var(--theme-text)' }}>{input.label}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span style={{ color: 'var(--theme-text-muted)' }}>Type: {input.type}</span>
                        {input.required && (
                          <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'var(--theme-danger)', color: 'white' }}>Required</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(selectedNode.outputs && selectedNode.outputs.length > 0) && (
              <div>
                <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--theme-text)' }}>
                  Output Ports ({selectedNode.outputs.length})
                </h4>
                <div className="space-y-1">
                  {selectedNode.outputs.map((output: any) => (
                    <div key={output.id} className="text-xs px-2 py-1.5 rounded" style={{ background: 'var(--theme-surface-variant)' }}>
                      <div className="font-medium" style={{ color: 'var(--theme-text)' }}>{output.label}</div>
                      <div style={{ color: 'var(--theme-text-muted)' }} className="mt-0.5">Type: {output.type}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Full-Screen Media Modal */}
      {modalMedia && (
        <MediaFullScreenModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          mediaData={modalMedia}
          mode={modalMode}
          initialIndex={modalIndex}
          onSave={handleModalSave}
        />
      )}
    </div>
  );
}

function renderField(
  key: string,
  field: ConfigField,
  value: any,
  onChange: (key: string, value: any) => void,
  configValues: Record<string, any>,
  onMediaClick?: (media: MediaFormat | MediaFormat[], mode: 'view' | 'edit', index?: number) => void
) {
  const widget = field.widget || getDefaultWidget(field.type);

  switch (widget) {
    case 'textarea':
      return (
        <textarea
          value={value || ''}
          onChange={(e) => onChange(key, e.target.value)}
          placeholder={field.placeholder}
          className="w-full px-3 py-2 border rounded text-sm resize-y min-h-[80px] focus:outline-none"
          style={{
            background: 'var(--theme-surface-variant)',
            color: 'var(--theme-text)',
            borderColor: 'var(--theme-border)',
          }}
          onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
          onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
          rows={4}
        />
      );

    case 'number':
      return (
        <input
          type="number"
          value={value ?? ''}
          onChange={(e) => {
            const val = e.target.value === '' ? null : (field.type === 'integer' ? parseInt(e.target.value) : parseFloat(e.target.value));
            onChange(key, val);
          }}
          min={field.min}
          max={field.max}
          placeholder={field.placeholder}
          className="w-full px-3 py-2 border rounded text-sm focus:outline-none"
          style={{
            background: 'var(--theme-surface-variant)',
            color: 'var(--theme-text)',
            borderColor: 'var(--theme-border)',
          }}
          onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
          onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
        />
      );

    case 'checkbox':
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => onChange(key, e.target.checked)}
            className="w-4 h-4 border rounded"
            style={{
              accentColor: 'var(--theme-primary)'
            }}
          />
          <span className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
            {field.label}
          </span>
        </label>
      );

    case 'select':
      return (
        <select
          value={value || ''}
          onChange={(e) => onChange(key, e.target.value)}
          className="w-full px-3 py-2 border rounded text-sm focus:outline-none"
          style={{
            background: 'var(--theme-surface-variant)',
            color: 'var(--theme-text)',
            borderColor: 'var(--theme-border)',
          }}
          onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
          onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
        >
          <option value="">Select...</option>
          {field.options?.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      );
    
    case 'provider_select':
      return <ProviderSelect value={value || ''} onChange={(val) => onChange(key, val)} placeholder={field.placeholder} />;
    
    case 'model_select':
      // Model select depends on provider - get provider value from config
      const providerValue = field.depends_on ? configValues[field.depends_on] : null;
      return <ModelSelect provider={providerValue} value={value || ''} onChange={(val) => onChange(key, val)} placeholder={field.placeholder} />;
    
    case 'slider':
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <input
              type="range"
              value={value ?? field.default ?? 0}
              onChange={(e) => onChange(key, parseFloat(e.target.value))}
              min={field.min ?? 0}
              max={field.max ?? 1}
              step={field.step ?? 0.01}
              className="flex-1"
              style={{
                accentColor: 'var(--theme-primary)'
              }}
            />
            <input
              type="number"
              value={value ?? field.default ?? 0}
              onChange={(e) => onChange(key, parseFloat(e.target.value))}
              min={field.min ?? 0}
              max={field.max ?? 1}
              step={field.step ?? 0.01}
              className="w-20 px-2 py-1 border rounded text-sm text-center"
              style={{
                background: 'var(--theme-surface-variant)',
                color: 'var(--theme-text)',
                borderColor: 'var(--theme-border)',
              }}
            />
          </div>
        </div>
      );

    case 'color':
      return (
        <div className="flex gap-2">
          <input
            type="color"
            value={value || '#000000'}
            onChange={(e) => onChange(key, e.target.value)}
            className="w-12 h-10 border rounded cursor-pointer"
            style={{ borderColor: 'var(--theme-border)' }}
          />
          <input
            type="text"
            value={value || ''}
            onChange={(e) => onChange(key, e.target.value)}
            placeholder="#000000"
            className="flex-1 px-3 py-2 border rounded text-sm focus:outline-none"
            style={{
              background: 'var(--theme-surface-variant)',
              color: 'var(--theme-text)',
              borderColor: 'var(--theme-border)',
            }}
            onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
            onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
          />
        </div>
      );

    case 'date':
      return (
        <input
          type="date"
          value={value || ''}
          onChange={(e) => onChange(key, e.target.value)}
          className="w-full px-3 py-2 border rounded text-sm focus:outline-none"
          style={{
            background: 'var(--theme-surface-variant)',
            color: 'var(--theme-text)',
            borderColor: 'var(--theme-border)',
          }}
          onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
          onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
        />
      );

    case 'file_picker':
      return (
        <div className="space-y-3">
          <FilePicker
            value={value || ''}
            onChange={(fileId, file) => {
              onChange(key, fileId);
            }}
            accept={field.accept}
            maxSizeMB={field.max_size_mb}
            fileCategory={field.file_category as FileCategory}
            placeholder={field.placeholder || 'Select or upload a file'}
          />
          {/* Media Preview - Supports all media types */}
          {value && (
            <MediaViewerConfig
              fileId={value}
              fileCategory={field.file_category as FileCategory}
              accept={field.accept}
              height="500px"
              onClick={() => {
                // Create MediaFormat from file picker data
                const mediaFormat: MediaFormat = {
                  type: (field.file_category as any) || 'document',
                  format: field.accept?.split(',')[0]?.replace('.', '') || 'pdf',
                  data: value,
                  data_type: 'file_path',
                  metadata: {
                    file_id: value,
                  },
                };
                onMediaClick?.(mediaFormat, 'edit');
              }}
            />
          )}
        </div>
      );

    case 'folder_picker':
      return (
        <FolderPicker
          value={value || ''}
          onChange={(folderPath) => {
            onChange(key, folderPath);
          }}
          placeholder={field.placeholder || 'Select a folder'}
        />
      );

    case 'password':
      return (
        <PasswordInput
          value={value || ''}
          onChange={(val) => onChange(key, val)}
          placeholder={field.placeholder || 'Enter password or API key'}
        />
      );

    case 'keyvalue':
      return <KeyValueEditor value={value || {}} onChange={(val) => onChange(key, val)} placeholder={field.placeholder} />;

    case 'credential':
      return <LocalCredentialPicker value={value || ''} onChange={(val) => onChange(key, val)} filter={field.filter} />;

    case 'huggingface_model_browser':
      return (
        <HuggingFaceModelBrowser
          onModelSelected={(model: ModelDetails) => {
            // Store the entire model object in config
            onChange(key, {
              model_id: model.model_id,
              task: model.pipeline_tag,
              model_info: model,
            });
          }}
          initialModelId={value?.model_id}
          enableFilters={true}
          itemsPerPage={20}
        />
      );

    case 'text':
    default:
      return (
        <input
          type="text"
          value={value || ''}
          onChange={(e) => onChange(key, e.target.value)}
          placeholder={field.placeholder}
          className="w-full px-3 py-2 border rounded text-sm focus:outline-none"
          style={{
            background: 'var(--theme-surface-variant)',
            color: 'var(--theme-text)',
            borderColor: 'var(--theme-border)',
          }}
          onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
          onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
        />
      );
  }
}

function getDefaultWidget(type: string): string {
  switch (type) {
    case 'boolean': return 'checkbox';
    case 'integer':
    case 'float': return 'number';
    case 'string': return 'text';
    default: return 'text';
  }
}

/**
 * Check if a field should be shown based on show_if or visible_when conditions
 * show_if format: { fieldName: expectedValue, ... }
 * visible_when format: { fieldName: expectedValue or [value1, value2] }
 * All conditions must be met (AND logic)
 */
function checkShowIf(field: ConfigField, configValues: Record<string, any>): boolean {
  const conditions = field.show_if || field.visible_when;
  
  if (!conditions) {
    return true; // No conditions, always show
  }
  
  // Check all conditions (AND logic)
  for (const [conditionField, expectedValue] of Object.entries(conditions)) {
    const actualValue = configValues[conditionField];
    
    // Handle array of values (OR logic within the field)
    if (Array.isArray(expectedValue)) {
      if (!expectedValue.includes(actualValue)) {
        return false; // Value not in expected list
      }
    } else {
      // Single value comparison
      if (actualValue !== expectedValue) {
        return false; // Condition not met
      }
    }
  }
  
  return true; // All conditions met
}


/**
 * Workflow Editor API Integration
 * Handles all backend API calls for the workflow editor
 */

import { getApiBaseUrl } from './api-config';
import { apiFetch } from './api';

// ===== WORKFLOW CRUD =====

/**
 * Create a new workflow
 */
export async function createWorkflow(workflow: any): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/workflows`, {
    method: 'POST',
    body: JSON.stringify(workflow),
  });
}

/**
 * Get all workflows (for Load dialog)
 */
export async function listWorkflows(): Promise<any[]> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/workflows`);
}

/**
 * Get a single workflow by ID
 */
export async function getWorkflow(id: string): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/workflows/${id}`);
}

/**
 * Update a workflow
 */
export async function updateWorkflow(id: string, workflow: any): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/workflows/${id}`, {
    method: 'PUT',
    body: JSON.stringify(workflow),
  });
}

/**
 * Delete a workflow
 */
export async function deleteWorkflow(id: string): Promise<void> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/workflows/${id}`, {
    method: 'DELETE',
  });
}

// ===== EXECUTION CONTROL =====

/**
 * Execute a workflow (Run button)
 */
export async function executeWorkflow(workflowId: string, triggerData?: any): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/workflows/${workflowId}/execute`, {
    method: 'POST',
    body: JSON.stringify({ trigger_data: triggerData }),
  });
}

/**
 * Stop a workflow
 */
export async function stopWorkflow(workflowId: string): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/workflows/${workflowId}/stop`, {
    method: 'POST',
  });
}

/**
 * Pause a workflow
 */
export async function pauseWorkflow(workflowId: string): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/workflows/${workflowId}/pause`, {
    method: 'POST',
  });
}

/**
 * Resume a workflow
 */
export async function resumeWorkflow(workflowId: string): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/workflows/${workflowId}/resume`, {
    method: 'POST',
  });
}

/**
 * Retry execution from checkpoint
 * Creates new execution that skips already-completed nodes
 */
export async function retryExecution(executionId: string, force: boolean = false): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/executions/${executionId}/retry?force=${force}`, {
    method: 'POST',
  });
}

/**
 * Get retry info for an execution
 * Returns information about what nodes would be skipped and any structure warnings
 */
export async function getRetryInfo(executionId: string): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/executions/${executionId}/retry-info`);
}

// ===== NODE DEFINITIONS =====

/**
 * Get node definitions from backend
 */
export async function fetchNodeDefinitions(): Promise<any> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/nodes/definitions`);
}

// ===== SSE STREAMING =====

/**
 * Stream execution events via SSE (for one-shot workflows)
 * Returns a cleanup function to close the connection
 */
export function streamExecutionEvents(
  executionId: string,
  onEvent: (event: any) => void,
  onError?: (error: Error) => void
): () => void {
  const url = `${getApiBaseUrl()}/api/v1/executions/${executionId}/stream`;
  const eventSource = new EventSource(url);
  let receivedTerminalEvent = false;
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      
      // Track if we received a terminal event
      if (['execution_complete', 'execution_failed', 'execution_stopped'].includes(data.type)) {
        receivedTerminalEvent = true;
      }
      
      onEvent(data);
    } catch (error) {
      console.error('Failed to parse SSE event:', error);
      onError?.(error as Error);
    }
  };
  
  eventSource.onerror = (error) => {
    // Only treat as error if we didn't receive a terminal event
    // (terminal events close the connection normally)
    if (!receivedTerminalEvent) {
      // Give a tiny delay to let any pending messages process
      setTimeout(() => {
        if (!receivedTerminalEvent) {
          console.error('SSE connection error:', error);
          onError?.(new Error('SSE connection failed'));
        }
      }, 50);
    }
    eventSource.close();
  };
  
  // Return cleanup function
  return () => {
    eventSource.close();
  };
}

/**
 * Stream workflow events via SSE (for monitoring/trigger workflows)
 * Returns a cleanup function to close the connection
 */
export function streamWorkflowEvents(
  workflowId: string,
  onEvent: (event: any) => void,
  onError?: (error: Error) => void
): () => void {
  const url = `${getApiBaseUrl()}/api/v1/executions/workflow/${workflowId}/stream`;
  console.log('[streamWorkflowEvents] Connecting to:', url);
  
  const eventSource = new EventSource(url);
  
  eventSource.onopen = () => {
    console.log('[streamWorkflowEvents] Connection opened');
  };
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('[streamWorkflowEvents] Message received:', data);
      onEvent(data);
    } catch (error) {
      console.error('[streamWorkflowEvents] Failed to parse SSE event:', error);
      onError?.(error as Error);
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('[streamWorkflowEvents] SSE connection error:', error);
    console.error('[streamWorkflowEvents] EventSource readyState:', eventSource.readyState);
    onError?.(new Error('SSE connection failed'));
    eventSource.close();
  };
  
  // Return cleanup function
  return () => {
    console.log('[streamWorkflowEvents] Closing connection');
    eventSource.close();
  };
}

// ===== SETTINGS API =====

/**
 * UI Settings interface (matches backend schema)
 */
export interface UISettings {
  default_theme_mode: "light" | "dark" | "default";
  default_grid_size: number;
  enable_grid: boolean;
  grid_opacity: number;
  auto_save_enabled: boolean;
  auto_save_delay: number;
}

/**
 * Get UI settings from backend
 */
export async function getUISettings(): Promise<UISettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/ui`);
}

/**
 * Update UI settings in backend
 */
export async function updateUISettings(settings: UISettings): Promise<UISettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/ui`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

/**
 * Security Settings interface
 */
export interface SecuritySettings {
  max_content_length: number;
}

/**
 * Get security settings from backend
 */
export async function getSecuritySettings(): Promise<SecuritySettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/security`);
}

/**
 * Update security settings in backend
 */
export async function updateSecuritySettings(settings: SecuritySettings): Promise<SecuritySettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/security`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

/**
 * Developer Settings interface
 */
export interface DeveloperSettings {
  enable_dev_mode: boolean;
  debug_mode: boolean;
  console_logging: boolean;
  error_details: boolean;
  api_timing: boolean;
  memory_monitoring: boolean;
}

/**
 * Get developer settings from backend
 */
export async function getDeveloperSettings(): Promise<DeveloperSettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/developer`);
}

/**
 * Update developer settings in backend
 */
export async function updateDeveloperSettings(settings: DeveloperSettings): Promise<DeveloperSettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/developer`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

/**
 * Storage Settings interface
 */
export interface StorageSettings {
  auto_cleanup: boolean;
  temp_file_cleanup: boolean;
  cleanup_on_startup: boolean;
  upload_dir: string;
  upload_storage_days: number;
  uploads_cleanup_interval_hours: number;
  artifact_dir: string;
  artifact_ttl_days: number;
  artifact_cleanup_interval_hours: number;
  artifact_max_bytes: number;
  artifact_backend: 'fs' | 's3' | 'gcs';
  temp_dir: string;
  temp_cleanup_interval_hours: number;
  temp_file_max_age_hours: number;
  result_storage_days: number;
}

/**
 * Get storage settings from backend
 */
export async function getStorageSettings(): Promise<StorageSettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/storage`);
}

/**
 * Update storage settings in backend
 */
export async function updateStorageSettings(settings: StorageSettings): Promise<StorageSettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/storage`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

/**
 * Execution Settings interface
 */
export interface ExecutionSettings {
  // Concurrency & Performance
  max_concurrent_nodes: number;
  ai_concurrent_limit: number;
  max_concurrent_runs_global: number;
  max_concurrent_runs_per_workflow: number;
  max_queue_depth_per_workflow: number;
  
  // Timeouts & Limits
  default_timeout: number;
  http_timeout: number;
  workflow_timeout: number;
  
  // Retry & Error Handling
  error_handling: "stop_on_error" | "continue_on_error";
  max_retries: number;
  retry_delay: number;
  backoff_multiplier: number;
  max_retry_delay: number;
  
  // Triggers & Monitoring
  trigger_max_executions: number;
  auto_restart_triggers: boolean;
}

/**
 * Get execution settings from backend
 */
export async function getExecutionSettings(): Promise<ExecutionSettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/execution`);
}

/**
 * Update execution settings in backend
 */
export async function updateExecutionSettings(settings: ExecutionSettings): Promise<ExecutionSettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/execution`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

/**
 * Integrations Settings interface
 */
export interface IntegrationsSettings {
  // Search APIs
  search_serper_api_key: string;
  search_bing_api_key: string;
  search_google_pse_api_key: string;
  search_google_pse_cx: string;
  search_duckduckgo_enabled: boolean;
  
  // AI Platforms
  huggingface_api_token: string;
}

/**
 * Get integrations settings from backend
 */
export async function getIntegrationsSettings(): Promise<IntegrationsSettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/integrations`);
}

/**
 * Update integrations settings
 */
export async function updateIntegrationsSettings(settings: IntegrationsSettings): Promise<IntegrationsSettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/integrations`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

/**
 * AI Provider Metadata
 */
export interface ProviderMetadata {
  name: string;
  display_name: string;
  description: string;
  default_base_url: string;
  auth_type: string;
  requires_api_key: boolean;
  supports_streaming: boolean;
  supports_function_calling: boolean;
  default_models: Array<{
    id: string;
    name: string;
    recommended?: boolean;
  }>;
  default_model: string;
  max_tokens: number;
  icon: string;
  documentation_url: string;
}

/**
 * Available Providers Response
 */
export interface AvailableProvidersResponse {
  providers: Record<string, ProviderMetadata>;
  count: number;
}

/**
 * Get available AI providers (dynamically from backend)
 */
export async function getAvailableProviders(): Promise<AvailableProvidersResponse> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/ai/providers/available`);
}

/**
 * AI Provider Config
 */
export interface AIProviderConfig {
  name: string;
  provider_type: string;
  role: 'primary' | 'fallback' | 'inactive';
  fallback_priority?: number;
  enabled: boolean;
  api_key: string;
  base_url?: string;
  default_model: string;
  available_models?: string[];
  max_tokens?: number;
  temperature?: number;
  timeout_seconds?: number;
}

/**
 * AI Settings
 */
export interface AISettings {
  enabled: boolean;
  default_provider?: string;
  fallback_provider?: string;
  default_temperature: number;
  default_max_tokens: number;
  request_timeout: number;  // AI request timeout (seconds)
  max_retries: number;
  retry_delay: number;
  providers: Record<string, AIProviderConfig>;
}

/**
 * Validate Provider Request
 */
export interface ValidateProviderRequest {
  provider_type: string;
  api_key: string;
  base_url?: string;
}

/**
 * Validate Provider Response
 */
export interface ValidateProviderResponse {
  valid: boolean;
  models?: Array<{
    id: string;
    name?: string;
    context_window?: number;
  }>;
  provider_info?: {
    name: string;
    type: string;
    [key: string]: any;
  };
  error?: string;
  error_type?: string;
}

/**
 * Validate AI provider credentials and fetch available models
 */
export async function validateAIProvider(request: ValidateProviderRequest): Promise<ValidateProviderResponse> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/ai/providers/validate`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Get current AI settings
 */
export async function getAISettings(): Promise<AISettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/ai/settings`);
}

/**
 * Update AI settings
 */
export async function updateAISettings(settings: AISettings): Promise<AISettings> {
  return await apiFetch(`${getApiBaseUrl()}/api/v1/settings/ai`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

/**
 * Add a new AI provider
 */
export async function addAIProvider(providerName: string, config: AIProviderConfig): Promise<AISettings> {
  const currentSettings = await getAISettings();
  currentSettings.providers[providerName] = config;
  return await updateAISettings(currentSettings);
}

/**
 * Update an existing AI provider
 */
export async function updateAIProvider(providerName: string, config: AIProviderConfig): Promise<AISettings> {
  const currentSettings = await getAISettings();
  currentSettings.providers[providerName] = config;
  return await updateAISettings(currentSettings);
}

/**
 * Delete an AI provider
 */
export async function deleteAIProvider(providerName: string): Promise<AISettings> {
  const currentSettings = await getAISettings();
  delete currentSettings.providers[providerName];
  return await updateAISettings(currentSettings);
}


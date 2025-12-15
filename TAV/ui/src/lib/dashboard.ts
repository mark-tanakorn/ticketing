/**
 * Dashboard API Integration - handles workflow data fetching with real-time updates
 */

import { getApiBaseUrl } from './api-config';
import { getAuthHeaders } from './auth';

// ===== INTERFACES =====

/**
 * Individual workflow item from database
 */
export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: string;
  author_id: number | null;
  created_at: string;
  last_run_at: string | null;
  progress?: number; // Progress percentage (0-100)
  is_running?: boolean; // Whether workflow is currently executing
  recommended_await_completion: string; // Recommended X-Await-Completion header value, defaults to "false"
}

/**
 * API response format from backend
 */
export interface WorkflowsResponse {
  workflows: Workflow[];
  total: number;
  page: number;
  pageSize: number;
}

/**
 * API error response
 */
export interface ApiError {
  message: string;
  code: string;
  details?: any;
}

// ===== API CONFIG =====

/**
 * Get API endpoints dynamically
 * This ensures the correct base URL is used after SSR hydration
 */
function getApiEndpoints() {
  const baseUrl = getApiBaseUrl();
  return {
    workflows: `${baseUrl}/api/v1/workflows`,
    activeExecutions: `${baseUrl}/api/v1/dashboard/active-executions`,
  };
}

// ===== API FUNCTIONS =====

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(), // Include JWT token if available
        ...options?.headers,
      },
      credentials: 'include', // Add credentials for cookies/auth
      ...options,
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
        console.error('API error details:', errorData);
      } catch (e) {
        console.error('Could not parse error response');
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    console.error('API fetch error:', error);
    throw error;
  }
}

/**
 * Fetch workflows from backend
 */
export async function fetchWorkflows(): Promise<Workflow[]> {
  // The API returns the array directly, not wrapped in an object
  const endpoints = getApiEndpoints();
  const workflows = await apiFetch<Workflow[]>(endpoints.workflows);
  return workflows;
}

/**
 * Fetch active executions with progress
 */
export async function fetchActiveExecutions(): Promise<any> {
  const endpoints = getApiEndpoints();
  return await apiFetch<any>(endpoints.activeExecutions);
}

/**
 * Merge workflows with active execution progress
 */
export async function fetchWorkflowsWithProgress(): Promise<Workflow[]> {
  const [workflows, activeData] = await Promise.all([
    fetchWorkflows(),
    fetchActiveExecutions().catch(() => ({ active_executions: [], monitoring_workflows: [] }))
  ]);
  
  // Create a map of workflow_id -> progress info
  const progressMap = new Map<string, { progress: number; is_running: boolean }>();
  
  // Add running one-shot executions
  if (activeData.active_executions) {
    activeData.active_executions.forEach((exec: any) => {
      const progress = exec.progress?.progress_percentage || 0;
      console.log(`📊 Frontend received progress for ${exec.workflow_id}: ${progress}%`, exec.progress);
      progressMap.set(exec.workflow_id, {
        progress: Math.round(progress), // Round to full number
        is_running: true
      });
    });
  }
  
  // Add monitoring workflows (show as 0% when waiting for trigger)
  if (activeData.monitoring_workflows) {
    activeData.monitoring_workflows.forEach((wf: any) => {
      if (!progressMap.has(wf.workflow_id)) {
        progressMap.set(wf.workflow_id, {
          progress: 0,
          is_running: true // Monitoring is "active" even if waiting
        });
      }
    });
  }
  
  // Merge progress into workflows
  return workflows.map(workflow => {
    const activeProgress = progressMap.get(workflow.id);
    
    // If we have active execution data, use it (takes priority over database status)
    if (activeProgress) {
      console.log(`✅ Applying active progress to workflow ${workflow.id}: ${activeProgress.progress}%`);
      return {
        ...workflow,
        progress: activeProgress.progress,
        is_running: true
      };
    }
    
    // Otherwise, use database status for completed/failed workflows
    
    // If workflow is completed, show 100% progress
    if (workflow.status.toLowerCase() === 'completed') {
      return {
        ...workflow,
        progress: 100,
        is_running: false
      };
    }
    
    // If workflow is error or failed, show 0% progress so it displays the error icon
    if (workflow.status.toLowerCase() === 'error' || workflow.status.toLowerCase() === 'failed') {
      return {
        ...workflow,
        progress: 0,
        is_running: false
      };
    }
    
    // If workflow is stopped, show 0% progress so it displays the stopped icon
    if (workflow.status.toLowerCase() === 'stopped') {
      return {
        ...workflow,
        progress: 0,
        is_running: false
      };
    }
    
    // No active execution and no special status - show no progress
    return {
      ...workflow,
      progress: undefined,
      is_running: false
    };
  });
}

// ===== REACT HOOKS =====

import { useState, useEffect, useCallback } from 'react';

/**
 * Hook state
 */
interface UseWorkflowsState {
  workflows: Workflow[];
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

/**
 * Hook options
 */
interface UseWorkflowsOptions {
  pollingInterval?: number; // default: 5000ms
  enabled?: boolean;        // default: true
}

/**
 * Hook for workflow data with auto-polling
 * Usage: const { workflows, loading, error, refresh } = useWorkflows();
 */
export function useWorkflows(options: UseWorkflowsOptions = {}): UseWorkflowsState & {
  refresh: () => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
} {
  const { pollingInterval = 5000, enabled = true } = options;
  
  const [state, setState] = useState<UseWorkflowsState>({
    workflows: [],
    loading: true,
    error: null,
    lastUpdated: null,
  });

  const [intervalId, setIntervalId] = useState<NodeJS.Timeout | null>(null);

  // Fetch data function
  const fetchData = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      const workflows = await fetchWorkflowsWithProgress(); // Use merged data
      setState(prev => ({
        ...prev,
        workflows,
        loading: false,
        error: null,
        lastUpdated: new Date(),
      }));
    } catch (error) {
      console.error('Failed to fetch workflows:', error);
      setState(prev => ({
        ...prev,
        workflows: prev.workflows || [], // Preserve existing workflows or use empty array
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch workflows',
      }));
    }
  }, []);

  // Start polling
  const startPolling = useCallback(() => {
    if (intervalId) return;
    const id = setInterval(fetchData, pollingInterval);
    setIntervalId(id);
  }, [fetchData, pollingInterval, intervalId]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (intervalId) {
      clearInterval(intervalId);
      setIntervalId(null);
    }
  }, [intervalId]);

  // Auto-fetch and setup polling
  useEffect(() => {
    fetchData();
    if (enabled) {
      startPolling();
    }
    return () => {
      stopPolling();
    };
  }, [enabled, startPolling, stopPolling, fetchData]);

  return {
    ...state,
    refresh: fetchData,
    startPolling,
    stopPolling,
  };
}
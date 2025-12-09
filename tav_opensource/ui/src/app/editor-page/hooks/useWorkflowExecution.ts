/**
 * Custom hook for managing workflow execution state and controls
 */

import { useState, useRef, useEffect } from 'react';
import {
  executeWorkflow,
  stopWorkflow,
  pauseWorkflow,
  resumeWorkflow,
  streamExecutionEvents,
  streamWorkflowEvents,
  retryExecution,
  getRetryInfo,
} from '@/lib/editor';
import { getApiBaseUrl } from '@/lib/api-config';

// Execution result status (after execution completes)
type ExecutionResult = 'none' | 'completed' | 'failed' | 'stopped';

// Retry info from backend
interface RetryInfo {
  can_retry: boolean;
  completed_nodes: string[];
  completed_count: number;
  failed_nodes: { node_id: string; error: string }[];
  failed_count: number;
  has_structure_changes: boolean;
  structure_warnings: string[];
}

type NodeStatus = 'idle' | 'pending' | 'executing' | 'completed' | 'failed';

/**
 * Trigger browser download for exported files
 * Handles both 'download' (quick download) and 'save_as' (file picker) modes
 */
function triggerDownload(downloadInfo: {
  filename: string;
  temp_filename: string;
  mode: string;
  mime_type: string;
}) {
  const { temp_filename, filename, mode } = downloadInfo;
  
  // Build download URL
  const url = `${getApiBaseUrl()}/api/v1/files/temp/download/${temp_filename}?mode=${mode}`;
  
  // Create temporary anchor element
  const a = document.createElement('a');
  a.href = url;
  
  // For 'download' mode: set download attribute to trigger direct download
  // For 'save_as' mode: don't set download attribute to trigger "Save As" dialog
  if (mode === 'download') {
    a.download = filename;
  }
  // Note: 'save_as' mode doesn't set download attribute, which triggers browser's Save As dialog
  
  // Trigger click
  document.body.appendChild(a);
  a.click();
  
  // Cleanup
  setTimeout(() => {
    document.body.removeChild(a);
  }, 100);
  
  console.log(`📥 Download triggered: ${filename} (mode=${mode})`);
}

export function useWorkflowExecution(
  workflowId: string | null,
  addLog: (message: string) => void,
  updateNodeState: (nodeId: string, status: NodeStatus, error?: string, previewData?: any, fullExecutionData?: any) => void,
  resetAllNodeStates: () => void,
  setAllNodesPending: () => void  // Add this new function
) {
  const [isExecuting, setIsExecuting] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [isMonitoring, setIsMonitoring] = useState(false); // For trigger workflows
  const [lastResult, setLastResult] = useState<ExecutionResult>('none'); // Track last execution result
  const [retryInfo, setRetryInfo] = useState<RetryInfo | null>(null); // Retry info for failed executions
  const [showRetryWarning, setShowRetryWarning] = useState(false); // Show warning modal
  const [retryWarnings, setRetryWarnings] = useState<string[]>([]); // Structure change warnings
  const sseCleanupRef = useRef<(() => void) | null>(null);
  const isMonitoringRef = useRef<boolean>(false); // Ref to avoid closure issues
  const isRecoveringStateRef = useRef<boolean>(false); // Track if we're reconnecting to existing execution
  const executionIdRef = useRef<string | null>(null); // Track current execution ID for SSE callbacks
  
  // State recovery: Check if workflow is already running when workflowId changes
  useEffect(() => {
    if (!workflowId) return;
    
    async function recoverState() {
      try {
        console.log(`[State Recovery] Checking status for workflow: ${workflowId}`);
        const response = await fetch(`${getApiBaseUrl()}/api/v1/workflows/${workflowId}/status`, {
          credentials: 'include'
        });
        
        if (!response.ok) {
          console.warn(`[State Recovery] Failed to get status: ${response.status}`);
          return;
        }
        
        const status = await response.json();
        console.log('[State Recovery] Workflow status:', status);
        
        // Check if workflow is monitoring (use is_monitoring field from TriggerManager)
        const isActiveMonitoring = status.is_monitoring === true;
        
        if (isActiveMonitoring) {
          addLog(`🔄 Reconnecting to monitoring workflow...`);
          setIsExecuting(true);
          setIsMonitoring(true);
          isMonitoringRef.current = true;
          isRecoveringStateRef.current = true; // Mark that we're recovering
          setAllNodesPending();
          
          // Reconnect to workflow stream
          if (workflowId) {
            connectToWorkflowStream(workflowId);
          }
          addLog(`✅ Reconnected to monitoring`);
        } else if (status.running_executions > 0 && status.last_execution) {
          // One-shot execution is running
          const lastExecId = status.last_execution.execution_id;
          const wasPaused = status.is_paused === true;
          
          addLog(`🔄 Reconnecting to ${wasPaused ? 'paused' : 'running'} execution...`);
          setIsExecuting(true);
          setIsPaused(wasPaused); // Restore pause state!
          setExecutionId(lastExecId);
          executionIdRef.current = lastExecId;
          isRecoveringStateRef.current = true; // Mark that we're recovering
          setAllNodesPending();
          
          // Fetch execution details to restore node states
          try {
            const execResponse = await fetch(`${getApiBaseUrl()}/api/v1/workflows/executions/${lastExecId}`, {
              credentials: 'include'
            });
            if (execResponse.ok) {
              const execData = await execResponse.json();
              console.log('[State Recovery] Execution details:', execData);
              console.log('[State Recovery] node_results:', execData.node_results);
              
              // Restore node states from node_results
              if (execData.node_results) {
                console.log(`[State Recovery] Restoring ${Object.keys(execData.node_results).length} node states`);
                Object.entries(execData.node_results).forEach(([nodeId, result]: [string, any]) => {
                  console.log(`[State Recovery] Restoring node ${nodeId}:`, result);
                  if (result.success === true) {
                    updateNodeState(nodeId, 'completed', undefined, result.outputs?.preview_data, result);
                  } else if (result.success === false) {
                    // Check if it's currently executing (running) or actually failed
                    // A node is only "running" if metadata says executing AND completed_at is null
                    if (result.metadata?.status === 'executing' && !result.completed_at) {
                      updateNodeState(nodeId, 'executing', undefined, undefined, result);
                    } else {
                      // Either explicitly failed, or was running but now stale (has completed_at)
                      updateNodeState(nodeId, 'failed', result.error, undefined, result);
                    }
                  }
                });
                addLog(`📊 Restored ${Object.keys(execData.node_results).length} node states`);
              } else {
                console.warn('[State Recovery] No node_results in response');
              }
            } else {
              console.warn('[State Recovery] Failed to fetch execution details:', execResponse.status);
            }
          } catch (error) {
            console.warn('[State Recovery] Failed to fetch execution details:', error);
            // Continue anyway - we'll get updates from SSE
          }
          
          // Reconnect to execution stream
          connectToExecutionStream(lastExecId);
          addLog(`✅ Reconnected to execution${wasPaused ? ' (paused)' : ''}`);
        } else {
          console.log('[State Recovery] Workflow is idle, no reconnection needed');
        }
      } catch (error) {
        console.error('[State Recovery] Error:', error);
      }
    }
    
    recoverState();
  }, [workflowId]); // Run when workflowId changes

  async function handleRun() {
    if (!workflowId) {
      alert('Please save workflow first');
      return;
    }

    try {
      addLog(`▶️ Running workflow...`);
      
      // Clean up any existing SSE connections first
      if (sseCleanupRef.current) {
        console.log('[handleRun] Cleaning up existing SSE connection');
        sseCleanupRef.current();
        sseCleanupRef.current = null;
      }
      
      // Reset all states for fresh execution
      setIsExecuting(true);
      setIsPaused(false);
      setIsMonitoring(false);
      isMonitoringRef.current = false;
      setLastResult('none');
      setRetryInfo(null);
      setShowRetryWarning(false);
      setRetryWarnings([]);
      resetAllNodeStates(); // Reset all nodes before execution

      const response = await executeWorkflow(workflowId);
      console.log('[handleRun] Response:', response);
      
      // Check if this is a monitoring workflow (persistent mode)
      if (response.mode === 'persistent') {
        // Monitoring workflow - connect to workflow-level SSE
        addLog(`✅ Monitoring started (${response.trigger_count} trigger(s))`);
        setIsMonitoring(true);
        isMonitoringRef.current = true;
        connectToWorkflowStream(workflowId);
      } else {
        // One-shot workflow - connect to execution-level SSE
        setExecutionId(response.execution_id);
        executionIdRef.current = response.execution_id;
        addLog(`✅ Started (${response.mode})`);
        
        // Make sure monitoring is off for one-shot
        setIsMonitoring(false);
        isMonitoringRef.current = false;
        
        if (response.execution_id) {
          connectToExecutionStream(response.execution_id);
        }
      }
    } catch (error) {
      addLog(`❌ Execute failed: ${error}`);
      setIsExecuting(false);
      setIsMonitoring(false);
      isMonitoringRef.current = false;
    }
  }

  async function handleStop() {
    if (!workflowId) return;
    try {
      await stopWorkflow(workflowId);
      addLog(`⏹️ Stopped`);
      setIsExecuting(false);
      setIsPaused(false);
      setIsMonitoring(false);
      isMonitoringRef.current = false;
      
      // Reset nodes to idle when stopped
      resetAllNodeStates();
      
      // Disconnect SSE
      if (sseCleanupRef.current) {
        sseCleanupRef.current();
        sseCleanupRef.current = null;
      }
    } catch (error) {
      addLog(`❌ Stop failed: ${error}`);
    }
  }

  async function handlePause() {
    if (!workflowId) return;
    try {
      await pauseWorkflow(workflowId);
      addLog(`⏸️ Paused`);
      setIsPaused(true);
    } catch (error) {
      addLog(`❌ Pause failed: ${error}`);
    }
  }

  async function handleResume() {
    if (!workflowId) return;
    try {
      await resumeWorkflow(workflowId);
      addLog(`▶️ Resumed`);
      setIsPaused(false);
    } catch (error) {
      addLog(`❌ Resume failed: ${error}`);
    }
  }

  async function handleRetry(force: boolean = false) {
    if (!executionId) {
      addLog(`❌ No execution to retry`);
      return;
    }

    try {
      addLog(`🔄 Retrying from checkpoint...`);
      
      // Clean up any existing SSE connections first (same as handleRun)
      if (sseCleanupRef.current) {
        console.log('[handleRetry] Cleaning up existing SSE connection');
        sseCleanupRef.current();
        sseCleanupRef.current = null;
      }
      
      const response = await retryExecution(executionId, force);
      
      if (response.requires_confirmation) {
        // Structure changed - show warning modal
        setRetryWarnings(response.warnings || []);
        setShowRetryWarning(true);
        addLog(`⚠️ Workflow changed since failure. Review warnings.`);
        return;
      }
      
      if (response.success && response.execution_id) {
        // Retry started successfully - reset states (same as handleRun)
        setIsExecuting(true);
        setIsPaused(false);
        setIsMonitoring(false);
        isMonitoringRef.current = false;
        setLastResult('none');
        setShowRetryWarning(false);
        setRetryInfo(null);
        
        // Update execution ID
        setExecutionId(response.execution_id);
        executionIdRef.current = response.execution_id;
        
        // Mark skipped nodes as completed (they were successful in original execution)
        const skippedNodes = response.skipped_nodes || [];
        skippedNodes.forEach((nodeId: string) => {
          updateNodeState(nodeId, 'completed', undefined, undefined, {
            success: true,
            skipped: true,
            message: 'Skipped - completed in previous execution'
          });
        });
        
        const skippedCount = skippedNodes.length;
        addLog(`✅ Retry started. Skipping ${skippedCount} completed node(s).`);
        
        // Connect to new execution stream
        connectToExecutionStream(response.execution_id);
      } else {
        addLog(`❌ Retry failed: ${response.message || 'Unknown error'}`);
      }
    } catch (error) {
      addLog(`❌ Retry failed: ${error}`);
      // Reset executing state on error (same as handleRun)
      setIsExecuting(false);
      setIsMonitoring(false);
      isMonitoringRef.current = false;
    }
  }

  async function handleRetryForce() {
    // Called when user confirms retry despite warnings
    setShowRetryWarning(false);
    await handleRetry(true);
  }

  function handleRetryCancel() {
    // Called when user cancels retry from warning modal
    setShowRetryWarning(false);
    setRetryWarnings([]);
    addLog(`ℹ️ Retry cancelled`);
  }

  async function handleRestart() {
    // Full restart - same as handleRun but clears the last execution state first
    // Reset all failure/retry related state
    setLastResult('none');
    setExecutionId(null);
    executionIdRef.current = null;
    setRetryInfo(null);
    setShowRetryWarning(false);
    setRetryWarnings([]);
    
    // handleRun will handle the rest (SSE cleanup, node states, etc.)
    await handleRun();
  }

  // Fetch retry info when execution fails (optional - button works without it)
  async function fetchRetryInfo(execId: string) {
    try {
      const info = await getRetryInfo(execId);
      setRetryInfo(info);
    } catch (error) {
      // Retry info is optional - button will still work without it
      // Just won't show the count of completed nodes to skip
      console.debug('Could not fetch retry info (optional):', error);
      setRetryInfo(null);
    }
  }

  function connectToExecutionStream(execId: string) {
    // Store cleanup function so we can disconnect later
    const cleanup = streamExecutionEvents(
      execId,
      (event) => handleSSEEvent(event),
      (error) => {
        addLog(`❌ Stream error: ${error.message}`);
        setIsExecuting(false);
      }
    );
    sseCleanupRef.current = cleanup;
  }

  function connectToWorkflowStream(wfId: string) {
    // Connect to workflow-level SSE for monitoring workflows
    addLog(`🔌 Connecting to workflow stream...`);
    console.log('[SSE] Connecting to workflow stream:', wfId);
    
    const cleanup = streamWorkflowEvents(
      wfId,
      (event) => handleSSEEvent(event),
      (error) => {
        addLog(`❌ Stream error: ${error.message}`);
        console.error('[SSE] Stream error:', error);
        setIsExecuting(false);
        setIsMonitoring(false);
        isMonitoringRef.current = false;
      }
    );
    sseCleanupRef.current = cleanup;
  }

  function handleSSEEvent(event: any) {
    const time = new Date().toLocaleTimeString();
    console.log('[SSE] Event received:', event.type, event);

    switch (event.type) {
      case 'connected':
        addLog(`📡 Connected to stream`);
        break;
      
      case 'workflow_monitoring_start':
        addLog(`📡 Monitoring workflow: ${event.workflow_name}`);
        // Set all nodes to pending when monitoring starts
        setAllNodesPending();
        break;
      
      case 'execution_start':
        console.log('[SSE] execution_start received, isRecoveringStateRef:', isRecoveringStateRef.current);
        const isRetry = event.retry_from || event.skipped_nodes?.length > 0;
        addLog(`[${time}] 🚀 ${isRetry ? 'Retry' : 'Execution'} started${event.execution_id ? ` (${event.execution_id.substring(0, 8)}...)` : ''}`);
        
        // For retries, mark skipped nodes as completed first
        if (isRetry && event.skipped_nodes?.length > 0) {
          console.log('[SSE] Retry detected, marking skipped nodes as completed:', event.skipped_nodes);
          event.skipped_nodes.forEach((nodeId: string) => {
            updateNodeState(nodeId, 'completed', undefined, undefined, {
              success: true,
              skipped: true,
              message: 'Skipped - completed in previous execution'
            });
          });
        }
        
        // Only set nodes to pending if this is a NEW execution (not recovering state)
        // When recovering, we've already restored node states from DB
        // For retries, we skip this since skipped nodes are already marked completed
        if (!isRecoveringStateRef.current && !isRetry) {
          console.log('[SSE] Setting all nodes to pending (fresh execution)');
          setAllNodesPending();
        } else {
          // We're reconnecting or retrying - clear the recovery flag
          console.log('[SSE] Skipping setAllNodesPending (recovery or retry)');
          isRecoveringStateRef.current = false;
        }
        break;
      
      case 'node_start':
        addLog(`[${time}] ⚙️ Node '${event.node_name || event.node_id}' starting...`);
        updateNodeState(event.node_id, 'executing');
        break;
      
      case 'node_complete':
        console.log('[SSE] node_complete event:', event);
        addLog(`[${time}] ✅ Node '${event.node_name || event.node_id}' completed`);
        
        // Check for download marker
        if (event.outputs?._download) {
          const download = event.outputs._download;
          addLog(`📥 Triggering download: ${download.filename} (${download.mode})`);
          
          // Trigger download
          triggerDownload(download);
        }
        
        // Pass full execution data including inputs and outputs
        updateNodeState(event.node_id, 'completed', undefined, event.outputs?.preview_data, {
          success: true,
          inputs: event.inputs,
          outputs: event.outputs,
          node_name: event.node_name
        });
        break;
      
      case 'node_failed':
        addLog(`[${time}] ❌ Node '${event.node_name || event.node_id}' failed: ${event.error}`);
        updateNodeState(event.node_id, 'failed', event.error, undefined, {
          success: false,
          error: event.error,
          inputs: event.inputs,
          node_name: event.node_name
        });
        break;
      
      case 'execution_complete':
        addLog(`[${time}] 🎉 Execution completed`);
        
        if (isMonitoringRef.current) {
          // For persistent workflows: wait 2 seconds then reset to pending
          addLog(`⏳ Waiting for next trigger...`);
          setTimeout(() => {
            setAllNodesPending();
          }, 2000);
        } else {
          // For one-shot workflows: reset execution state so Run button shows again
          setIsExecuting(false);
          setIsPaused(false);
          setLastResult('completed'); // Track that execution completed successfully
          setRetryInfo(null); // Clear retry info on success
          if (sseCleanupRef.current) {
            sseCleanupRef.current();
            sseCleanupRef.current = null;
          }
        }
        break;
      
      case 'execution_failed':
        addLog(`[${time}] ❌ Execution failed: ${event.error || event.message}`);
        
        if (isMonitoringRef.current) {
          // For persistent workflows: wait 2 seconds then reset to pending
          addLog(`⏳ Waiting for next trigger...`);
          setTimeout(() => {
            setAllNodesPending();
          }, 2000);
        } else {
          // For one-shot workflows: track failure for retry
          setIsExecuting(false);
          setIsPaused(false);
          setLastResult('failed'); // Track that execution failed
          
          // Fetch retry info for the failed execution
          const failedExecId = event.execution_id || executionIdRef.current;
          if (failedExecId) {
            fetchRetryInfo(failedExecId);
          }
          
          if (sseCleanupRef.current) {
            sseCleanupRef.current();
            sseCleanupRef.current = null;
          }
        }
        break;
      
      case 'execution_stopped':
        addLog(`[${time}] ⏹️ Stopped`);
        setIsExecuting(false);
        setIsMonitoring(false);
        isMonitoringRef.current = false;
        setLastResult('stopped'); // Track that execution was stopped
        
        // Fetch retry info for stopped execution (can also be retried)
        const stoppedExecId = event.execution_id || executionIdRef.current;
        if (stoppedExecId) {
          fetchRetryInfo(stoppedExecId);
        }
        
        resetAllNodeStates(); // Return to idle when stopped
        if (sseCleanupRef.current) {
          sseCleanupRef.current();
          sseCleanupRef.current = null;
        }
        break;
      
      case 'heartbeat':
        // Silent heartbeat
        console.debug(`Heartbeat received for ${event.workflow_id || event.execution_id}`);
        break;
    }
  }

  return {
    isExecuting,
    isPaused,
    executionId,
    isMonitoring,
    lastResult,
    retryInfo,
    showRetryWarning,
    retryWarnings,
    handleRun,
    handleStop,
    handlePause,
    handleResume,
    handleRetry,
    handleRetryForce,
    handleRetryCancel,
    handleRestart,
  };
}

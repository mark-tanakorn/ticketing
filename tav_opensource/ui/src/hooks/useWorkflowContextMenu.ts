'use client';

import { useState, useCallback } from 'react';
import { getApiBaseUrl } from '@/lib/api-config';

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  workflowId: string | null;
  currentRecommendation: string | null;
}

export const useWorkflowContextMenu = () => {
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    workflowId: null,
    currentRecommendation: null,
  });

  const showContextMenu = useCallback(
    (
      e: React.MouseEvent,
      workflowId: string,
      currentRecommendation: string | null
    ) => {
      e.preventDefault();
      setContextMenu({
        visible: true,
        x: e.clientX,
        y: e.clientY,
        workflowId,
        currentRecommendation,
      });
    },
    []
  );

  const hideContextMenu = useCallback(() => {
    setContextMenu((prev) => ({ ...prev, visible: false }));
  }, []);

  const updateWorkflowRecommendation = useCallback(
    async (workflowId: string, recommendation: string | null) => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/v1/workflows/${workflowId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            // Add auth header if needed
            // 'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            recommended_await_completion: recommendation,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to update workflow');
        }

        const updated = await response.json();
        
        // Return success
        return {
          success: true,
          workflow: updated,
        };
      } catch (error) {
        console.error('Failed to update workflow recommendation:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    },
    []
  );

  return {
    contextMenu,
    showContextMenu,
    hideContextMenu,
    updateWorkflowRecommendation,
  };
};


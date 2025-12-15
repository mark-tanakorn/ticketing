/**
 * Custom hook for managing grid settings from backend
 */

import { useState, useEffect } from 'react';
import { getUISettings, type UISettings } from '@/lib/editor';

interface GridSettings {
  gridSize: number;
  gridOpacity: number;
  enableGrid: boolean;
  isLoading: boolean;
}

export function useGridSettings(): GridSettings {
  const [settings, setSettings] = useState<GridSettings>({
    gridSize: 20,          // Default fallback
    gridOpacity: 0.3,      // Default fallback
    enableGrid: true,      // Default fallback
    isLoading: true,
  });

  useEffect(() => {
    async function loadSettings() {
      try {
        const uiSettings: UISettings = await getUISettings();
        setSettings({
          gridSize: uiSettings.default_grid_size,
          gridOpacity: uiSettings.grid_opacity,
          enableGrid: uiSettings.enable_grid,
          isLoading: false,
        });
      } catch (error) {
        console.error('Failed to load grid settings:', error);
        // Keep default fallback values
        setSettings(prev => ({ ...prev, isLoading: false }));
      }
    }

    // Load settings on mount
    loadSettings();

    // Poll for settings changes every 2 seconds (for cross-tab updates)
    const interval = setInterval(loadSettings, 2000);

    // Cleanup
    return () => {
      clearInterval(interval);
    };
  }, []);

  return settings;
}


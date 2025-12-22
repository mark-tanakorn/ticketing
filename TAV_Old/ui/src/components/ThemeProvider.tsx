"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getApiBaseUrl } from "@/lib/api-config";
import { getAuthToken } from "@/lib/auth";

type ThemeMode = "light" | "dark" | "default";

type ThemeContextType = {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  effectiveTheme: "light" | "dark"; // The actual theme being displayed (after system preference)
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>("default");
  const [mounted, setMounted] = useState(false);

  // Get effective theme based on system preference
  const getEffectiveTheme = (mode: ThemeMode): "light" | "dark" => {
    if (mode === "dark") return "dark";
    if (mode === "light" || mode === "default") return "light";
    return "light";
  };

  const [effectiveTheme, setEffectiveTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    setMounted(true);
    
    // First, apply localStorage theme immediately (for instant rendering)
    const savedTheme = localStorage.getItem("theme") as ThemeMode | null;
    if (savedTheme) {
      setThemeState(savedTheme);
      applyTheme(savedTheme);
    } else {
      setThemeState("default");
      applyTheme("default");
    }

    // Then fetch from backend to sync across devices
    async function loadThemeFromBackend() {
      try {
        const token = getAuthToken();
        const headers: Record<string, string> = {};
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch(`${getApiBaseUrl()}/api/v1/settings/ui`, {
          headers: headers,
          credentials: 'include',
        });
        
        if (response.ok) {
          const settings = await response.json();
          const backendTheme = settings.default_theme_mode as ThemeMode;
          
          // Only update if different from current theme
          if (backendTheme && backendTheme !== savedTheme) {
            setThemeState(backendTheme);
            applyTheme(backendTheme);
            localStorage.setItem("theme", backendTheme);
          }
        }
      } catch (error) {
        console.warn("Failed to load theme from backend, using local cache:", error);
        // Fallback to localStorage is already applied above
      }
    }

    loadThemeFromBackend();
  }, []);

  const applyTheme = (mode: ThemeMode) => {
    const root = document.documentElement;
    const effective = getEffectiveTheme(mode);
    
    // Remove all theme classes
    root.classList.remove("theme-light", "theme-dark", "theme-default", "dark");
    
    // Apply new theme
    if (mode === "dark") {
      root.classList.add("theme-dark", "dark");
    } else if (mode === "default") {
      root.classList.add("theme-default");
    } else {
      root.classList.add("theme-light");
    }
    
    setEffectiveTheme(effective);
  };

  const setTheme = (mode: ThemeMode) => {
    setThemeState(mode);
    applyTheme(mode);
    
    // Save to localStorage for instant loading next time
    if (typeof window !== "undefined") {
      localStorage.setItem("theme", mode);
    }
    
    // Note: We don't save to backend here because:
    // - Settings page already does updateUISettings() which saves all settings
    // - Saving only theme would overwrite other UI settings
    // - ThemeProvider just syncs from backend on initial load
  };

  // Always provide the context, but the theme might not be fully loaded yet
  return (
    <ThemeContext.Provider value={{ theme, setTheme, effectiveTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}


"use client";

import { useState, useEffect } from "react";
import { useTheme } from "../../components/ThemeProvider";
import AIProvidersSection from "./AIProvidersSection";
import CredentialsSection from "./CredentialsSection";
import PasswordInput from "../../components/PasswordInput";
import {
  getUISettings,
  updateUISettings,
  getSecuritySettings,
  updateSecuritySettings,
  getDeveloperSettings,
  updateDeveloperSettings,
  getExecutionSettings,
  updateExecutionSettings,
  getStorageSettings,
  updateStorageSettings,
  getIntegrationsSettings,
  updateIntegrationsSettings,
  type UISettings,
  type SecuritySettings,
  type DeveloperSettings,
  type ExecutionSettings,
  type StorageSettings,
  type IntegrationsSettings,
} from "@/lib/editor";

type Category = {
  id: string;
  label: string;
  icon: string;
  subcategories?: { id: string; label: string }[];
};

export default function SettingsDemo() {
  const { theme, setTheme } = useTheme();
  const [selectedCategory, setSelectedCategory] = useState("ai");
  const [expandedCategories, setExpandedCategories] = useState<string[]>([
    "ai",
  ]);

  // UI Settings state
  const [uiSettings, setUiSettings] = useState<UISettings>({
    default_theme_mode: "default",
    default_grid_size: 20,
    enable_grid: true,
    grid_opacity: 0.3,
    auto_save_enabled: true,
    auto_save_delay: 1000,
  });
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  // Security Settings state
  const [securitySettings, setSecuritySettings] = useState<SecuritySettings>({
    max_content_length: 104857600, // 100MB default
  });
  const [isLoadingSecurity, setIsLoadingSecurity] = useState(true);
  const [isSavingSecurity, setIsSavingSecurity] = useState(false);

  // Developer Settings state
  const [developerSettings, setDeveloperSettings] = useState<DeveloperSettings>(
    {
      enable_dev_mode: true,
      debug_mode: false,
      console_logging: true,
      error_details: true,
      api_timing: false,
      memory_monitoring: false,
    }
  );
  const [isLoadingDeveloper, setIsLoadingDeveloper] = useState(true);
  const [isSavingDeveloper, setIsSavingDeveloper] = useState(false);

  // Execution Settings state
  const [executionSettings, setExecutionSettings] = useState<ExecutionSettings>(
    {
      max_concurrent_nodes: 5,
      ai_concurrent_limit: 1,
      max_concurrent_runs_global: 8,
      max_concurrent_runs_per_workflow: 20,
      max_queue_depth_per_workflow: 200,
      default_timeout: 300,
      http_timeout: 60,
      workflow_timeout: 1800,
      error_handling: "stop_on_error",
      max_retries: 3,
      retry_delay: 5.0,
      backoff_multiplier: 1.5,
      max_retry_delay: 60,
      trigger_max_executions: 0,
      auto_restart_triggers: false,
    }
  );
  const [isLoadingExecution, setIsLoadingExecution] = useState(true);
  const [isSavingExecution, setIsSavingExecution] = useState(false);

  // Storage Settings state
  const [storageSettings, setStorageSettings] = useState<StorageSettings>({
    auto_cleanup: true,
    temp_file_cleanup: true,
    cleanup_on_startup: false,  // Safe default
    upload_dir: "uploads",
    upload_storage_days: 30,
    uploads_cleanup_interval_hours: 24,
    artifact_dir: "artifacts",
    artifact_ttl_days: 7,
    artifact_cleanup_interval_hours: 6,
    artifact_max_bytes: 1073741824,
    artifact_backend: "fs",
    temp_dir: "temp",
    temp_cleanup_interval_hours: 1,
    temp_file_max_age_hours: 1,
    result_storage_days: 30,
  });
  const [isLoadingStorage, setIsLoadingStorage] = useState(true);
  const [isSavingStorage, setIsSavingStorage] = useState(false);

  // Integrations Settings state
  const [integrationsSettings, setIntegrationsSettings] = useState<IntegrationsSettings>({
    search_serper_api_key: "",
    search_bing_api_key: "",
    search_google_pse_api_key: "",
    search_google_pse_cx: "",
    search_duckduckgo_enabled: true,
    huggingface_api_token: "",
  });
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(true);
  const [isSavingIntegrations, setIsSavingIntegrations] = useState(false);

  // Load settings from backend on mount
  useEffect(() => {
    async function loadSettings() {
      try {
        const [ui, security, developer, execution, storage, integrations] = await Promise.all([
          getUISettings(),
          getSecuritySettings(),
          getDeveloperSettings(),
          getExecutionSettings(),
          getStorageSettings(),
          getIntegrationsSettings(),
        ]);
        setUiSettings(ui);
        setSecuritySettings(security);
        setDeveloperSettings(developer);
        setExecutionSettings(execution);
        setStorageSettings(storage);
        setIntegrationsSettings(integrations);
      } catch (error) {
        console.error("Failed to load settings:", error);
      } finally {
        setIsLoadingSettings(false);
        setIsLoadingSecurity(false);
        setIsLoadingDeveloper(false);
        setIsLoadingExecution(false);
        setIsLoadingStorage(false);
        setIsLoadingIntegrations(false);
      }
    }
    loadSettings();
  }, []);

  // Save settings handlers
  const handleSaveUISettings = async () => {
    setIsSavingSettings(true);
    try {
      const updated = await updateUISettings(uiSettings);
      setUiSettings(updated);
      
      // Also update the theme in ThemeProvider for immediate effect
      setTheme(updated.default_theme_mode);
      
      alert(
        "✅ Settings saved successfully!\n\n💡 Theme and grid changes will apply immediately."
      );
    } catch (error) {
      console.error("Failed to save settings:", error);
      alert("❌ Failed to save settings. Check console for details.");
    } finally {
      setIsSavingSettings(false);
    }
  };

  const handleSaveSecuritySettings = async () => {
    setIsSavingSecurity(true);
    try {
      const updated = await updateSecuritySettings(securitySettings);
      setSecuritySettings(updated);
      alert("✅ Security settings saved successfully!");
    } catch (error) {
      console.error("Failed to save security settings:", error);
      alert("❌ Failed to save security settings. Check console for details.");
    } finally {
      setIsSavingSecurity(false);
    }
  };

  const handleSaveDeveloperSettings = async () => {
    setIsSavingDeveloper(true);
    try {
      const updated = await updateDeveloperSettings(developerSettings);
      setDeveloperSettings(updated);
      alert(
        "✅ Developer settings saved successfully!\n\n💡 Dev mode changes take effect immediately."
      );
    } catch (error) {
      console.error("Failed to save developer settings:", error);
      alert("❌ Failed to save developer settings. Check console for details.");
    } finally {
      setIsSavingDeveloper(false);
    }
  };

  const handleSaveExecutionSettings = async () => {
    setIsSavingExecution(true);
    try {
      const updated = await updateExecutionSettings(executionSettings);
      setExecutionSettings(updated);
      alert("✅ Execution settings saved successfully!");
    } catch (error) {
      console.error("Failed to save execution settings:", error);
      alert("❌ Failed to save execution settings. Check console for details.");
    } finally {
      setIsSavingExecution(false);
    }
  };

  const handleSaveStorageSettings = async () => {
    setIsSavingStorage(true);
    try {
      const updated = await updateStorageSettings(storageSettings);
      setStorageSettings(updated);
      alert("✅ Storage settings saved successfully!");
    } catch (error) {
      console.error("Failed to save storage settings:", error);
      alert("❌ Failed to save storage settings. Check console for details.");
    } finally {
      setIsSavingStorage(false);
    }
  };

  const handleSaveIntegrationsSettings = async () => {
    setIsSavingIntegrations(true);
    try {
      const updated = await updateIntegrationsSettings(integrationsSettings);
      setIntegrationsSettings(updated);
      alert("✅ Integration settings saved successfully! API keys are encrypted in the database.");
    } catch (error) {
      console.error("Failed to save integration settings:", error);
      alert("❌ Failed to save integration settings. Check console for details.");
    } finally {
      setIsSavingIntegrations(false);
    }
  };

  const categories: Category[] = [
    {
      id: "ai",
      label: "AI Providers",
      icon: "",
    },
    {
      id: "storage",
      label: "Storage",
      icon: "",
    },
    {
      id: "system",
      label: "System",
      icon: "⚙️",
      subcategories: [
        { id: "system-preferences", label: "Preferences" },
        { id: "system-security", label: "Security" },
      ],
    },
    {
      id: "execution",
      label: "Execution",
      icon: "⚡",
      subcategories: [
        { id: "execution-concurrency", label: "Concurrency" },
        { id: "execution-timeouts", label: "Timeouts" },
        { id: "execution-retry", label: "Retry & Error" },
        { id: "execution-queue", label: "Queue" },
      ],
    },
    {
      id: "integrations",
      label: "Integrations",
      icon: "🔗",
      subcategories: [
        { id: "integrations-credentials", label: "Credentials" },
        { id: "integrations-search", label: "Search APIs" },
      ],
    },
    {
      id: "developer",
      label: "Developer",
      icon: "",
      subcategories: [
        { id: "developer-debug", label: "Debug & Logging" },
        { id: "developer-monitoring", label: "Monitoring" },
      ],
    },
  ];

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories((prev) =>
      prev.includes(categoryId)
        ? prev.filter((id) => id !== categoryId)
        : [...prev, categoryId]
    );
  };

  const renderContent = () => {
    switch (selectedCategory) {
      case "execution-concurrency":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Concurrency & Performance
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Control how many operations run in parallel
              </p>
            </div>

            {isLoadingExecution ? (
              <div style={{ color: "var(--theme-text-muted)" }}>Loading...</div>
            ) : (
              <>
                <div className="space-y-6">
                  {/* Max Concurrent Nodes */}
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Max Concurrent Nodes
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="50"
                      value={executionSettings.max_concurrent_nodes}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          max_concurrent_nodes: parseInt(e.target.value),
                        })
                      }
                      className="w-full h-2"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                    <div
                      className="flex justify-between text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      <span>1</span>
                      <span
                        className="font-semibold text-base"
                        style={{ color: "var(--theme-primary)" }}
                      >
                        {executionSettings.max_concurrent_nodes}
                      </span>
                      <span>50</span>
                    </div>
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Control how many nodes run in parallel per workflow
                    </p>
                  </div>

                  {/* AI Concurrent Limit */}
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      AI Concurrent Limit
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={executionSettings.ai_concurrent_limit}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          ai_concurrent_limit: parseInt(e.target.value),
                        })
                      }
                      className="w-full h-2"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                    <div
                      className="flex justify-between text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      <span>1</span>
                      <span
                        className="font-semibold text-base"
                        style={{ color: "var(--theme-primary)" }}
                      >
                        {executionSettings.ai_concurrent_limit}
                      </span>
                      <span>10</span>
                    </div>
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Limit expensive AI calls running simultaneously
                    </p>
                  </div>

                  {/* Global Runs Limit */}
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Max Global Runs
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="200"
                      value={executionSettings.max_concurrent_runs_global}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          max_concurrent_runs_global: parseInt(e.target.value),
                        })
                      }
                      className="w-full h-2"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                    <div
                      className="flex justify-between text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      <span>1</span>
                      <span
                        className="font-semibold text-base"
                        style={{ color: "var(--theme-primary)" }}
                      >
                        {executionSettings.max_concurrent_runs_global}
                      </span>
                      <span>200</span>
                    </div>
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Max total workflow runs system-wide
                    </p>
                  </div>

                  {/* Per Workflow Limit */}
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Max Runs Per Workflow
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="50"
                      value={executionSettings.max_concurrent_runs_per_workflow}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          max_concurrent_runs_per_workflow: parseInt(
                            e.target.value
                          ),
                        })
                      }
                      className="w-full h-2"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                    <div
                      className="flex justify-between text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      <span>1</span>
                      <span
                        className="font-semibold text-base"
                        style={{ color: "var(--theme-primary)" }}
                      >
                        {executionSettings.max_concurrent_runs_per_workflow}
                      </span>
                      <span>50</span>
                    </div>
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Max concurrent runs of the same workflow
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleSaveExecutionSettings}
                  disabled={isSavingExecution}
                  className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
                  style={{
                    background: isSavingExecution
                      ? "var(--theme-text-muted)"
                      : "var(--theme-primary)",
                  }}
                  onMouseEnter={(e) =>
                    !isSavingExecution &&
                    (e.currentTarget.style.background =
                      "var(--theme-primary-hover)")
                  }
                  onMouseLeave={(e) =>
                    !isSavingExecution &&
                    (e.currentTarget.style.background = "var(--theme-primary)")
                  }
                >
                  {isSavingExecution ? "Saving..." : "Save Settings"}
                </button>
              </>
            )}
          </div>
        );

      case "execution-timeouts":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Timeouts
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Configure timeout limits for various operations
              </p>
            </div>

            {isLoadingExecution ? (
              <div style={{ color: "var(--theme-text-muted)" }}>Loading...</div>
            ) : (
              <>
                <div className="space-y-6">
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Default Timeout (seconds)
                    </label>
                    <input
                      type="number"
                      value={executionSettings.default_timeout}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          default_timeout: parseInt(e.target.value),
                        })
                      }
                      min="10"
                      max="7200"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Range: 10-7200 seconds
                    </p>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      HTTP Timeout (seconds)
                    </label>
                    <input
                      type="number"
                      value={executionSettings.http_timeout}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          http_timeout: parseInt(e.target.value),
                        })
                      }
                      min="5"
                      max="600"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Range: 5-600 seconds
                    </p>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Workflow Timeout (seconds)
                    </label>
                    <input
                      type="number"
                      value={executionSettings.workflow_timeout}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          workflow_timeout: parseInt(e.target.value),
                        })
                      }
                      min="60"
                      max="86400"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Range: 60-86400 seconds
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleSaveExecutionSettings}
                  disabled={isSavingExecution}
                  className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
                  style={{
                    background: isSavingExecution
                      ? "var(--theme-text-muted)"
                      : "var(--theme-primary)",
                  }}
                  onMouseEnter={(e) =>
                    !isSavingExecution &&
                    (e.currentTarget.style.background =
                      "var(--theme-primary-hover)")
                  }
                  onMouseLeave={(e) =>
                    !isSavingExecution &&
                    (e.currentTarget.style.background = "var(--theme-primary)")
                  }
                >
                  {isSavingExecution ? "Saving..." : "Save Settings"}
                </button>
              </>
            )}
          </div>
        );

      case "execution-retry":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Retry & Error Handling
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Configure retry behavior and error handling strategies
              </p>
            </div>

            {isLoadingExecution ? (
              <div style={{ color: "var(--theme-text-muted)" }}>Loading...</div>
            ) : (
              <>
                <div className="space-y-6">
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Error Handling Strategy
                    </label>
                    <select
                      value={executionSettings.error_handling}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          error_handling: e.target.value as
                            | "stop_on_error"
                            | "continue_on_error",
                        })
                      }
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-border)")
                      }
                    >
                      <option value="stop_on_error">Stop on Error</option>
                      <option value="continue_on_error">
                        Continue on Error
                      </option>
                    </select>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Max Retries
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="20"
                      value={executionSettings.max_retries}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          max_retries: parseInt(e.target.value),
                        })
                      }
                      className="w-full h-2"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                    <div
                      className="flex justify-between text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      <span>0</span>
                      <span
                        className="font-semibold text-base"
                        style={{ color: "var(--theme-primary)" }}
                      >
                        {executionSettings.max_retries}
                      </span>
                      <span>20</span>
                    </div>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Retry Delay (seconds)
                    </label>
                    <input
                      type="number"
                      value={executionSettings.retry_delay}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          retry_delay: parseFloat(e.target.value),
                        })
                      }
                      step="0.1"
                      min="0.1"
                      max="300"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-border)")
                      }
                    />
                  </div>
                </div>

                <button
                  onClick={handleSaveExecutionSettings}
                  disabled={isSavingExecution}
                  className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
                  style={{
                    background: isSavingExecution
                      ? "var(--theme-text-muted)"
                      : "var(--theme-primary)",
                  }}
                  onMouseEnter={(e) =>
                    !isSavingExecution &&
                    (e.currentTarget.style.background =
                      "var(--theme-primary-hover)")
                  }
                  onMouseLeave={(e) =>
                    !isSavingExecution &&
                    (e.currentTarget.style.background = "var(--theme-primary)")
                  }
                >
                  {isSavingExecution ? "Saving..." : "Save Settings"}
                </button>
              </>
            )}
          </div>
        );

      case "execution-queue":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Queue Management
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Configure queue behavior for trigger workflows
              </p>
            </div>

            {isLoadingExecution ? (
              <div style={{ color: "var(--theme-text-muted)" }}>Loading...</div>
            ) : (
              <>
                <div className="space-y-6">
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Max Queue Depth Per Workflow
                    </label>
                    <input
                      type="number"
                      value={executionSettings.max_queue_depth_per_workflow}
                      onChange={(e) =>
                        setExecutionSettings({
                          ...executionSettings,
                          max_queue_depth_per_workflow: parseInt(
                            e.target.value
                          ),
                        })
                      }
                      min="1"
                      max="10000"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Max queued executions per workflow (when concurrency limit
                      reached)
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleSaveExecutionSettings}
                  disabled={isSavingExecution}
                  className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
                  style={{
                    background: isSavingExecution
                      ? "var(--theme-text-muted)"
                      : "var(--theme-primary)",
                  }}
                  onMouseEnter={(e) =>
                    !isSavingExecution &&
                    (e.currentTarget.style.background =
                      "var(--theme-primary-hover)")
                  }
                  onMouseLeave={(e) =>
                    !isSavingExecution &&
                    (e.currentTarget.style.background = "var(--theme-primary)")
                  }
                >
                  {isSavingExecution ? "Saving..." : "Save Settings"}
                </button>
              </>
            )}
          </div>
        );

      case "system-preferences":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Preferences
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Customize application behavior and appearance
              </p>
            </div>

            {isLoadingSettings ? (
              <div
                className="text-center py-8"
                style={{ color: "var(--theme-text-muted)" }}
              >
                Loading settings...
              </div>
            ) : (
              <>
                <div className="space-y-6">
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Theme Mode
                    </label>
                    <select
                      value={theme}
                      onChange={(e) => {
                        const newTheme = e.target.value as "light" | "dark" | "default";
                        setTheme(newTheme);
                        setUiSettings({
                          ...uiSettings,
                          default_theme_mode: newTheme,
                        });
                      }}
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-border)")
                      }
                    >
                      <option value="default">
                        Default (Professional Blue)
                      </option>
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                    </select>
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Choose your preferred color scheme. Changes apply
                      immediately.
                    </p>
                  </div>

                  {/* Auto Save Settings */}
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <div className="space-y-4">
                      <label className="flex items-center justify-between cursor-pointer">
                        <div>
                          <span
                            className="text-sm font-medium block"
                            style={{ color: "var(--theme-text)" }}
                          >
                            Enable Auto Save
                          </span>
                          <span
                            className="text-xs mt-1 block"
                            style={{ color: "var(--theme-text-muted)" }}
                          >
                            Automatically save changes while you work
                          </span>
                        </div>
                        <input
                          type="checkbox"
                          checked={uiSettings.auto_save_enabled}
                          onChange={(e) =>
                            setUiSettings({
                              ...uiSettings,
                              auto_save_enabled: e.target.checked,
                            })
                          }
                          className="w-12 h-6"
                          style={{ accentColor: "var(--theme-primary)" }}
                        />
                      </label>

                      {uiSettings.auto_save_enabled && (
                        <div>
                          <label
                            className="text-sm font-medium block mb-2"
                            style={{ color: "var(--theme-text)" }}
                          >
                            Auto Save Delay (seconds)
                          </label>
                          <input
                            type="range"
                            min="0.5"
                            max="5"
                            step="0.5"
                            value={uiSettings.auto_save_delay / 1000}
                            onChange={(e) =>
                              setUiSettings({
                                ...uiSettings,
                                auto_save_delay: parseFloat(e.target.value) * 1000,
                              })
                            }
                            className="w-full h-2"
                            style={{ accentColor: "var(--theme-primary)" }}
                          />
                          <div
                            className="flex justify-between text-xs mt-2"
                            style={{ color: "var(--theme-text-muted)" }}
                          >
                            <span>0.5s</span>
                            <span
                              className="font-semibold text-base"
                              style={{ color: "var(--theme-primary)" }}
                            >
                              {(uiSettings.auto_save_delay / 1000).toFixed(1)}s
                            </span>
                            <span>5.0s</span>
                          </div>
                          <p
                            className="text-xs mt-2"
                            style={{ color: "var(--theme-text-muted)" }}
                          >
                            How long to wait after changes before saving
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Grid Size (pixels)
                    </label>
                    <input
                      type="range"
                      min="10"
                      max="50"
                      value={uiSettings.default_grid_size}
                      onChange={(e) =>
                        setUiSettings({
                          ...uiSettings,
                          default_grid_size: parseInt(e.target.value),
                        })
                      }
                      className="w-full h-2"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                    <div
                      className="flex justify-between text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      <span>10</span>
                      <span
                        className="font-semibold text-base"
                        style={{ color: "var(--theme-primary)" }}
                      >
                        {uiSettings.default_grid_size}
                      </span>
                      <span>50</span>
                    </div>
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Canvas grid size for the workflow editor
                    </p>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Grid Opacity
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={uiSettings.grid_opacity}
                      onChange={(e) =>
                        setUiSettings({
                          ...uiSettings,
                          grid_opacity: parseFloat(e.target.value),
                        })
                      }
                      className="w-full h-2"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                    <div
                      className="grid grid-cols-3 text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      <span className="text-left">0.0 (Invisible)</span>
                      <span
                        className="font-semibold text-base text-center"
                        style={{ color: "var(--theme-primary)" }}
                      >
                        {uiSettings.grid_opacity.toFixed(1)}
                      </span>
                      <span className="text-right">1.0 (Solid)</span>
                    </div>
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Adjust the visibility of the canvas grid
                    </p>
                  </div>
                </div>

                <div
                  className="rounded-lg p-6 border"
                  style={{
                    background: "var(--theme-surface)",
                    borderColor: "var(--theme-border)",
                  }}
                >
                  <label className="flex items-center justify-between">
                    <span
                      className="text-sm font-medium"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Enable Grid
                    </span>
                    <input
                      type="checkbox"
                      checked={uiSettings.enable_grid}
                      onChange={(e) =>
                        setUiSettings({
                          ...uiSettings,
                          enable_grid: e.target.checked,
                        })
                      }
                      className="w-12 h-6"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                  </label>
                  <p
                    className="text-xs mt-3"
                    style={{ color: "var(--theme-text-muted)" }}
                  >
                    Show grid lines on the workflow canvas
                  </p>
                </div>

                <button
                  onClick={handleSaveUISettings}
                  disabled={isSavingSettings}
                  className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
                  style={{
                    background: isSavingSettings
                      ? "var(--theme-text-muted)"
                      : "var(--theme-primary)",
                    cursor: isSavingSettings ? "not-allowed" : "pointer",
                  }}
                  onMouseEnter={(e) => {
                    if (!isSavingSettings)
                      e.currentTarget.style.background =
                        "var(--theme-primary-hover)";
                  }}
                  onMouseLeave={(e) => {
                    if (!isSavingSettings)
                      e.currentTarget.style.background = "var(--theme-primary)";
                  }}
                >
                  {isSavingSettings ? "Saving..." : "Save Settings"}
                </button>
              </>
            )}
          </div>
        );

      case "system-security":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Security
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Server protection and security settings
              </p>
            </div>

            {isLoadingSecurity ? (
              <div style={{ color: "var(--theme-text-muted)" }}>Loading...</div>
            ) : (
              <>
                <div className="space-y-6">
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Max Request Size (MB)
                    </label>
                    <input
                      type="number"
                      value={Math.round(
                        securitySettings.max_content_length / 1048576
                      )}
                      onChange={(e) =>
                        setSecuritySettings({
                          ...securitySettings,
                          max_content_length:
                            parseInt(e.target.value) * 1048576,
                        })
                      }
                      min="1"
                      max="2048"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor =
                          "var(--theme-border)")
                      }
                    />
                    <div
                      className="mt-3 p-3 rounded"
                      style={{
                        background: "rgba(59, 130, 246, 0.1)",
                        border: "1px solid var(--theme-info)",
                      }}
                    >
                      <p
                        className="text-xs"
                        style={{ color: "var(--theme-text)" }}
                      >
                        💡 <strong>What this does:</strong> Limits the maximum
                        size of HTTP requests (file uploads, API calls, etc.) to
                        protect your server from large uploads that could crash
                        it or consume all memory/storage.
                      </p>
                      <p
                        className="text-xs mt-2"
                        style={{ color: "var(--theme-text-secondary)" }}
                      >
                        <strong>Range:</strong> 1-2048 MB •{" "}
                        <strong>Default:</strong> 100 MB •{" "}
                        <strong>Recommendation:</strong> Keep at 100-500 MB
                        unless you need to upload large files.
                      </p>
                    </div>
                  </div>
                </div>

                <button
                  onClick={handleSaveSecuritySettings}
                  disabled={isSavingSecurity}
                  className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
                  style={{
                    background: isSavingSecurity
                      ? "var(--theme-text-muted)"
                      : "var(--theme-primary)",
                  }}
                  onMouseEnter={(e) =>
                    !isSavingSecurity &&
                    (e.currentTarget.style.background =
                      "var(--theme-primary-hover)")
                  }
                  onMouseLeave={(e) =>
                    !isSavingSecurity &&
                    (e.currentTarget.style.background = "var(--theme-primary)")
                  }
                >
                  {isSavingSecurity ? "Saving..." : "Save Settings"}
                </button>
              </>
            )}
          </div>
        );

      case "ai":
        return <AIProvidersSection />;

      case "storage":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Storage & Cleanup
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Configure file storage and automatic cleanup settings
              </p>
            </div>

            {isLoadingStorage ? (
              <div style={{ color: "var(--theme-text-muted)" }}>
                Loading storage settings...
              </div>
            ) : (
              <>
                {/* Auto Cleanup Toggle */}
                <div
                  className="rounded-lg p-6 border"
                  style={{
                    background: "var(--theme-surface)",
                    borderColor: "var(--theme-border)",
                  }}
                >
                  <label className="flex items-center justify-between cursor-pointer">
                    <div>
                      <span
                        className="text-sm font-medium block"
                        style={{ color: "var(--theme-text)" }}
                      >
                        Auto Cleanup
                      </span>
                      <span
                        className="text-xs mt-1 block"
                        style={{ color: "var(--theme-text-muted)" }}
                      >
                        Automatically delete expired files
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={storageSettings.auto_cleanup}
                      onChange={(e) =>
                        setStorageSettings({
                          ...storageSettings,
                          auto_cleanup: e.target.checked,
                        })
                      }
                      className="w-12 h-6"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                  </label>
                </div>

                {/* Temp File Cleanup Toggle */}
                <div
                  className="rounded-lg p-6 border"
                  style={{
                    background: "var(--theme-surface)",
                    borderColor: "var(--theme-border)",
                  }}
                >
                  <label className="flex items-center justify-between cursor-pointer">
                    <div>
                      <span
                        className="text-sm font-medium block"
                        style={{ color: "var(--theme-text)" }}
                      >
                        Temp File Cleanup
                      </span>
                      <span
                        className="text-xs mt-1 block"
                        style={{ color: "var(--theme-text-muted)" }}
                      >
                        Clean up temporary processing files
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={storageSettings.temp_file_cleanup}
                      onChange={(e) =>
                        setStorageSettings({
                          ...storageSettings,
                          temp_file_cleanup: e.target.checked,
                        })
                      }
                      className="w-12 h-6"
                      style={{ accentColor: "var(--theme-primary)" }}
                    />
                  </label>
                </div>

                {/* Cleanup on Startup Toggle */}
                <div
                  className="rounded-lg p-6 border"
                  style={{
                    background: "var(--theme-surface)",
                    borderColor: "var(--theme-border-error)",
                  }}
                >
                  <label className="flex items-center justify-between cursor-pointer">
                    <div>
                      <span
                        className="text-sm font-medium block"
                        style={{ color: "var(--theme-text-error)" }}
                      >
                        ⚠️ Cleanup on Startup (Dev Only)
                      </span>
                      <span
                        className="text-xs mt-1 block"
                        style={{ color: "var(--theme-text-muted)" }}
                      >
                        DELETE all uploads/artifacts/temp on server restart. Use only for development.
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={storageSettings.cleanup_on_startup}
                      onChange={(e) =>
                        setStorageSettings({
                          ...storageSettings,
                          cleanup_on_startup: e.target.checked,
                        })
                      }
                      className="w-12 h-6"
                      style={{ accentColor: "#ef4444" }}
                    />
                  </label>
                </div>

                {/* Upload Settings */}
                <div
                  className="rounded-lg p-6 border space-y-4"
                  style={{
                    background: "var(--theme-surface)",
                    borderColor: "var(--theme-border)",
                  }}
                >
                  <h3
                    className="text-lg font-semibold"
                    style={{ color: "var(--theme-text)" }}
                  >
                    Upload Files
                  </h3>
                  
                  <div>
                    <label
                      className="text-sm font-medium block mb-2"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Storage Duration (days)
                    </label>
                    <input
                      type="number"
                      value={storageSettings.upload_storage_days}
                      onChange={(e) =>
                        setStorageSettings({
                          ...storageSettings,
                          upload_storage_days: parseInt(e.target.value) || 1,
                        })
                      }
                      min="1"
                      max="365"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Days to keep uploaded files before deletion
                    </p>
                  </div>

                  <div>
                    <label
                      className="text-sm font-medium block mb-2"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Cleanup Interval (hours)
                    </label>
                    <input
                      type="number"
                      value={storageSettings.uploads_cleanup_interval_hours}
                      onChange={(e) =>
                        setStorageSettings({
                          ...storageSettings,
                          uploads_cleanup_interval_hours: parseInt(e.target.value) || 1,
                        })
                      }
                      min="1"
                      max="168"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      How often to run upload cleanup job
                    </p>
                  </div>
                </div>

                {/* Artifact Settings */}
                <div
                  className="rounded-lg p-6 border space-y-4"
                  style={{
                    background: "var(--theme-surface)",
                    borderColor: "var(--theme-border)",
                  }}
                >
                  <h3
                    className="text-lg font-semibold"
                    style={{ color: "var(--theme-text)" }}
                  >
                    Artifacts (Generated Files)
                  </h3>
                  
                  <div>
                    <label
                      className="text-sm font-medium block mb-2"
                      style={{ color: "var(--theme-text)" }}
                    >
                      TTL (days)
                    </label>
                    <input
                      type="number"
                      value={storageSettings.artifact_ttl_days}
                      onChange={(e) =>
                        setStorageSettings({
                          ...storageSettings,
                          artifact_ttl_days: parseInt(e.target.value) || 1,
                        })
                      }
                      min="1"
                      max="365"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Days to keep generated artifacts
                    </p>
                  </div>

                  <div>
                    <label
                      className="text-sm font-medium block mb-2"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Cleanup Interval (hours)
                    </label>
                    <input
                      type="number"
                      value={storageSettings.artifact_cleanup_interval_hours}
                      onChange={(e) =>
                        setStorageSettings({
                          ...storageSettings,
                          artifact_cleanup_interval_hours: parseInt(e.target.value) || 1,
                        })
                      }
                      min="1"
                      max="168"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      How often to run artifact cleanup job
                    </p>
                  </div>
                </div>

                {/* Temp File Settings */}
                <div
                  className="rounded-lg p-6 border space-y-4"
                  style={{
                    background: "var(--theme-surface)",
                    borderColor: "var(--theme-border)",
                  }}
                >
                  <h3
                    className="text-lg font-semibold"
                    style={{ color: "var(--theme-text)" }}
                  >
                    Temporary Files
                  </h3>
                  
                  <div>
                    <label
                      className="text-sm font-medium block mb-2"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Max Age (hours)
                    </label>
                    <input
                      type="number"
                      value={storageSettings.temp_file_max_age_hours}
                      onChange={(e) =>
                        setStorageSettings({
                          ...storageSettings,
                          temp_file_max_age_hours: parseInt(e.target.value) || 1,
                        })
                      }
                      min="1"
                      max="24"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      Delete temp files older than this
                    </p>
                  </div>

                  <div>
                    <label
                      className="text-sm font-medium block mb-2"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Cleanup Interval (hours)
                    </label>
                    <input
                      type="number"
                      value={storageSettings.temp_cleanup_interval_hours}
                      onChange={(e) =>
                        setStorageSettings({
                          ...storageSettings,
                          temp_cleanup_interval_hours: parseInt(e.target.value) || 1,
                        })
                      }
                      min="1"
                      max="24"
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-border)")
                      }
                    />
                    <p
                      className="text-xs mt-2"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      How often to run temp cleanup job
                    </p>
                  </div>
                </div>

                {/* Execution Results Storage */}
                <div
                  className="rounded-lg p-6 border"
                  style={{
                    background: "var(--theme-surface)",
                    borderColor: "var(--theme-border)",
                  }}
                >
                  <label
                    className="text-sm font-medium block mb-2"
                    style={{ color: "var(--theme-text)" }}
                  >
                    Execution Results Storage (days)
                  </label>
                  <input
                    type="number"
                    value={storageSettings.result_storage_days}
                    onChange={(e) =>
                      setStorageSettings({
                        ...storageSettings,
                        result_storage_days: parseInt(e.target.value) || 1,
                      })
                    }
                    min="1"
                    max="365"
                    className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                    style={{
                      background: "var(--theme-surface-variant)",
                      borderColor: "var(--theme-border)",
                      color: "var(--theme-text)",
                    }}
                    onFocus={(e) =>
                      (e.currentTarget.style.borderColor = "var(--theme-primary)")
                    }
                    onBlur={(e) =>
                      (e.currentTarget.style.borderColor = "var(--theme-border)")
                    }
                  />
                  <p
                    className="text-xs mt-3"
                    style={{ color: "var(--theme-text-muted)" }}
                  >
                    Days to keep workflow execution results
                  </p>
                </div>

                {/* Save Button */}
                <button
                  onClick={handleSaveStorageSettings}
                  disabled={isSavingStorage}
                  className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
                  style={{
                    background: isSavingStorage
                      ? "var(--theme-text-muted)"
                      : "var(--theme-primary)",
                  }}
                  onMouseEnter={(e) =>
                    !isSavingStorage &&
                    (e.currentTarget.style.background =
                      "var(--theme-primary-hover)")
                  }
                  onMouseLeave={(e) =>
                    !isSavingStorage &&
                    (e.currentTarget.style.background = "var(--theme-primary)")
                  }
                >
                  {isSavingStorage ? "Saving..." : "Save Settings"}
                </button>
              </>
            )}
          </div>
        );

      case "integrations-credentials":
        return <CredentialsSection />;

      case "integrations-search":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Search APIs
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Configure search API integrations
              </p>
            </div>

            {isLoadingIntegrations ? (
              <div style={{ color: "var(--theme-text-muted)" }}>Loading...</div>
            ) : (
              <>
                <div className="space-y-6">
                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Serper API Key
                    </label>
                    <PasswordInput
                      value={integrationsSettings.search_serper_api_key}
                      onChange={(value) =>
                        setIntegrationsSettings({
                          ...integrationsSettings,
                          search_serper_api_key: value,
                        })
                      }
                      placeholder="Enter Serper.dev API key"
                    />
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      API key is encrypted in database
                    </p>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Bing Search API Key
                    </label>
                    <PasswordInput
                      value={integrationsSettings.search_bing_api_key}
                      onChange={(value) =>
                        setIntegrationsSettings({
                          ...integrationsSettings,
                          search_bing_api_key: value,
                        })
                      }
                      placeholder="Enter Bing API key"
                    />
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      API key is encrypted in database
                    </p>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Google PSE API Key
                    </label>
                    <PasswordInput
                      value={integrationsSettings.search_google_pse_api_key}
                      onChange={(value) =>
                        setIntegrationsSettings({
                          ...integrationsSettings,
                          search_google_pse_api_key: value,
                        })
                      }
                      placeholder="Enter Google PSE API key"
                    />
                    <p
                      className="text-xs mt-3"
                      style={{ color: "var(--theme-text-muted)" }}
                    >
                      API key is encrypted in database
                    </p>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label
                      className="text-sm font-medium block mb-3"
                      style={{ color: "var(--theme-text)" }}
                    >
                      Google PSE Search Engine ID
                    </label>
                    <input
                      type="text"
                      placeholder="Enter Search Engine CX"
                      value={integrationsSettings.search_google_pse_cx}
                      onChange={(e) =>
                        setIntegrationsSettings({
                          ...integrationsSettings,
                          search_google_pse_cx: e.target.value,
                        })
                      }
                      className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                      style={{
                        background: "var(--theme-surface-variant)",
                        borderColor: "var(--theme-border)",
                        color: "var(--theme-text)",
                      }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-primary)")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "var(--theme-border)")
                      }
                    />
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label className="flex items-center justify-between">
                      <span
                        className="text-sm font-medium"
                        style={{ color: "var(--theme-text)" }}
                      >
                        Enable DuckDuckGo
                      </span>
                      <input
                        type="checkbox"
                        checked={integrationsSettings.search_duckduckgo_enabled}
                        onChange={(e) =>
                          setIntegrationsSettings({
                            ...integrationsSettings,
                            search_duckduckgo_enabled: e.target.checked,
                          })
                        }
                        className="w-12 h-6"
                        style={{ accentColor: "var(--theme-primary)" }}
                      />
                    </label>
                  </div>
                </div>

                <button
                  onClick={handleSaveIntegrationsSettings}
                  disabled={isSavingIntegrations}
                  className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
                  style={{
                    background: isSavingIntegrations
                      ? "var(--theme-text-muted)"
                      : "var(--theme-primary)",
                  }}
                  onMouseEnter={(e) =>
                    !isSavingIntegrations &&
                    (e.currentTarget.style.background =
                      "var(--theme-primary-hover)")
                  }
                  onMouseLeave={(e) =>
                    !isSavingIntegrations &&
                    (e.currentTarget.style.background = "var(--theme-primary)")
                  }
                >
                  {isSavingIntegrations ? "Saving..." : "Save Settings"}
                </button>
              </>
            )}
          </div>
        );

      case "developer-debug":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Debug & Logging
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Development mode and debugging settings
              </p>
            </div>

            {isLoadingDeveloper ? (
              <div style={{ color: "var(--theme-text-muted)" }}>Loading...</div>
            ) : (
              <>
                <div className="space-y-6">
                  <div
                    className="rounded-lg p-6 border-2"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-warning)",
                    }}
                  >
                    <label className="flex items-center justify-between">
                      <div>
                        <span
                          className="text-sm font-medium block mb-1"
                          style={{ color: "var(--theme-text)" }}
                        >
                          Development Mode
                        </span>
                        <span
                          className="text-xs"
                          style={{ color: "var(--theme-text-muted)" }}
                        >
                          Bypasses authentication (auto-login). Disable in
                          production!
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={developerSettings.enable_dev_mode}
                        onChange={(e) =>
                          setDeveloperSettings({
                            ...developerSettings,
                            enable_dev_mode: e.target.checked,
                          })
                        }
                        className="w-12 h-6"
                        style={{ accentColor: "var(--theme-warning)" }}
                      />
                    </label>
                    <div
                      className="mt-3 p-3 rounded"
                      style={{
                        background: "rgba(245, 158, 11, 0.1)",
                        border: "1px solid var(--theme-warning)",
                      }}
                    >
                      <p
                        className="text-xs"
                        style={{ color: "var(--theme-text)" }}
                      >
                        ⚠️ <strong>Warning:</strong> When enabled, anyone can
                        access your instance without logging in. Only enable on
                        local development environments. Always disable before
                        deploying to production!
                      </p>
                    </div>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label className="flex items-center justify-between">
                      <div>
                        <span
                          className="text-sm font-medium block mb-1"
                          style={{ color: "var(--theme-text)" }}
                        >
                          Debug Mode
                        </span>
                        <span
                          className="text-xs"
                          style={{ color: "var(--theme-text-muted)" }}
                        >
                          Enable verbose logging for troubleshooting
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={developerSettings.debug_mode}
                        onChange={(e) =>
                          setDeveloperSettings({
                            ...developerSettings,
                            debug_mode: e.target.checked,
                          })
                        }
                        className="w-12 h-6"
                        style={{ accentColor: "var(--theme-primary)" }}
                      />
                    </label>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label className="flex items-center justify-between">
                      <div>
                        <span
                          className="text-sm font-medium block mb-1"
                          style={{ color: "var(--theme-text)" }}
                        >
                          Console Logging
                        </span>
                        <span
                          className="text-xs"
                          style={{ color: "var(--theme-text-muted)" }}
                        >
                          Output logs to server console
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={developerSettings.console_logging}
                        onChange={(e) =>
                          setDeveloperSettings({
                            ...developerSettings,
                            console_logging: e.target.checked,
                          })
                        }
                        className="w-12 h-6"
                        style={{ accentColor: "var(--theme-primary)" }}
                      />
                    </label>
                  </div>

                  <div
                    className="rounded-lg p-6 border"
                    style={{
                      background: "var(--theme-surface)",
                      borderColor: "var(--theme-border)",
                    }}
                  >
                    <label className="flex items-center justify-between">
                      <div>
                        <span
                          className="text-sm font-medium block mb-1"
                          style={{ color: "var(--theme-text)" }}
                        >
                          Show Error Details
                        </span>
                        <span
                          className="text-xs"
                          style={{ color: "var(--theme-text-muted)" }}
                        >
                          Include full stack traces in API error responses
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={developerSettings.error_details}
                        onChange={(e) =>
                          setDeveloperSettings({
                            ...developerSettings,
                            error_details: e.target.checked,
                          })
                        }
                        className="w-12 h-6"
                        style={{ accentColor: "var(--theme-primary)" }}
                      />
                    </label>
                  </div>
                </div>

                <button
                  onClick={handleSaveDeveloperSettings}
                  disabled={isSavingDeveloper}
                  className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
                  style={{
                    background: isSavingDeveloper
                      ? "var(--theme-text-muted)"
                      : "var(--theme-primary)",
                  }}
                  onMouseEnter={(e) =>
                    !isSavingDeveloper &&
                    (e.currentTarget.style.background =
                      "var(--theme-primary-hover)")
                  }
                  onMouseLeave={(e) =>
                    !isSavingDeveloper &&
                    (e.currentTarget.style.background = "var(--theme-primary)")
                  }
                >
                  {isSavingDeveloper ? "Saving..." : "Save Settings"}
                </button>
              </>
            )}
          </div>
        );

      case "developer-monitoring":
        return (
          <div className="space-y-6">
            <div>
              <h2
                className="text-2xl font-bold mb-2"
                style={{ color: "var(--theme-text)" }}
              >
                Monitoring & Performance
              </h2>
              <p
                className="text-sm"
                style={{ color: "var(--theme-text-secondary)" }}
              >
                Configure monitoring and performance tracking
              </p>
            </div>

            <div className="space-y-6">
              <div
                className="rounded-lg p-6 border"
                style={{
                  background: "var(--theme-surface)",
                  borderColor: "var(--theme-border)",
                }}
              >
                <label className="flex items-center justify-between">
                  <span
                    className="text-sm font-medium"
                    style={{ color: "var(--theme-text)" }}
                  >
                    API Timing
                  </span>
                  <input
                    type="checkbox"
                    className="w-12 h-6"
                    style={{ accentColor: "var(--theme-primary)" }}
                  />
                </label>
              </div>

              <div
                className="rounded-lg p-6 border"
                style={{
                  background: "var(--theme-surface)",
                  borderColor: "var(--theme-border)",
                }}
              >
                <label className="flex items-center justify-between">
                  <span
                    className="text-sm font-medium"
                    style={{ color: "var(--theme-text)" }}
                  >
                    Memory Monitoring
                  </span>
                  <input
                    type="checkbox"
                    className="w-12 h-6"
                    style={{ accentColor: "var(--theme-primary)" }}
                  />
                </label>
              </div>
            </div>

            <button
              className="w-full text-white font-medium py-3 px-4 rounded-lg transition"
              style={{ background: "var(--theme-primary)" }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background =
                  "var(--theme-primary-hover)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "var(--theme-primary)")
              }
            >
              Save Settings
            </button>
          </div>
        );

      default:
        return (
          <div
            className="flex items-center justify-center h-full"
            style={{ color: "var(--theme-text-muted)" }}
          >
            <div className="text-center">
              <div className="text-4xl mb-4">⚙️</div>
              <p>Select a category from the sidebar</p>
            </div>
          </div>
        );
    }
  };

  return (
    <div
      className="min-h-screen"
      style={{
        background: "var(--theme-background)",
        color: "var(--theme-text)",
      }}
    >
      {/* Main Content - Split View */}
      <div className="flex h-screen">
        {/* Sidebar */}
        <div
          className="w-64 border-r overflow-y-auto"
          style={{
            borderColor: "var(--theme-border)",
            background: "var(--theme-surface)",
          }}
        >
          <div className="p-4">
            <h2
              className="text-lg font-semibold mb-4 px-2"
              style={{ color: "var(--theme-text)" }}
            >
              Settings
            </h2>
            <nav className="space-y-1">
              {categories.map((category) => (
                <div key={category.id}>
                  {/* Main Category */}
                  <button
                    onClick={() => {
                      if (category.subcategories) {
                        toggleCategory(category.id);
                      } else {
                        setSelectedCategory(category.id);
                      }
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition"
                    style={{
                      background:
                        selectedCategory === category.id
                          ? "var(--theme-primary)"
                          : "transparent",
                      color:
                        selectedCategory === category.id
                          ? "white"
                          : "var(--theme-text)",
                    }}
                    onMouseEnter={(e) => {
                      if (selectedCategory !== category.id) {
                        e.currentTarget.style.background =
                          "var(--theme-surface-hover)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (selectedCategory !== category.id) {
                        e.currentTarget.style.background = "transparent";
                      }
                    }}
                  >
                    <span className="text-sm flex items-center justify-center w-4">
                      {category.subcategories ? (
                        <svg 
                          className={`w-3 h-3 transition-transform duration-200 ${expandedCategories.includes(category.id) ? 'rotate-90' : ''}`}
                          viewBox="0 0 24 24" 
                          fill="none" 
                          stroke="currentColor" 
                          strokeWidth="2.5" 
                          strokeLinecap="round" 
                          strokeLinejoin="round"
                        >
                          <path d="M9 18l6-6-6-6"/>
                        </svg>
                      ) : null}
                    </span>
                    <span className="text-sm font-medium">
                      {category.label}
                    </span>
                  </button>

                  {/* Subcategories */}
                  {category.subcategories &&
                    expandedCategories.includes(category.id) && (
                      <div className="ml-4 mt-1 space-y-1">
                        {category.subcategories.map((sub) => (
                          <button
                            key={sub.id}
                            onClick={() => setSelectedCategory(sub.id)}
                            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition"
                            style={{
                              background:
                                selectedCategory === sub.id
                                  ? "var(--theme-primary)"
                                  : "transparent",
                              color:
                                selectedCategory === sub.id
                                  ? "white"
                                  : "var(--theme-text-secondary)",
                            }}
                            onMouseEnter={(e) => {
                              if (selectedCategory !== sub.id) {
                                e.currentTarget.style.background =
                                  "var(--theme-surface-hover)";
                                e.currentTarget.style.color =
                                  "var(--theme-text)";
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (selectedCategory !== sub.id) {
                                e.currentTarget.style.background =
                                  "transparent";
                                e.currentTarget.style.color =
                                  "var(--theme-text-secondary)";
                              }
                            }}
                          >
                            <span className="text-xs">•</span>
                            <span className="text-sm">{sub.label}</span>
                          </button>
                        ))}
                      </div>
                    )}
                </div>
              ))}
            </nav>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto flex justify-center">
          <div className="p-8 w-full max-w-4xl">
            {renderContent()}
            <div style={{ height: '150px' }}></div>
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useWorkflows } from "@/lib/dashboard";
import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { WorkflowContextMenu } from "@/components/WorkflowContextMenu";
import { useWorkflowContextMenu } from "@/hooks/useWorkflowContextMenu";
import { getApiBaseUrl } from "@/lib/api-config";

type SortField = "name" | "status" | "last_run_at" | "created_at" | "author_id";
type SortDirection = "asc" | "desc";

export default function Dashboard() {
  const router = useRouter();

  // Get workflow data with real-time updates
  const {
    workflows: workflowsData,
    loading,
    error,
    refresh,
    lastUpdated,
  } = useWorkflows();
  // Safety check to ensure workflows is always an array
  const workflows = workflowsData || [];

  // Sorting state
  const [sortField, setSortField] = useState<SortField>("last_run_at");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // Click feedback state
  const [isClicked, setIsClicked] = useState(false);

  // Deleting state
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Context menu hook
  const {
    contextMenu,
    showContextMenu,
    hideContextMenu,
    updateWorkflowRecommendation,
  } = useWorkflowContextMenu();

  const handleRefresh = () => {
    setIsClicked(true);
    setTimeout(() => setIsClicked(false), 250);
    refresh();
  };

  // Handle recommendation update from context menu
  const handleRecommendationUpdate = async (
    workflowId: string,
    recommendation: string | null
  ) => {
    const result = await updateWorkflowRecommendation(workflowId, recommendation);
    
    if (result.success) {
      // Refresh to get updated data
      refresh();
      console.log('✅ Execution mode updated!');
    } else {
      console.error('❌ Failed to update:', result.error);
      alert(`Failed to update execution mode: ${result.error}`);
    }
  };

  // Handle workflow row click - open in editor
  const handleWorkflowClick = (workflowId: string, event: React.MouseEvent) => {
    console.log("handleWorkflowClick called for workflow:", workflowId);
    
    // Clear any pending delete confirmations
    setConfirmDeleteId(null);
    event.preventDefault();
    event.stopPropagation();

    // Open the editor page for this workflow in a new tab
    const url = `${window.location.origin}/editor-page?workflow=${workflowId}`;
    console.log("Opening URL:", url);
    window.open(url, "_blank", "noopener,noreferrer");
  };

  // Handle delete workflow
  const handleDeleteWorkflow = async (
    workflowId: string,
    workflowName: string,
    event: React.MouseEvent
  ) => {
    // Prevent row click
    event.stopPropagation();

    // If clicking on a different workflow's delete button, clear previous confirmation
    if (confirmDeleteId && confirmDeleteId !== workflowId) {
      setConfirmDeleteId(null);
      return;
    }

    // If this is the confirm step
    if (confirmDeleteId === workflowId) {
      setDeletingId(workflowId);
      setConfirmDeleteId(null);

      try {
        const response = await fetch(
          `${getApiBaseUrl()}/api/v1/workflows/${workflowId}`,
          {
            method: "DELETE",
            headers: {
              "Content-Type": "application/json",
            },
          }
        );

        if (!response.ok) {
          const errorData = await response
            .json()
            .catch(() => ({ detail: "Unknown error" }));
          throw new Error(
            errorData.detail || `Failed to delete workflow (${response.status})`
          );
        }

        // Success - refresh the list
        console.log(`✅ Deleted workflow: ${workflowName}`);
        refresh();
      } catch (error) {
        console.error("Failed to delete workflow:", error);
        alert(
          `Failed to delete workflow: ${
            error instanceof Error ? error.message : "Unknown error"
          }`
        );
      } finally {
        setDeletingId(null);
      }
    } else {
      // First click - show confirm button
      setConfirmDeleteId(workflowId);
    }
  };

  // Handle column header click
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      // New field, default to descending
      setSortField(field);
      setSortDirection("desc");
    }
  };

  // Sort workflows based on current sort state
  const sortedWorkflows = useMemo(() => {
    const sorted = [...workflows].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case "name":
          aValue = a.name?.toLowerCase() || "";
          bValue = b.name?.toLowerCase() || "";
          break;
        case "status":
          aValue = a.status?.toLowerCase() || "";
          bValue = b.status?.toLowerCase() || "";
          break;
        case "author_id":
          aValue = a.author_id || 0;
          bValue = b.author_id || 0;
          break;
        case "last_run_at":
          aValue = a.last_run_at ? new Date(a.last_run_at).getTime() : 0;
          bValue = b.last_run_at ? new Date(b.last_run_at).getTime() : 0;
          break;
        case "created_at":
          aValue = a.created_at ? new Date(a.created_at).getTime() : 0;
          bValue = b.created_at ? new Date(b.created_at).getTime() : 0;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
      if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [workflows, sortField, sortDirection]);

  // Calculate status distribution for donut chart
  const statusData = useMemo(() => {
    const statusCounts: Record<string, number> = {};

    workflows.forEach((workflow) => {
      let status = workflow.status || "Unknown";
      // Normalize "failed" to "error" for combined display
      if (status.toLowerCase() === "failed") status = "error";
      statusCounts[status] = (statusCounts[status] || 0) + 1;
    });

    // Define fixed order for status display
    const statusOrder = [
      "completed",
      "running",
      "pending",
      "error",
      "stopped",
      "na",
      "unknown",
    ];

    return Object.entries(statusCounts)
      .map(([name, value]) => ({
        name,
        value,
      }))
      .sort((a, b) => {
        const aIndex = statusOrder.indexOf(a.name.toLowerCase());
        const bIndex = statusOrder.indexOf(b.name.toLowerCase());

        // If both statuses are in the order array, sort by order
        if (aIndex !== -1 && bIndex !== -1) {
          return aIndex - bIndex;
        }

        // If only one is in the order array, prioritize it
        if (aIndex !== -1) return -1;
        if (bIndex !== -1) return 1;

        // If neither is in the order array, sort alphabetically
        return a.name.localeCompare(b.name);
      });
  }, [workflows]);

  // Status colors for donut chart (fixed to match backend lowercase values)
  const STATUS_COLORS: Record<string, string> = {
    pending: "#eab308", // yellow
    running: "#3b82f6", // blue
    completed: "#22c55e", // green
    error: "#ef4444", // red
    failed: "#ef4444", // red (alias)
    stopped: "#6b7280", // gray
    na: "#a1a1aa", // zinc
    Unknown: "#a1a1aa", // zinc (fallback)
  };

  // Calculate metrics for summary cards
  const metrics = useMemo(() => {
    const total = workflows.length;
    const completed = workflows.filter(w => w.status?.toLowerCase() === "completed").length;
    const failed = workflows.filter(w => 
      w.status?.toLowerCase() === "failed" || w.status?.toLowerCase() === "error"
    ).length;
    const stopped = workflows.filter(w => w.status?.toLowerCase() === "stopped").length;
    const running = workflows.filter(w => w.status?.toLowerCase() === "running").length;
    
    const successRate = total > 0 ? Math.round((completed / total) * 100) : 0;
    const failedRate = total > 0 ? Math.round((failed / total) * 100) : 0;
    const stoppedRate = total > 0 ? Math.round((stopped / total) * 100) : 0;
    
    return { total, completed, failed, stopped, running, successRate, failedRate, stoppedRate };
  }, [workflows]);

  // Render sort arrow icon
  const SortArrow = ({ field }: { field: SortField }) => {
    const isActive = sortField === field;
    const color = isActive ? "#3b82f6" : "#d4d4d8";

    return (
      <span className="inline-flex items-center justify-center w-5 h-5 ml-0 align-middle">
        {!isActive ? (
          <svg className="w-5 h-5" viewBox="0 0 12 12" fill="none">
            <path d="M6 4L9 8H3L6 4Z" fill={color} />
          </svg>
        ) : sortDirection === "asc" ? (
          <svg className="w-5 h-5" viewBox="0 0 12 12" fill="none">
            <path d="M6 4L9 8H3L6 4Z" fill={color} />
          </svg>
        ) : (
          <svg className="w-5 h-5" viewBox="0 0 12 12" fill="none">
            <path d="M6 8L9 4H3L6 8Z" fill={color} />
          </svg>
        )}
      </span>
    );
  };

  return (
    <div
      className="font-sans h-full overflow-auto"
      style={{ background: "var(--theme-background)" }}
      onClick={() => setConfirmDeleteId(null)}
    >
      <main 
        className="max-w-screen-2xl mx-auto py-12 px-4"
      >
        <div className="flex justify-between items-center mb-8">
          <h1
            className="text-4xl font-bold"
            style={{ color: "var(--theme-text)" }}
          >
            Trusted ActionVerse
          </h1>
          <div className="flex items-center gap-4">
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="px-4 py-2 text-white font-bold rounded transition-colors"
              style={{
                background:
                  loading || isClicked
                    ? "var(--color-gray-400)"
                    : "var(--theme-button-primary)",
                cursor: loading || isClicked ? "not-allowed" : "pointer",
              }}
              onMouseEnter={(e) => {
                if (!loading && !isClicked) {
                  e.currentTarget.style.background =
                    "var(--theme-button-primary-hover)";
                }
              }}
              onMouseLeave={(e) => {
                if (!loading && !isClicked) {
                  e.currentTarget.style.background =
                    "var(--theme-button-primary)";
                }
              }}
            >
              Refresh
            </button>
            {lastUpdated && (
              <span
                className="text-sm min-w-[180px]"
                style={{ color: "var(--theme-text-muted)" }}
              >
                Last updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>

        {/* Metric Summary Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {/* Total Workflows */}
          <div 
            className="rounded-2xl p-5 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5"
            style={{ 
              background: "var(--theme-surface)", 
              border: "1px solid var(--theme-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)"
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium" style={{ color: "var(--theme-text-secondary)" }}>
                Total Workflows
              </span>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                   style={{ background: "#dbeafe" }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="7" height="7" rx="1"/>
                  <rect x="14" y="3" width="7" height="7" rx="1"/>
                  <rect x="3" y="14" width="7" height="7" rx="1"/>
                  <rect x="14" y="14" width="7" height="7" rx="1"/>
                </svg>
              </div>
            </div>
            <div className="text-3xl font-extrabold" style={{ color: "var(--theme-text)" }}>
              {metrics.total}
            </div>
            <div className="text-xs mt-1" style={{ color: "var(--theme-text-muted)" }}>
              All time
            </div>
          </div>

          {/* Completed */}
          <div 
            className="rounded-2xl p-5 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5"
            style={{ 
              background: "var(--theme-surface)", 
              border: "1px solid var(--theme-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)"
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium" style={{ color: "var(--theme-text-secondary)" }}>
                Completed
              </span>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                   style={{ background: "#dcfce7", color: "#16a34a" }}>
                ✓
              </div>
            </div>
            <div className="text-3xl font-extrabold" style={{ color: "var(--theme-text)" }}>
              {metrics.completed}
            </div>
            <div className="text-xs mt-1 font-medium" style={{ color: "#16a34a" }}>
              ↑ {metrics.successRate}% success rate
            </div>
          </div>

          {/* Failed */}
          <div 
            className="rounded-2xl p-5 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5"
            style={{ 
              background: "var(--theme-surface)", 
              border: "1px solid var(--theme-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)"
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium" style={{ color: "var(--theme-text-secondary)" }}>
                Failed
              </span>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                   style={{ background: "#fee2e2", color: "#dc2626" }}>
                ✕
              </div>
            </div>
            <div className="text-3xl font-extrabold" style={{ color: "var(--theme-text)" }}>
              {metrics.failed}
            </div>
            <div className="text-xs mt-1 font-medium" style={{ color: "#dc2626" }}>
              ↓ {metrics.failedRate}% of total
            </div>
          </div>

          {/* Running */}
          <div 
            className="rounded-2xl p-5 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5"
            style={{ 
              background: "var(--theme-surface)", 
              border: "1px solid var(--theme-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)"
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium" style={{ color: "var(--theme-text-secondary)" }}>
                Running
              </span>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                   style={{ background: "#dbeafe", color: "#2563eb" }}>
                <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M12 2v4m0 12v4m10-10h-4M6 12H2m15.07-5.07l-2.83 2.83M8.76 15.24l-2.83 2.83m11.31 0l-2.83-2.83M8.76 8.76L5.93 5.93" strokeLinecap="round"/>
                </svg>
              </div>
            </div>
            <div className="text-3xl font-extrabold" style={{ color: "var(--theme-text)" }}>
              {metrics.running}
            </div>
            <div className="text-xs mt-1" style={{ color: metrics.running > 0 ? "#2563eb" : "var(--theme-text-muted)" }}>
              {metrics.running > 0 ? "● Active now" : "No active runs"}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          <section
            className="lg:col-span-4 rounded-3xl shadow p-6"
            style={{
              background: "var(--theme-surface)",
              border: "1px solid var(--theme-border)",
            }}
          >
            <h2
              className="text-2xl font-semibold mb-4"
              style={{ color: "var(--theme-text)" }}
            >
              Workflows
            </h2>
            <p
              className="mb-4"
              style={{ color: "var(--theme-text-secondary)" }}
            >
              Manage and monitor your automation workflows.
            </p>
            {/* Error State */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
                <p className="text-red-600 dark:text-red-400">
                  Error loading workflows: {error}
                </p>
                <button
                  onClick={refresh}
                  className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
                >
                  Try again
                </button>
              </div>
            )}

            {/* Loading State */}
            {loading && workflows.length === 0 && (
              <div className="flex justify-center py-8">
                <div style={{ color: "var(--theme-text-muted)" }}>
                  Loading workflows...
                </div>
              </div>
            )}

            {/* Workflows Table */}
            {!loading || sortedWorkflows.length > 0 ? (
              <div className="h-115 overflow-y-auto">
                <table className="w-full text-left">
                  <thead
                    className="sticky top-0 z-10"
                    style={{ background: "var(--theme-surface)" }}
                  >
                    <tr
                      style={{ borderBottom: "2px solid var(--theme-border)" }}
                    >
                      <th
                        className="py-3 px-4 cursor-pointer select-none transition-colors text-xs font-semibold uppercase tracking-wider"
                        style={{
                          color: "var(--theme-text-muted)",
                        }}
                        onClick={() => handleSort("name")}
                        onMouseEnter={(e) => e.currentTarget.style.color = "var(--theme-primary)"}
                        onMouseLeave={(e) => e.currentTarget.style.color = "var(--theme-text-muted)"}
                      >
                        <div className="flex items-center">
                          Name
                          <SortArrow field="name" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-4 text-xs font-semibold uppercase tracking-wider"
                        style={{ color: "var(--theme-text-muted)" }}
                      >
                        Description
                      </th>
                      <th
                        className="py-3 px-4 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer select-none transition-colors"
                        style={{ color: "var(--theme-text-muted)" }}
                        onClick={() => handleSort("status")}
                        onMouseEnter={(e) => e.currentTarget.style.color = "var(--theme-primary)"}
                        onMouseLeave={(e) => e.currentTarget.style.color = "var(--theme-text-muted)"}
                      >
                        <div className="flex items-center justify-center">
                          Status
                          <SortArrow field="status" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-4 cursor-pointer select-none transition-colors text-xs font-semibold uppercase tracking-wider"
                        style={{
                          color: "var(--theme-text-muted)",
                        }}
                        onClick={() => handleSort("author_id")}
                        onMouseEnter={(e) => e.currentTarget.style.color = "var(--theme-primary)"}
                        onMouseLeave={(e) => e.currentTarget.style.color = "var(--theme-text-muted)"}
                      >
                        <div className="flex items-center">
                          Owner
                          <SortArrow field="author_id" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-4 cursor-pointer select-none transition-colors text-xs font-semibold uppercase tracking-wider"
                        style={{
                          color: "var(--theme-text-muted)",
                        }}
                        onClick={() => handleSort("last_run_at")}
                        onMouseEnter={(e) => e.currentTarget.style.color = "var(--theme-primary)"}
                        onMouseLeave={(e) => e.currentTarget.style.color = "var(--theme-text-muted)"}
                      >
                        <div className="flex items-center">
                          Last Run
                          <SortArrow field="last_run_at" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-4 text-xs font-semibold uppercase tracking-wider"
                        style={{ color: "var(--theme-text-muted)" }}
                      >
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedWorkflows.length === 0 && !loading ? (
                      <tr>
                        <td
                          colSpan={6}
                          className="py-8 text-center"
                          style={{ color: "var(--theme-text-muted)" }}
                        >
                          No workflows found
                        </td>
                      </tr>
                    ) : (
                      sortedWorkflows.map((workflow) => {
                        // Helper function to get status color
                        const getStatusColor = (status: string) => {
                          switch (status.toLowerCase()) {
                            case "pending":
                              return "#eab308";
                            case "running":
                              return "#3b82f6";
                            case "completed":
                              return "#22c55e";
                            case "error":
                            case "failed":
                              return "#ef4444";
                            case "failed":
                              return "#ef4444";
                            case "stopped":
                              return "#6b7280";
                            case "na":
                              return "#a1a1aa";
                            default:
                              return "#a1a1aa"; // gray for unknown
                          }
                        };

                        // Helper function to format date
                        const formatDate = (dateStr: string | null) => {
                          if (!dateStr) return "Never";
                          try {
                            return new Date(dateStr).toLocaleDateString();
                          } catch {
                            return "Invalid date";
                          }
                        };

                        return (
                          <tr
                            key={workflow.id}
                            onClick={(e) => handleWorkflowClick(workflow.id, e)}
                            onContextMenu={(e) => showContextMenu(e, workflow.id, workflow.recommended_await_completion)}
                            className="transition-all duration-150 cursor-pointer group"
                            style={{
                              borderBottom: "1px solid var(--theme-border)",
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background =
                                "var(--theme-surface-hover)";
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = "transparent";
                            }}
                          >
                            <td
                              className="py-4 px-4 font-semibold"
                              style={{ color: "var(--theme-text)" }}
                            >
                              {workflow.name}
                            </td>
                            <td
                              className="py-4 px-4 text-sm max-w-xs truncate"
                              style={{ color: "var(--theme-text-secondary)" }}
                            >
                              {workflow.description}
                            </td>
                            <td className="py-4 px-4 text-center">
                              {/* Status Icon Only */}
                              <div className="flex items-center justify-center">
                                {workflow.progress !== undefined ? (
                                  <>
                                    {/* Error/Failed - Red Circle with X */}
                                    {workflow.status?.toLowerCase() === "error" ||
                                    workflow.status?.toLowerCase() === "failed" ? (
                                      <div className="relative w-9 h-9">
                                        <svg className="w-9 h-9 transform -rotate-90" viewBox="0 0 36 36">
                                          <circle cx="18" cy="18" r="16" fill="none" stroke="#ef4444" strokeWidth="3" />
                                        </svg>
                                        <div className="absolute inset-0 flex items-center justify-center">
                                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                                            <path d="M4 4L12 12M12 4L4 12" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
                                          </svg>
                                        </div>
                                      </div>
                                    ) : workflow.status?.toLowerCase() === "stopped" ? (
                                      /* Stopped - Gray Circle with Dash */
                                      <div className="relative w-9 h-9">
                                        <svg className="w-9 h-9 transform -rotate-90" viewBox="0 0 36 36">
                                          <circle cx="18" cy="18" r="16" fill="none" stroke="#6b7280" strokeWidth="3" />
                                        </svg>
                                        <div className="absolute inset-0 flex items-center justify-center">
                                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                                            <path d="M4 8L12 8" stroke="#6b7280" strokeWidth="3" strokeLinecap="round" />
                                          </svg>
                                        </div>
                                      </div>
                                    ) : workflow.progress === 100 ? (
                                      /* Completed - Green Circle with Checkmark */
                                      <div className="relative w-9 h-9">
                                        <svg className="w-9 h-9 transform -rotate-90" viewBox="0 0 36 36">
                                          <circle cx="18" cy="18" r="16" fill="none" stroke="#22c55e" strokeWidth="3" />
                                        </svg>
                                        <div className="absolute inset-0 flex items-center justify-center">
                                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                                            <path d="M3 8L6.5 11.5L13 5" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                                          </svg>
                                        </div>
                                      </div>
                                    ) : (
                                      /* In Progress - Circle with percentage */
                                      <div className="relative w-9 h-9">
                                        <svg className="w-9 h-9 transform -rotate-90" viewBox="0 0 36 36">
                                          <circle cx="18" cy="18" r="16" fill="none" stroke="var(--theme-border)" strokeWidth="3" />
                                          <circle
                                            cx="18" cy="18" r="16" fill="none"
                                            stroke="var(--theme-primary)"
                                            strokeWidth="3" strokeLinecap="round"
                                            strokeDasharray={`${workflow.progress} ${100 - workflow.progress}`}
                                            style={{ transition: "stroke-dasharray 0.3s ease" }}
                                          />
                                        </svg>
                                        <div className="absolute inset-0 flex items-center justify-center">
                                          <span className="text-[9px] font-semibold" style={{ color: "var(--theme-text)" }}>
                                            {workflow.progress}%
                                          </span>
                                        </div>
                                      </div>
                                    )}
                                  </>
                                ) : (
                                  <span className="text-xs" style={{ color: "var(--theme-text-muted)" }}>-</span>
                                )}
                              </div>
                            </td>
                            <td
                              className="py-4 px-4 text-sm"
                              style={{ color: "var(--theme-text-secondary)" }}
                            >
                              {workflow.author_id}
                            </td>
                            <td
                              className="py-4 px-4 text-sm"
                              style={{ color: "var(--theme-text-secondary)" }}
                            >
                              {formatDate(workflow.last_run_at)}
                            </td>
                            <td className="py-4 px-4">
                              <button
                                onClick={(e) =>
                                  handleDeleteWorkflow(
                                    workflow.id,
                                    workflow.name,
                                    e
                                  )
                                }
                                disabled={deletingId === workflow.id}
                                className="text-sm"
                                style={{
                                  color:
                                    confirmDeleteId === workflow.id
                                      ? "#3b82f6"
                                      : deletingId === workflow.id
                                      ? "var(--theme-text-muted)"
                                      : "var(--theme-danger)",
                                  backgroundColor: "transparent",
                                  cursor:
                                    deletingId === workflow.id
                                      ? "not-allowed"
                                      : "pointer",
                                  padding: "0",
                                  borderRadius: "0",
                                  border: "none",
                                  fontWeight: "normal",
                                }}
                                onMouseEnter={(e) => {
                                  if (deletingId !== workflow.id) {
                                    e.currentTarget.style.textDecoration =
                                      "underline";
                                  }
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.textDecoration = "none";
                                }}
                              >
                                {deletingId === workflow.id
                                  ? "Deleting..."
                                  : confirmDeleteId === workflow.id
                                  ? "Confirm?"
                                  : "Delete"}
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>

          {/* Status Distribution Chart */}
          <section
            className="lg:sticky lg:top-6 rounded-2xl p-6"
            style={{
              background: "var(--theme-surface)",
              border: "1px solid var(--theme-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)"
            }}
          >
            <h2
              className="text-xl font-bold mb-1"
              style={{ color: "var(--theme-text)" }}
            >
              Status Distribution
            </h2>
            <p
              className="text-sm mb-6"
              style={{ color: "var(--theme-text-muted)" }}
            >
              Overview of workflow statuses
            </p>

            {statusData.length > 0 ? (
              <div className="flex flex-col items-center h-full">
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={statusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={0}
                      dataKey="value"
                      animationBegin={0}
                      animationDuration={800}
                      animationEasing="ease-out"
                      isAnimationActive={true}
                      stroke="none"
                    >
                      {statusData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={STATUS_COLORS[entry.name] || "#a1a1aa"}
                          style={{ 
                            filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.1))",
                            cursor: "pointer",
                            transition: "all 0.2s ease"
                          }}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--theme-surface)",
                        border: "1px solid var(--theme-border)",
                        borderRadius: "12px",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                        padding: "8px 12px",
                      }}
                      itemStyle={{
                        color: "var(--theme-text)",
                        fontWeight: 500,
                      }}
                    />
                    <text
                      x="50%"
                      y="50%"
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="var(--theme-text)"
                    >
                      <tspan
                        x="50%"
                        dy="-0.3em"
                        fontSize="28"
                        fontWeight="bold"
                      >
                        {workflows.length}
                      </tspan>
                      <tspan
                        x="50%"
                        dy="1.4em"
                        fontSize="12"
                        fill="var(--theme-text-muted)"
                      >
                        Workflows
                      </tspan>
                    </text>
                  </PieChart>
                </ResponsiveContainer>

                {/* Custom Legend Below */}
                <div className="mt-6 w-full space-y-2">
                  {statusData.map((entry, index) => {
                    const percentage = (
                      (entry.value / workflows.length) *
                      100
                    ).toFixed(0);
                    // Capitalize status for display, combine error/failed
                    const displayName =
                      entry.name === "error"
                        ? "Error/Failed"
                        : entry.name.charAt(0).toUpperCase() + entry.name.slice(1);
                    return (
                      <div
                        key={index}
                        className="flex items-center justify-between py-2 px-3 rounded-lg transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{
                              backgroundColor:
                                STATUS_COLORS[entry.name] || "#a1a1aa",
                            }}
                          />
                          <span
                            className="text-sm font-medium"
                            style={{ color: "var(--theme-text)" }}
                          >
                            {displayName}
                          </span>
                        </div>
                        <span
                          className="text-sm font-semibold"
                          style={{ color: "var(--theme-text-secondary)" }}
                        >
                          {entry.value} <span style={{ color: "var(--theme-text-muted)" }}>({percentage}%)</span>
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div
                className="flex items-center justify-center h-64"
                style={{ color: "var(--theme-text-muted)" }}
              >
                No data available
              </div>
            )}
          </section>
        </div>
      </main>

      {/* Context Menu */}
      {contextMenu.visible && contextMenu.workflowId && (
        <WorkflowContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          workflowId={contextMenu.workflowId}
          currentRecommendation={contextMenu.currentRecommendation}
          onClose={hideContextMenu}
          onUpdate={handleRecommendationUpdate}
        />
      )}
    </div>
  );
}

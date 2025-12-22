/**
 * Utility functions for node categorization and icons
 */

export function groupNodesByCategory(nodes: any[]) {
  const grouped = new Map();
  nodes.forEach(node => {
    if (!grouped.has(node.category)) {
      grouped.set(node.category, []);
    }
    grouped.get(node.category).push({
      type: node.node_type || node.type,
      name: node.display_name || node.name,
      description: node.description,
      category: node.category,
      icon: node.icon,
      input_ports: node.input_ports || [],   // ✅ Preserve ports
      output_ports: node.output_ports || [], // ✅ Preserve ports
    });
  });

  return Array.from(grouped.entries()).map(([name, nodes]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    icon: getCategoryIcon(name),
    nodes,
  }));
}

export function getCategoryIcon(category: string) {
  const icons: Record<string, string> = {
    triggers: "fa-solid fa-bolt",
    actions: "fa-solid fa-play",
    ai: "fa-solid fa-brain",
    communication: "fa-solid fa-paper-plane",
    processing: "fa-solid fa-gears",
    workflow: "fa-solid fa-sitemap",
    input: "fa-solid fa-keyboard",
    output: "fa-solid fa-display",
    business: "fa-solid fa-briefcase",
    analytics: "fa-solid fa-chart-line",
  };
  return icons[category.toLowerCase()] || "fa-solid fa-cube";
}

export function getNodeIcon(category: string) {
  const icons: Record<string, { icon: string; color: string; bgColor: string }> = {
    triggers: {
      icon: "fa-solid fa-bolt",
      color: "#d97706",
      bgColor: "rgba(251, 191, 36, 0.15)" // Amber
    },
    actions: {
      icon: "fa-solid fa-play",
      color: "#16a34a",
      bgColor: "rgba(34, 197, 94, 0.15)" // Green
    },
    ai: {
      icon: "fa-solid fa-brain",
      color: "#9333ea",
      bgColor: "rgba(168, 85, 247, 0.15)" // Purple
    },
    communication: {
      icon: "fa-solid fa-paper-plane",
      color: "#2563eb",
      bgColor: "rgba(59, 130, 246, 0.15)" // Blue
    },
    processing: {
      icon: "fa-solid fa-gears",
      color: "#ea580c",
      bgColor: "rgba(249, 115, 22, 0.15)" // Orange
    },
    workflow: {
      icon: "fa-solid fa-sitemap",
      color: "#4f46e5",
      bgColor: "rgba(99, 102, 241, 0.15)" // Indigo
    },
    input: {
      icon: "fa-solid fa-keyboard",
      color: "#0891b2",
      bgColor: "rgba(6, 182, 212, 0.15)" // Cyan
    },
    output: {
      icon: "fa-solid fa-display",
      color: "#db2777",
      bgColor: "rgba(236, 72, 153, 0.15)" // Pink
    },
    control: {
      icon: "fa-solid fa-code-branch",
      color: "#7c3aed",
      bgColor: "rgba(139, 92, 246, 0.15)" // Violet
    },
    business: {
      icon: "fa-solid fa-briefcase",
      color: "#059669",
      bgColor: "rgba(16, 185, 129, 0.15)" // Emerald
    },
    analytics: {
      icon: "fa-solid fa-chart-line",
      color: "#e11d48",
      bgColor: "rgba(244, 63, 94, 0.15)" // Rose
    },
  };
  return icons[category.toLowerCase()] || {
    icon: "fa-solid fa-cube",
    color: "#4b5563",
    bgColor: "rgba(107, 114, 128, 0.15)" // Gray
  };
}

export function getDummyCategories() {
  return [
    {
      name: "Triggers",
      icon: "fa-solid fa-bolt",
      nodes: [
        { name: "Manual Trigger", description: "Start workflow manually" },
        { name: "Schedule", description: "Run on schedule" },
      ],
    },
    {
      name: "Actions",
      icon: "fa-solid fa-play",
      nodes: [
        { name: "HTTP Request", description: "Make HTTP request" },
        { name: "Send Email", description: "Send email" },
      ],
    },
  ];
}


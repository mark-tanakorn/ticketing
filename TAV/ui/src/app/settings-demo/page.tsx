"use client";

import { useState } from "react";

type Category = {
  id: string;
  label: string;
  icon: string;
  subcategories?: { id: string; label: string }[];
};

export default function SettingsDemo() {
  const [selectedCategory, setSelectedCategory] = useState("execution-concurrency");
  const [expandedCategories, setExpandedCategories] = useState<string[]>(["execution", "ai"]);

  const categories: Category[] = [
    {
      id: "system",
      label: "System",
      icon: "⚙️",
      subcategories: [
        { id: "system-ui", label: "UI & Theme" },
        { id: "system-storage", label: "Storage" },
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
        { id: "execution-retry", label: "Retry" },
        { id: "execution-queue", label: "Queue" },
        { id: "execution-resources", label: "Resources" },
      ],
    },
    {
      id: "ai",
      label: "AI Providers",
      icon: "🤖",
      subcategories: [
        { id: "ai-global", label: "Global Settings" },
        { id: "ai-openai", label: "OpenAI" },
        { id: "ai-anthropic", label: "Anthropic" },
        { id: "ai-local", label: "Local Server" },
      ],
    },
    {
      id: "integrations",
      label: "Integrations",
      icon: "🔗",
      subcategories: [
        { id: "integrations-search", label: "Search APIs" },
        { id: "integrations-huggingface", label: "HuggingFace" },
      ],
    },
    {
      id: "storage",
      label: "Storage",
      icon: "💾",
    },
    {
      id: "network",
      label: "Network",
      icon: "🌐",
    },
    {
      id: "developer",
      label: "Developer",
      icon: "🛠️",
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
              <h2 className="text-2xl font-bold mb-2">Concurrency & Performance</h2>
              <p className="text-gray-400 text-sm">
                Control how many operations run in parallel
              </p>
            </div>

            <div className="space-y-6">
              {/* Max Concurrent Nodes */}
              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Max Concurrent Nodes
                </label>
                <input
                  type="range"
                  min="1"
                  max="50"
                  defaultValue="5"
                  className="w-full accent-blue-600 h-2"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>1</span>
                  <span className="text-blue-400 font-semibold text-base">5</span>
                  <span>50</span>
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  Control how many nodes run in parallel per workflow
                </p>
              </div>

              {/* AI Concurrent Limit */}
              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  AI Concurrent Limit
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  defaultValue="1"
                  className="w-full accent-blue-600 h-2"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>1</span>
                  <span className="text-blue-400 font-semibold text-base">1</span>
                  <span>10</span>
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  Limit expensive AI calls running simultaneously
                </p>
              </div>

              {/* Global Runs Limit */}
              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Max Global Runs
                </label>
                <input
                  type="range"
                  min="1"
                  max="200"
                  defaultValue="8"
                  className="w-full accent-blue-600 h-2"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>1</span>
                  <span className="text-blue-400 font-semibold text-base">8</span>
                  <span>200</span>
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  Max total workflow runs system-wide
                </p>
              </div>

              {/* Per Workflow Limit */}
              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Max Runs Per Workflow
                </label>
                <input
                  type="range"
                  min="1"
                  max="50"
                  defaultValue="20"
                  className="w-full accent-blue-600 h-2"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>1</span>
                  <span className="text-blue-400 font-semibold text-base">20</span>
                  <span>50</span>
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  Max concurrent runs of the same workflow
                </p>
              </div>
            </div>

            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition">
              Save Settings
            </button>
          </div>
        );

      case "execution-timeouts":
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-2">Timeouts</h2>
              <p className="text-gray-400 text-sm">
                Configure timeout limits for various operations
              </p>
            </div>

            <div className="space-y-6">
              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Default Timeout (seconds)
                </label>
                <input
                  type="number"
                  defaultValue="300"
                  min="10"
                  max="7200"
                  className="w-full bg-[#0a0a0a] border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-3">Range: 10-7200 seconds</p>
              </div>

              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  HTTP Timeout (seconds)
                </label>
                <input
                  type="number"
                  defaultValue="60"
                  min="5"
                  max="600"
                  className="w-full bg-[#0a0a0a] border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-3">Range: 5-600 seconds</p>
              </div>

              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Workflow Timeout (seconds)
                </label>
                <input
                  type="number"
                  defaultValue="1800"
                  min="60"
                  max="86400"
                  className="w-full bg-[#0a0a0a] border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-3">Range: 60-86400 seconds</p>
              </div>
            </div>

            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition">
              Save Settings
            </button>
          </div>
        );

      case "execution-retry":
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-2">Retry & Error Handling</h2>
              <p className="text-gray-400 text-sm">
                Configure retry behavior and error handling strategies
              </p>
            </div>

            <div className="space-y-6">
              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Error Handling Strategy
                </label>
                <select className="w-full bg-[#0a0a0a] border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500">
                  <option value="stop_on_error">Stop on Error</option>
                  <option value="continue_on_error">Continue on Error</option>
                </select>
              </div>

              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Max Retries
                </label>
                <input
                  type="range"
                  min="0"
                  max="20"
                  defaultValue="3"
                  className="w-full accent-blue-600 h-2"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>0</span>
                  <span className="text-blue-400 font-semibold text-base">3</span>
                  <span>20</span>
                </div>
              </div>

              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Retry Delay (seconds)
                </label>
                <input
                  type="number"
                  defaultValue="5.0"
                  step="0.1"
                  min="0.1"
                  max="300"
                  className="w-full bg-[#0a0a0a] border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition">
              Save Settings
            </button>
          </div>
        );

      case "ai-openai":
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-2">OpenAI Configuration</h2>
              <p className="text-gray-400 text-sm">
                Configure OpenAI provider settings
              </p>
            </div>

            <div className="space-y-6">
              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="flex items-center justify-between mb-4">
                  <span className="text-sm font-medium text-gray-300">Enabled</span>
                  <input
                    type="checkbox"
                    defaultChecked
                    className="w-12 h-6 accent-blue-600"
                  />
                </label>
              </div>

              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  API Key
                </label>
                <input
                  type="password"
                  placeholder="sk-..."
                  className="w-full bg-[#0a0a0a] border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-3">
                  API key is encrypted in database
                </p>
              </div>

              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Default Model
                </label>
                <select className="w-full bg-[#0a0a0a] border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500">
                  <option>gpt-4</option>
                  <option>gpt-4-turbo</option>
                  <option>gpt-3.5-turbo</option>
                </select>
              </div>

              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Base URL
                </label>
                <input
                  type="text"
                  defaultValue="https://api.openai.com/v1"
                  className="w-full bg-[#0a0a0a] border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition">
              Save Settings
            </button>
          </div>
        );

      case "system-ui":
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-2">UI & Theme</h2>
              <p className="text-gray-400 text-sm">
                Customize the appearance of the application
              </p>
            </div>

            <div className="space-y-6">
              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Theme Mode
                </label>
                <select className="w-full bg-[#0a0a0a] border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500">
                  <option value="default">Default</option>
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </div>

              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="text-sm font-medium text-gray-300 block mb-3">
                  Grid Size
                </label>
                <input
                  type="range"
                  min="10"
                  max="50"
                  defaultValue="20"
                  className="w-full accent-blue-600 h-2"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>10</span>
                  <span className="text-blue-400 font-semibold text-base">20</span>
                  <span>50</span>
                </div>
                <p className="text-xs text-gray-500 mt-3">Canvas grid size in pixels</p>
              </div>

              <div className="bg-[#1a1a1a] rounded-lg p-6 border border-gray-800">
                <label className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-300">
                    Enable Animations
                  </span>
                  <input
                    type="checkbox"
                    defaultChecked
                    className="w-12 h-6 accent-blue-600"
                  />
                </label>
              </div>
            </div>

            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition">
              Save Settings
            </button>
          </div>
        );

      default:
        return (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <div className="text-4xl mb-4">⚙️</div>
              <p>Select a category from the sidebar</p>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      {/* Top Nav */}
      <nav className="border-b border-gray-800 bg-[#111] px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-2xl font-bold text-green-400">⬡</div>
            <span className="text-lg font-semibold">TrustedHub</span>
          </div>
          <div className="flex gap-4">
            <button className="px-4 py-2 text-gray-400 hover:text-white transition">
              Dashboard
            </button>
            <button className="px-4 py-2 text-gray-400 hover:text-white transition">
              Editor
            </button>
            <button className="px-4 py-2 bg-gray-800 rounded-lg text-white">
              Settings
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content - Split View */}
      <div className="flex h-[calc(100vh-73px)]">
        {/* Sidebar */}
        <div className="w-64 border-r border-gray-800 bg-[#111] overflow-y-auto">
          <div className="p-4">
            <h2 className="text-lg font-semibold mb-4 px-2">Settings</h2>
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
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition ${
                      selectedCategory === category.id
                        ? "bg-blue-600 text-white"
                        : "text-gray-300 hover:bg-gray-800"
                    }`}
                  >
                    <span className="text-sm">
                      {category.subcategories
                        ? expandedCategories.includes(category.id)
                          ? "▼"
                          : "▶"
                        : category.icon}
                    </span>
                    <span className="text-sm font-medium">{category.label}</span>
                  </button>

                  {/* Subcategories */}
                  {category.subcategories &&
                    expandedCategories.includes(category.id) && (
                      <div className="ml-4 mt-1 space-y-1">
                        {category.subcategories.map((sub) => (
                          <button
                            key={sub.id}
                            onClick={() => setSelectedCategory(sub.id)}
                            className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition ${
                              selectedCategory === sub.id
                                ? "bg-blue-600 text-white"
                                : "text-gray-400 hover:bg-gray-800 hover:text-gray-300"
                            }`}
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
        <div className="flex-1 overflow-y-auto">
          <div className="p-8 max-w-3xl">{renderContent()}</div>
        </div>
      </div>
    </div>
  );
}


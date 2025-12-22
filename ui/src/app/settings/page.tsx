"use client";

import { useEffect, useState } from "react";

interface Setting {
  value: any;
  description: string;
  category: string;
  data_type: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, Setting>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/settings/");
      const data = await response.json();
      setSettings(data.settings || {});
    } catch (error) {
      console.error("Error fetching settings:", error);
      setMessage("Error loading settings");
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = async (key: string, value: any) => {
    setSaving(key);
    setMessage("");

    try {
      const response = await fetch(`http://localhost:8000/api/settings/${key}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          value: value,
          description: settings[key]?.description || "",
          category: settings[key]?.category || "general"
        }),
      });

      if (response.ok) {
        setMessage(`✅ ${key} updated successfully`);
        // Refresh settings
        await fetchSettings();
      } else {
        const error = await response.json();
        setMessage(`❌ Error: ${error.detail || "Failed to update"}`);
      }
    } catch (error) {
      console.error("Error updating setting:", error);
      setMessage("❌ Error updating setting");
    } finally {
      setSaving(null);
    }
  };

  const handleInputChange = (key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        value: value
      }
    }));
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <div className="w-64 bg-gray-800 text-white p-4">
          <h2 className="text-xl font-bold mb-4">Navigation</h2>
          <ul>
            <li className="mb-2">
              <a href="/" className="hover:text-gray-300">
                Dashboard
              </a>
            </li>
            <li className="mb-2">
              <a href="/users" className="hover:text-gray-300">
                Approvers
              </a>
            </li>
            <li className="mb-2">
              <a href="/fixers" className="hover:text-gray-300">
                Engineers
              </a>
            </li>
            <li className="mb-2">
              <a href="/settings" className="text-blue-300 font-semibold">
                Settings
              </a>
            </li>
          </ul>
        </div>
        <div className="flex-1 p-8">
          <div className="text-lg">Loading settings...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 text-white p-4">
        <h2 className="text-xl font-bold mb-4">Navigation</h2>
        <ul>
          <li className="mb-2">
            <a href="/" className="hover:text-gray-300">
              Dashboard
            </a>
          </li>
          <li className="mb-2">
            <a href="/users" className="hover:text-gray-300">
              Approvers
            </a>
          </li>
          <li className="mb-2">
            <a href="/fixers" className="hover:text-gray-300">
              Engineers
            </a>
          </li>
          <li className="mb-2">
            <a href="/settings" className="text-blue-300 font-semibold">
              Settings
            </a>
          </li>
        </ul>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">System Settings</h1>

          {message && (
            <div className={`mb-6 p-4 rounded-md ${message.includes('✅') ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
              {message}
            </div>
          )}

          {/* SLA Settings Section */}
          <div className="bg-white shadow-md rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">SLA Configuration</h2>
            <p className="text-gray-600 mb-6">
              Configure Service Level Agreement timeframes for different ticket severities.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* SLA Hours */}
              <div>
                <h3 className="text-lg font-medium mb-4">SLA Timeframes (Hours)</h3>
                <div className="space-y-3">
                  {["SLA_LOW_HOURS", "SLA_MEDIUM_HOURS", "SLA_HIGH_HOURS", "SLA_CRITICAL_HOURS"].map(key => (
                    <div key={key} className="flex justify-between items-center p-3 bg-gray-50 rounded-md">
                      <span className="font-medium">
                        {key.replace("SLA_", "").replace("_HOURS", "").toLowerCase().replace(/\b\w/g, l => l.toUpperCase())} Priority:
                      </span>
                      <div className="flex items-center space-x-2">
                        <input
                          type="number"
                          step="0.1"
                          value={settings[key]?.value || ""}
                          onChange={(e) => handleInputChange(key, parseFloat(e.target.value) || 0)}
                          className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                          disabled={saving === key}
                        />
                        <span className="text-gray-700">hours</span>
                        <button
                          onClick={() => updateSetting(key, settings[key]?.value)}
                          disabled={saving === key}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                          {saving === key ? "..." : "Save"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pre-breach Warning */}
              <div>
                <h3 className="text-lg font-medium mb-4">Pre-Breach Warning</h3>
                <div className="p-3 bg-orange-50 rounded-md">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-orange-700">Warning Time:</span>
                    <div className="flex items-center space-x-2">
                      <input
                        type="number"
                        value={settings["PRE_BREACH_SECONDS"]?.value || ""}
                        onChange={(e) => handleInputChange("PRE_BREACH_SECONDS", parseInt(e.target.value) || 0)}
                        className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                        disabled={saving === "PRE_BREACH_SECONDS"}
                      />
                      <span className="text-gray-700">seconds</span>
                      <button
                        onClick={() => updateSetting("PRE_BREACH_SECONDS", settings["PRE_BREACH_SECONDS"]?.value)}
                        disabled={saving === "PRE_BREACH_SECONDS"}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                      >
                        {saving === "PRE_BREACH_SECONDS" ? "..." : "Save"}
                      </button>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    System will send warnings this many seconds before SLA breach.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Communication Settings */}
          <div className="bg-white shadow-md rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Communication Settings</h2>
            <p className="text-gray-600 mb-6">
              Choose how the system communicates with users (email or WhatsApp workflows).
            </p>

            <div className="flex items-center space-x-4">
              <span className="font-medium">Communication Mode:</span>
              <select
                value={settings["COMMUNICATION_MODE"]?.value || "EMAIL"}
                onChange={(e) => handleInputChange("COMMUNICATION_MODE", e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={saving === "COMMUNICATION_MODE"}
              >
                <option value="EMAIL">Email</option>
                <option value="WHATSAPP">WhatsApp</option>
              </select>
              <button
                onClick={() => updateSetting("COMMUNICATION_MODE", settings["COMMUNICATION_MODE"]?.value)}
                disabled={saving === "COMMUNICATION_MODE"}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {saving === "COMMUNICATION_MODE" ? "Saving..." : "Save"}
              </button>
            </div>

            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <p className="text-sm text-blue-800">
                <strong>Current Mode:</strong> {settings["COMMUNICATION_MODE"]?.value || "EMAIL"}
                <br />
                When set to EMAIL, the system uses email workflows. When set to WHATSAPP, it uses WhatsApp workflows.
              </p>
            </div>
          </div>

          {/* System Information */}
          <div className="bg-white shadow-md rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">System Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 bg-gray-50 rounded-md">
                <h3 className="font-medium text-gray-800">Backend API</h3>
                <p className="text-sm text-gray-600">http://localhost:8000</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-md">
                <h3 className="font-medium text-gray-800">TAV Engine</h3>
                <p className="text-sm text-gray-600">http://localhost:5001</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
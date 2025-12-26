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
  const [originalSettings, setOriginalSettings] = useState<
    Record<string, Setting>
  >({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [modifiedSettings, setModifiedSettings] = useState<Set<string>>(
    new Set()
  );

  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  // Fetch current user
  useEffect(() => {
    fetch("http://localhost:8000/auth/me", { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setUser(data))
      .catch(() => setUser(null));
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/settings/");
      const data = await response.json();
      const settingsData = data.settings || {};
      setSettings(settingsData);
      setOriginalSettings(JSON.parse(JSON.stringify(settingsData))); // Deep copy
      setModifiedSettings(new Set()); // Reset modified settings when loading fresh data
    } catch (error) {
      console.error("Error fetching settings:", error);
      setMessage("Error loading settings");
    } finally {
      setLoading(false);
    }
  };

  const saveAllChanges = async () => {
    if (modifiedSettings.size === 0) {
      setMessage("ℹ️ No changes to save");
      return;
    }

    setSaving(true);
    setMessage("");

    const results = [];
    for (const key of modifiedSettings) {
      try {
        const response = await fetch(
          `http://localhost:8000/api/settings/${key}`,
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              value: settings[key]?.value,
              description: settings[key]?.description || "",
              category: settings[key]?.category || "general",
            }),
          }
        );

        if (response.ok) {
          results.push(`${key}: ✅`);
        } else {
          const error = await response.json();
          results.push(`${key}: ❌ ${error.detail || "Failed"}`);
        }
      } catch (error) {
        results.push(`${key}: ❌ Error`);
      }
    }

    // Refresh settings
    await fetchSettings();
    setModifiedSettings(new Set());

    const successCount = results.filter((r) => r.includes("✅")).length;
    const totalCount = results.length;

    if (successCount === totalCount) {
      setMessage(`✅ All ${totalCount} settings updated successfully`);
    } else {
      setMessage(
        `⚠️ ${successCount}/${totalCount} settings updated. Check details.`
      );
    }

    setSaving(false);
  };

  const handleInputChange = (key: string, value: any) => {
    setSettings((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        value: value,
      },
    }));

    // Check if the new value is different from the original (normalize to strings for comparison)
    const originalValue = String(originalSettings[key]?.value || "");
    const newValue = String(value || "");
    const isModified = originalValue !== newValue;
    setModifiedSettings((prev) => {
      const newSet = new Set(prev);
      if (isModified) {
        newSet.add(key);
      } else {
        newSet.delete(key);
      }
      return newSet;
    });
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
              <a href="/approvers" className="hover:text-gray-300">
                Approvers
              </a>
            </li>
            <li className="mb-2">
              <a href="/engineers" className="hover:text-gray-300">
                Engineers
              </a>
            </li>
            <li className="mb-2">
              <a href="/users" className="hover:text-gray-300">
                Users
              </a>
            </li>
            <li className="mb-2">
              <a href="/assets" className="hover:text-gray-300">
                Asset Management
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

  // Handle logout
  const handleLogout = async () => {
    try {
      await fetch("http://localhost:8000/auth/logout", {
        method: "POST",
        credentials: "include",
      });
      // Redirect to login
      window.location.href = "/login";
    } catch (error) {
      console.error("Logout error:", error);
      // Still redirect even if logout fails
      window.location.href = "/login";
    }
  };

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
          {user && user.role === "admin" && (
            <>
              <li className="mb-2">
                <a href="/approvers" className="hover:text-gray-300">
                  Approvers
                </a>
              </li>
              <li className="mb-2">
                <a href="/engineers" className="hover:text-gray-300">
                  Engineers
                </a>
              </li>
              <li className="mb-2">
                <a href="/users" className="hover:text-gray-300">
                  Users
                </a>
              </li>
              <li className="mb-2">
                <a href="/assets" className="hover:text-gray-300">
                  Asset Management
                </a>
              </li>
              <li className="mb-2">
                <a href="/settings" className="text-blue-300 font-semibold">
                  Settings
                </a>
              </li>
            </>
          )}
          <li className="mt-8 pt-4 border-t border-gray-600">
            <button
              onClick={handleLogout}
              className="w-full text-left hover:text-gray-300 text-red-300"
            >
              Logout
            </button>
          </li>
        </ul>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">System Settings</h1>

          {message && (
            <div
              className={`mb-6 p-4 rounded-md ${
                message.includes("✅")
                  ? "bg-green-50 text-green-800 border border-green-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {message}
            </div>
          )}

          {/* SLA & Communication Settings Section */}
          <div className="bg-white shadow-md rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">
              SLA & Communication Settings
            </h2>
            <p className="text-gray-600 mb-6">
              Configure Service Level Agreement timeframes and communication
              preferences.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* SLA Hours */}
              <div>
                <h3 className="text-lg font-medium mb-4">
                  SLA Timeframes (Hours)
                </h3>
                <div className="space-y-3">
                  {[
                    {
                      key: "SLA_LOW_HOURS",
                      bg: "bg-green-50",
                      text: "text-green-700",
                    },
                    {
                      key: "SLA_MEDIUM_HOURS",
                      bg: "bg-yellow-50",
                      text: "text-yellow-700",
                    },
                    {
                      key: "SLA_HIGH_HOURS",
                      bg: "bg-orange-50",
                      text: "text-orange-700",
                    },
                    {
                      key: "SLA_CRITICAL_HOURS",
                      bg: "bg-red-50",
                      text: "text-red-700",
                    },
                  ].map(({ key, bg, text }) => (
                    <div
                      key={key}
                      className={`flex justify-between items-center p-4 ${bg} rounded-md`}
                    >
                      <span className={`font-medium ${text}`}>
                        {key
                          .replace("SLA_", "")
                          .replace("_HOURS", "")
                          .toLowerCase()
                          .replace(/\b\w/g, (l) => l.toUpperCase())}{" "}
                        Priority:
                      </span>
                      <div className="flex items-center space-x-2">
                        <input
                          type="number"
                          step="0.1"
                          value={settings[key]?.value || ""}
                          onChange={(e) =>
                            handleInputChange(
                              key,
                              parseFloat(e.target.value) || 0
                            )
                          }
                          className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                        />
                        <span className="text-gray-700">hours</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pre-breach Warning & Communication */}
              <div>
                <h3 className="text-lg font-medium mb-4">Pre-Breach Warning</h3>
                <div className="p-3 bg-orange-50 rounded-md mb-6">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-orange-700">
                      Warning Time:
                    </span>
                    <div className="flex items-center space-x-2">
                      <input
                        type="number"
                        value={settings["PRE_BREACH_SECONDS"]?.value || ""}
                        onChange={(e) =>
                          handleInputChange(
                            "PRE_BREACH_SECONDS",
                            parseInt(e.target.value) || 0
                          )
                        }
                        className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                      />
                      <span className="text-gray-700">seconds</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    System will send warnings this many seconds before SLA
                    breach.
                  </p>
                </div>

                <h3 className="text-lg font-medium mb-4 mt-9">
                  Communication Mode
                </h3>
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-blue-700">Mode:</span>
                    <div className="flex items-center space-x-2">
                      <select
                        value={settings["COMMUNICATION_MODE"]?.value || "EMAIL"}
                        onChange={(e) =>
                          handleInputChange(
                            "COMMUNICATION_MODE",
                            e.target.value
                          )
                        }
                        className="px-3 py-1 border border-gray-300 rounded text-sm"
                      >
                        <option value="EMAIL">Email</option>
                        <option value="WHATSAPP">WhatsApp</option>
                      </select>
                    </div>
                  </div>
                  <p className="text-sm text-blue-800">
                    EMAIL uses email workflows
                    <br></br>
                    WHATSAPP uses WhatsApp workflows.
                  </p>
                </div>
              </div>
            </div>

            {/* Save All Button */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="flex justify-between items-center">
                <div className="text-sm text-gray-600">
                  <span>
                    {modifiedSettings.size} setting
                    {modifiedSettings.size !== 1 ? "s" : ""} modified
                  </span>
                </div>
                <button
                  onClick={saveAllChanges}
                  disabled={saving || modifiedSettings.size === 0}
                  className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? "Saving..." : "Save All Changes"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

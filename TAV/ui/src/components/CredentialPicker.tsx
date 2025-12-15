"use client";

import { useState, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api-config";
import { getAuthToken } from "@/lib/auth";

interface Credential {
  id: number;
  name: string;
  service_type: string;
  auth_type: string;
  is_active: boolean;
}

interface CredentialPickerProps {
  value: string | number | null | undefined;
  onChange: (value: string | null) => void;
  credentialTypes?: string[]; // Filter by credential types
  label?: string;
  required?: boolean;
}

export default function CredentialPicker({
  value,
  onChange,
  credentialTypes,
  label = "Credential",
  required = false,
}: CredentialPickerProps) {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCredentials();
  }, [credentialTypes]);

  const fetchCredentials = async () => {
    try {
      const token = getAuthToken();
      const headers: HeadersInit = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(`${getApiBaseUrl()}/api/v1/credentials`, {
        headers: headers,
        credentials: 'include', // Include cookies for authentication
      });

      if (!response.ok) {
        throw new Error("Failed to fetch credentials");
      }

      const data = await response.json();
      let creds = data.credentials || [];

      // Filter by credential types if specified
      if (credentialTypes && credentialTypes.length > 0) {
        creds = creds.filter((c: Credential) => 
          credentialTypes.includes(c.auth_type)
        );
      }

      // Only show active credentials
      creds = creds.filter((c: Credential) => c.is_active);

      setCredentials(creds);
      setError(null);
    } catch (err) {
      console.error("Error fetching credentials:", err);
      setError("Failed to load credentials");
      setCredentials([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newValue = e.target.value === "" ? null : e.target.value;
    onChange(newValue);
  };

  const handleCreateNew = () => {
    // Open settings page in new tab
    window.open("/settings-page?tab=integrations-credentials", "_blank");
  };

  if (isLoading) {
    return (
      <div className="text-sm text-gray-500">
        Loading credentials...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-500">
        {error}
        <button
          onClick={fetchCredentials}
          className="ml-2 text-blue-500 hover:text-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      <div className="flex gap-2">
        <select
          value={value || ""}
          onChange={handleChange}
          className="flex-1 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">
            {credentials.length === 0
              ? "No credentials available"
              : "Select a credential"}
          </option>
          {credentials.map((credential) => (
            <option key={credential.id} value={credential.id}>
              {credential.name} ({credential.service_type})
            </option>
          ))}
        </select>

        <button
          onClick={handleCreateNew}
          className="px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors whitespace-nowrap text-sm"
          title="Create new credential"
        >
          + New
        </button>

        {credentials.length > 0 && (
          <button
            onClick={fetchCredentials}
            className="px-3 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            title="Refresh credentials list"
          >
            <i className="fas fa-sync-alt text-sm"></i>
          </button>
        )}
      </div>

      {credentials.length === 0 && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          No credentials found. Click "+ New" to create one.
        </p>
      )}

      {credentialTypes && credentialTypes.length > 0 && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Showing: {credentialTypes.join(", ")}
        </p>
      )}
    </div>
  );
}


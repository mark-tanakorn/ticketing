"use client";

import { useState, useEffect } from "react";
import PasswordInput from "../../components/PasswordInput";
import { getApiBaseUrl } from "@/lib/api-config";

// Types
type AuthType = "api_key" | "bearer_token" | "basic_auth" | "oauth2" | "smtp" | "database" | "twilio" | "custom";

interface Credential {
  id: number;
  name: string;
  service_type: string;
  auth_type: AuthType;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
}

interface CredentialTypeDefinition {
  name: string;
  auth_type: AuthType;
  description?: string;
  fields: FieldDefinition[];
}

interface FieldDefinition {
  name: string;
  type: string;
  required: boolean;
  label?: string;
  description?: string;
}

// API functions
async function getCredentials(): Promise<{credentials: Credential[], total: number}> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/credentials`, {
    credentials: 'include', // Include cookies for authentication
  });
  if (!response.ok) {
    throw new Error("Failed to fetch credentials");
  }
  return response.json();
}

async function getCredentialTypes(): Promise<Record<string, CredentialTypeDefinition>> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/credentials/types/list`, {
    credentials: 'include', // Include cookies for authentication
  });
  if (!response.ok) {
    throw new Error("Failed to fetch credential types");
  }
  const data = await response.json();
  return data.types;
}

async function createCredential(data: {
  name: string;
  service_type: string;
  auth_type: AuthType;
  credential_data: Record<string, any>;
  metadata?: Record<string, any>;
  description?: string;
}): Promise<Credential> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/credentials`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: 'include', // Include cookies for authentication
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to create credential" }));
    const errorMessage = typeof error.detail === 'string' 
      ? error.detail 
      : JSON.stringify(error.detail || error);
    throw new Error(errorMessage);
  }
  return response.json();
}

async function deleteCredential(id: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/credentials/${id}`, {
    method: "DELETE",
    credentials: 'include', // Include cookies for authentication
  });
  if (!response.ok) {
    throw new Error("Failed to delete credential");
  }
}

export default function CredentialsSection() {
  // State management
  const [isEditing, setIsEditing] = useState(false);
  const [editingCredentialId, setEditingCredentialId] = useState<number | null>(null);
  
  // Data states
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [credentialTypes, setCredentialTypes] = useState<Record<string, CredentialTypeDefinition>>({});
  
  // Form state
  const [formData, setFormData] = useState({
    name: "",
    service_type: "",
    auth_type: "api_key" as AuthType,
    description: "",
    credential_data: {} as Record<string, any>,
  });
  
  // Track which credential type template is selected (e.g., "twilio", "api_key", etc.)
  const [selectedCredentialType, setSelectedCredentialType] = useState<string>("api_key");

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load initial data
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const [credsData, types] = await Promise.all([
        getCredentials(),
        getCredentialTypes(),
      ]);
      
      setCredentials(credsData.credentials);
      setCredentialTypes(types);
    } catch (err) {
      console.error("Failed to load credentials:", err);
      setError("Failed to load credentials");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle save
  const handleSave = async () => {
    if (!formData.name || !formData.service_type) {
      alert("Please fill in all required fields");
      return;
    }

    // Validate required fields for selected credential type
    const selectedType = credentialTypes[selectedCredentialType];
    if (selectedType) {
      const requiredFields = selectedType.fields.filter(f => f.required);
      for (const field of requiredFields) {
        if (!formData.credential_data[field.name]) {
          alert(`Please fill in required field: ${field.label || field.name}`);
          return;
        }
      }
    }

    setIsSaving(true);
    try {
      await createCredential(formData);
      await loadData();
      resetForm();
      alert("✅ Credential saved successfully!");
    } catch (error) {
      console.error("Failed to save credential:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to save credential";
      alert(`❌ Failed to save credential:\n\n${errorMessage}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Handle delete
  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await deleteCredential(id);
      await loadData();
      alert("✅ Credential deleted successfully!");
    } catch (error) {
      console.error("Failed to delete credential:", error);
      alert("❌ Failed to delete credential");
    }
  };

  // Reset form
  const resetForm = () => {
    setIsEditing(false);
    setEditingCredentialId(null);
    setSelectedCredentialType("api_key");
    setFormData({
      name: "",
      service_type: "",
      auth_type: "api_key",
      description: "",
      credential_data: {},
    });
  };

  const selectedTypeDefinition = credentialTypes[selectedCredentialType];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="text-lg" style={{ color: 'var(--theme-text)' }}>Loading credentials...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="text-lg text-red-500">{error}</div>
          <button 
            onClick={loadData}
            className="mt-4 px-4 py-2 rounded-lg"
            style={{ background: 'var(--theme-primary)', color: 'white' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2" style={{ color: 'var(--theme-text)' }}>
          Credentials
        </h2>
        <p className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
          Securely store API keys, tokens, and authentication credentials. Use them across workflows without exposing secrets.
        </p>
      </div>

      {/* TOP STICKY CARD - Add/Edit Credential */}
      <div 
        className="rounded-lg p-6 border sticky top-4 z-10" 
        style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}
      >
        {!isEditing ? (
          // Initial state: Just the Add button
          <button 
            className="w-full text-white font-medium py-3 px-6 rounded-lg transition flex items-center justify-center gap-2"
            style={{ background: 'var(--theme-primary)' }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-primary-hover)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-primary)'}
            onClick={() => setIsEditing(true)}
          >
            <span className="text-xl">+</span>
            <span>Add New Credential</span>
          </button>
        ) : (
          // Editing state: Show the form
          <div>
            <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--theme-text)' }}>
              {editingCredentialId ? 'Edit Credential' : 'Add New Credential'}
            </h3>
            
            <div className="space-y-4">
              {/* Credential Name */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                  Credential Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., My GitHub Token"
                  className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                  style={{ 
                    background: 'var(--theme-surface-variant)', 
                    borderColor: 'var(--theme-border)', 
                    color: 'var(--theme-text)' 
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                  onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                />
              </div>

              {/* Service Type */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                  Service Type
                </label>
                <input
                  type="text"
                  value={formData.service_type}
                  onChange={(e) => setFormData({ ...formData, service_type: e.target.value })}
                  placeholder="github, slack, discord, custom, etc."
                  className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                  style={{ 
                    background: 'var(--theme-surface-variant)', 
                    borderColor: 'var(--theme-border)', 
                    color: 'var(--theme-text)' 
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                  onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                />
                <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                  Identifier for the service (for filtering in node config)
                </p>
              </div>

              {/* Auth Type Dropdown */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                  Authentication Type
                </label>
                <select
                  value={selectedCredentialType}
                  onChange={(e) => {
                    const typeKey = e.target.value;
                    const typeDef = credentialTypes[typeKey];
                    setSelectedCredentialType(typeKey);
                    setFormData({ 
                      ...formData,
                      service_type: typeKey, // Auto-fill service_type with the credential type key
                      auth_type: typeDef?.auth_type || "api_key",
                      credential_data: {} // Reset fields when type changes
                    });
                  }}
                  className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                  style={{ 
                    background: 'var(--theme-surface-variant)', 
                    borderColor: 'var(--theme-border)', 
                    color: 'var(--theme-text)' 
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                  onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                >
                  {Object.entries(credentialTypes).map(([key, type]) => (
                    <option key={key} value={key}>
                      {type.name}
                    </option>
                  ))}
                </select>
                {selectedTypeDefinition?.description && (
                  <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                    {selectedTypeDefinition.description}
                  </p>
                )}
              </div>

              {/* Dynamic Fields based on auth type */}
              {selectedTypeDefinition && (
                <div className="space-y-3 pt-2 border-t" style={{ borderColor: 'var(--theme-border)' }}>
                  <h4 className="font-medium text-sm" style={{ color: 'var(--theme-text)' }}>
                    {selectedTypeDefinition.name} Fields
                  </h4>
                  {selectedTypeDefinition.fields.map((field) => (
                    <div key={field.name}>
                      <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                        {field.label || field.name}
                        {field.required && <span style={{ color: 'var(--theme-danger)' }}> *</span>}
                      </label>
                      {field.name.includes("password") || field.name.includes("token") || field.name.includes("key") || field.name.includes("secret") ? (
                        <PasswordInput
                          value={formData.credential_data[field.name] || ""}
                          onChange={(value) =>
                            setFormData({
                              ...formData,
                              credential_data: {
                                ...formData.credential_data,
                                [field.name]: value,
                              },
                            })
                          }
                          placeholder={field.description}
                        />
                      ) : field.type === "boolean" ? (
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formData.credential_data[field.name] || false}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                credential_data: {
                                  ...formData.credential_data,
                                  [field.name]: e.target.checked,
                                },
                              })
                            }
                            className="w-4 h-4 border rounded"
                            style={{ accentColor: 'var(--theme-primary)' }}
                          />
                          <span className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
                            {field.description || field.label}
                          </span>
                        </label>
                      ) : field.type === "integer" ? (
                        <input
                          type="number"
                          value={formData.credential_data[field.name] || ""}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              credential_data: {
                                ...formData.credential_data,
                                [field.name]: parseInt(e.target.value) || 0,
                              },
                            })
                          }
                          placeholder={field.description}
                          className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                          style={{ 
                            background: 'var(--theme-surface-variant)', 
                            borderColor: 'var(--theme-border)', 
                            color: 'var(--theme-text)' 
                          }}
                          onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                          onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                        />
                      ) : (
                        <input
                          type="text"
                          value={formData.credential_data[field.name] || ""}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              credential_data: {
                                ...formData.credential_data,
                                [field.name]: e.target.value,
                              },
                            })
                          }
                          placeholder={field.description}
                          className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                          style={{ 
                            background: 'var(--theme-surface-variant)', 
                            borderColor: 'var(--theme-border)', 
                            color: 'var(--theme-text)' 
                          }}
                          onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                          onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                        />
                      )}
                      {field.description && !field.name.includes("password") && !field.name.includes("token") && !field.name.includes("key") && (
                        <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                          {field.description}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Description */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                  Description (Optional)
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Notes about this credential..."
                  rows={2}
                  className="w-full border rounded-lg px-4 py-2 focus:outline-none resize-y"
                  style={{ 
                    background: 'var(--theme-surface-variant)', 
                    borderColor: 'var(--theme-border)', 
                    color: 'var(--theme-text)' 
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                  onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button 
                  onClick={handleSave}
                  disabled={isSaving}
                  className="flex-1 text-white font-medium py-2 px-4 rounded-lg transition"
                  style={{ 
                    background: isSaving ? 'var(--theme-text-muted)' : 'var(--theme-success)',
                    opacity: isSaving ? 0.5 : 1,
                    cursor: isSaving ? 'not-allowed' : 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    if (!isSaving) {
                      e.currentTarget.style.background = 'var(--theme-success-hover)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSaving) {
                      e.currentTarget.style.background = 'var(--theme-success)';
                    }
                  }}
                >
                  {isSaving ? 'Saving...' : 'Save Credential'}
                </button>
                <button 
                  onClick={resetForm}
                  className="flex-1 font-medium py-2 px-4 rounded-lg transition"
                  style={{ 
                    background: 'var(--theme-surface-variant)', 
                    color: 'var(--theme-text)' 
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-surface-hover)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-surface-variant)'}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* CREDENTIALS LIST */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>
          Your Credentials
        </h3>

        {credentials.length === 0 ? (
          <div 
            className="rounded-lg p-12 border text-center" 
            style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}
          >
            <p style={{ color: 'var(--theme-text-secondary)' }}>
              No credentials configured yet. Click "Add New Credential" above to get started.
            </p>
          </div>
        ) : (
          credentials.map((credential) => {
            const statusBadge = credential.is_active 
              ? { text: '✓ Active', color: 'var(--theme-success)', opacity: 0.7 }
              : { text: '✗ Inactive', color: 'var(--theme-danger)', opacity: 0.7 };

            return (
              <div
                key={credential.id}
                className="rounded-lg p-6 border"
                style={{
                  background: 'var(--theme-surface)',
                  borderColor: 'var(--theme-border)',
                  opacity: !credential.is_active ? 0.6 : 1
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full flex items-center justify-center text-2xl" style={{ background: 'var(--theme-primary)', color: 'white' }}>
                      <i className="fas fa-key"></i>
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>
                          {credential.name}
                        </h4>
                        <span 
                          className="text-xs px-2 py-1 rounded-full font-semibold" 
                          style={{ background: 'var(--theme-info)', color: 'white' }}
                        >
                          {credential.service_type}
                        </span>
                        <span 
                          className="text-xs px-2 py-1 rounded-full" 
                          style={{ background: statusBadge.color, color: 'white', opacity: statusBadge.opacity }}
                        >
                          {statusBadge.text}
                        </span>
                      </div>
                      <p className="text-sm mt-1" style={{ color: 'var(--theme-text-secondary)' }}>
                        {credentialTypes[credential.auth_type]?.name || credential.auth_type}
                      </p>
                      {credential.description && (
                        <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                          {credential.description}
                        </p>
                      )}
                      {credential.last_used_at && (
                        <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                          Last used: {new Date(credential.last_used_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleDelete(credential.id, credential.name)}
                      className="text-sm px-3 py-1 rounded transition"
                      style={{ background: 'var(--theme-danger)', color: 'white' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-danger-hover)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-danger)'}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

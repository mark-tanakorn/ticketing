'use client';

import { useState, useEffect } from 'react';
import ProviderIcon from './ProviderIcon';
import PasswordInput from '../../components/PasswordInput';
import {
  getAvailableProviders,
  getAISettings,
  addAIProvider,
  updateAIProvider,
  updateAISettings,
  deleteAIProvider,
  validateAIProvider,
  type AIProviderConfig,
  type AISettings,
  type ValidateProviderResponse,
  type ProviderMetadata,
} from '@/lib/editor';

export default function AIProvidersSection() {
  // State management
  const [isEditing, setIsEditing] = useState(false);
  const [editingProviderKey, setEditingProviderKey] = useState<string | null>(null);
  
  // Data states
  const [aiSettings, setAiSettings] = useState<AISettings | null>(null);
  const [availableProviders, setAvailableProviders] = useState<Record<string, ProviderMetadata>>({});
  
  // Form states
  const [formData, setFormData] = useState<Partial<AIProviderConfig>>({
    provider_type: 'openai',
    role: 'inactive',
    enabled: true,
    api_key: '',
    base_url: 'https://api.openai.com/v1', // Default to OpenAI
    default_model: '',
    max_tokens: 4096,
  });
  
  // Validation states
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidateProviderResponse | null>(null);
  const [availableModels, setAvailableModels] = useState<Array<{ id: string; name?: string }>>([]);
  
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
      
      const [settingsData, providersData] = await Promise.all([
        getAISettings(),
        getAvailableProviders(),
      ]);
      
      setAiSettings(settingsData);
      setAvailableProviders(providersData.providers);
    } catch (err) {
      console.error('Failed to load AI settings:', err);
      setError('Failed to load AI settings');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle validation
  const handleValidate = async () => {
    // For local providers, fetch models from Ollama API
    if (formData.provider_type === 'local') {
      try {
        setIsValidating(true);
        setValidationResult(null);
        
        const baseUrl = formData.base_url || 'http://localhost:11434';
        
        // Fetch models from Ollama API
        const response = await fetch(`${baseUrl}/api/tags`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch models from Ollama: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Ollama returns { models: [{ name: "llama3", ... }, ...] }
        if (data.models && Array.isArray(data.models)) {
          const models = data.models.map((model: any) => ({
            id: model.name,
            name: model.name,
          }));
          
          setAvailableModels(models);
          setValidationResult({ valid: true });
          
          // Auto-select first model if none selected
          if (!formData.default_model && models.length > 0) {
            setFormData(prev => ({ ...prev, default_model: models[0].id }));
          }
          
          if (models.length === 0) {
            alert('No models found in Ollama. Please pull a model first:\n\nollama pull llama3');
          }
        } else {
          throw new Error('Invalid response from Ollama API');
        }
      } catch (err: any) {
        console.error('Ollama fetch error:', err);
        alert(`Failed to fetch models from Ollama:\n\n${err.message}\n\nMake sure Ollama is running at: ${formData.base_url || 'http://localhost:11434'}`);
      } finally {
        setIsValidating(false);
      }
      return;
    }

    if (!formData.provider_type || !formData.api_key) {
      alert('Please provide provider type and API key');
      return;
    }

    try {
      setIsValidating(true);
      setValidationResult(null);
      
      const result = await validateAIProvider({
        provider_type: formData.provider_type,
        api_key: formData.api_key,
        base_url: formData.base_url,
      });
      
      setValidationResult(result);
      
      if (result.valid && result.models) {
        setAvailableModels(result.models);
        // Auto-select first model if none selected
        if (!formData.default_model && result.models.length > 0) {
          setFormData(prev => ({ ...prev, default_model: result.models![0].id }));
        }
      } else {
        alert(`Validation failed: ${result.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      console.error('Validation error:', err);
      alert(`Validation failed: ${err.message}`);
    } finally {
      setIsValidating(false);
    }
  };

  // Handle save provider
  const handleSave = async () => {
    const isLocal = formData.provider_type === 'local';
    
    if (!formData.name || !formData.provider_type || !formData.default_model) {
      alert('Please fill in all required fields and validate first');
      return;
    }

    if (!isLocal && !formData.api_key) {
      alert('Please provide an API key');
      return;
    }

    if (!validationResult?.valid) {
      alert('Please validate the provider first');
      return;
    }

    try {
      setIsSaving(true);
      
      const config: AIProviderConfig = {
        name: formData.name!,
        provider_type: formData.provider_type,
        role: formData.role as 'primary' | 'fallback' | 'inactive',
        enabled: formData.enabled!,
        api_key: formData.api_key || '', // Empty for local
        base_url: formData.base_url,
        default_model: formData.default_model,
        available_models: availableModels.map(m => m.id),
        max_tokens: formData.max_tokens,
      };

      if (editingProviderKey) {
        // Update existing
        await updateAIProvider(editingProviderKey, config);
      } else {
        // Add new
        await addAIProvider(formData.name!, config);
      }

      // Reload data and reset form
      await loadData();
      resetForm();
      alert('Provider saved successfully!');
    } catch (err: any) {
      console.error('Save error:', err);
      alert(`Failed to save: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Handle delete
  const handleDelete = async (providerKey: string) => {
    if (!confirm(`Are you sure you want to delete "${providerKey}"?`)) {
      return;
    }

    try {
      await deleteAIProvider(providerKey);
      await loadData();
      alert('Provider deleted successfully!');
    } catch (err: any) {
      console.error('Delete error:', err);
      alert(`Failed to delete: ${err.message}`);
    }
  };

  // Handle edit
  const handleEdit = (providerKey: string, config: AIProviderConfig) => {
    setEditingProviderKey(providerKey);
    setFormData(config);
    setIsEditing(true);
    setValidationResult({ valid: true }); // Assume already validated
    setAvailableModels((config.available_models || []).map(id => ({ id })));
  };

  // Reset form
  const resetForm = () => {
    setIsEditing(false);
    setEditingProviderKey(null);
    setFormData({
      provider_type: 'openai',
      role: 'inactive',
      enabled: true,
      api_key: '',
      base_url: 'https://api.openai.com/v1',
      default_model: '',
      max_tokens: 4096,
    });
    setValidationResult(null);
    setAvailableModels([]);
  };

  // Get providers sorted by role
  const getSortedProviders = () => {
    if (!aiSettings) return [];
    
    const providers = Object.entries(aiSettings.providers || {});
    
    const primary = providers.filter(([_, config]) => config.role === 'primary');
    const fallback = providers
      .filter(([_, config]) => config.role === 'fallback')
      .sort(([_, a], [__, b]) => (a.fallback_priority || 999) - (b.fallback_priority || 999));
    const inactive = providers.filter(([_, config]) => config.role === 'inactive');
    
    return [...primary, ...fallback, ...inactive];
  };

  // Get default base URL for provider type
  const getDefaultBaseUrl = (providerType: string): string => {
    const urlMap: Record<string, string> = {
      openai: 'https://api.openai.com/v1',
      anthropic: 'https://api.anthropic.com/v1',
      deepseek: 'https://api.deepseek.com',
      local: 'http://localhost:11434',
      google: 'https://generativelanguage.googleapis.com/v1',
      cohere: 'https://api.cohere.ai/v1',
      mistral: 'https://api.mistral.ai/v1',
      groq: 'https://api.groq.com/openai/v1',
      perplexity: 'https://api.perplexity.ai',
      together: 'https://api.together.xyz/v1',
      replicate: 'https://api.replicate.com/v1',
      huggingface: 'https://api-inference.huggingface.co/models',
    };
    return urlMap[providerType] || '';
  };

  // Handle provider type change - auto-fill base URL
  const handleProviderTypeChange = (newType: string) => {
    setFormData(prev => ({
      ...prev,
      provider_type: newType,
      base_url: getDefaultBaseUrl(newType),
    }));
    // Reset validation when provider type changes
    setValidationResult(null);
    setAvailableModels([]);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="text-lg" style={{ color: 'var(--theme-text)' }}>Loading AI providers...</div>
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
          AI Providers
        </h2>
        <p className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
          Configure your AI providers. Set one as Primary, add Fallbacks for redundancy, or keep providers Inactive for later use.
        </p>
      </div>

      {/* TOP STICKY CARD - Add/Edit Provider */}
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
            <span>Add New Provider</span>
          </button>
        ) : (
          // Editing state: Show the form
          <div>
            <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--theme-text)' }}>
              {editingProviderKey ? 'Edit Provider' : 'Add New Provider'}
            </h3>
            
            <div className="space-y-4">
              {/* Provider Type Dropdown */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                  Provider Type
                </label>
                <select 
                  value={formData.provider_type}
                  onChange={(e) => handleProviderTypeChange(e.target.value)}
                  className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                  style={{ 
                    background: 'var(--theme-surface-variant)', 
                    borderColor: 'var(--theme-border)', 
                    color: 'var(--theme-text)' 
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                  onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                >
                  <optgroup label="Popular">
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="deepseek">DeepSeek</option>
                    <option value="local">Self-Hosted</option>
                  </optgroup>
                  <optgroup label="Cloud Providers">
                    <option value="google">Google AI - Gemini</option>
                    <option value="cohere">Cohere - Command R+</option>
                    <option value="mistral">Mistral AI</option>
                    <option value="groq">Groq - Ultra Fast!</option>
                    <option value="perplexity">Perplexity AI - Web Search</option>
                    <option value="together">Together AI</option>
                    <option value="replicate">Replicate</option>
                    <option value="huggingface">HuggingFace</option>
                  </optgroup>
                </select>
              </div>

              {/* Provider Name */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                  Provider Name
                </label>
                <input
                  type="text"
                  value={formData.name || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., My OpenAI Provider"
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

              {/* API Key */}
              {formData.provider_type !== 'local' && (
                <div>
                  <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                    API Key
                  </label>
                  <PasswordInput
                    value={formData.api_key || ''}
                    onChange={(value) => setFormData(prev => ({ ...prev, api_key: value }))}
                    placeholder="sk-..."
                  />
                </div>
              )}

              {/* Base URL */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                  Base URL {formData.provider_type === 'local' && '(Ollama)'}
                </label>
                <input
                  type="text"
                  value={formData.base_url || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, base_url: e.target.value }))}
                  placeholder={formData.provider_type === 'local' ? 'http://localhost:11434' : 'https://api.openai.com/v1'}
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

              {/* Role */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                  Role
                </label>
                <select 
                  value={formData.role}
                  onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value as any }))}
                  className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                  style={{ 
                    background: 'var(--theme-surface-variant)', 
                    borderColor: 'var(--theme-border)', 
                    color: 'var(--theme-text)' 
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                  onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                >
                  <option value="primary">Primary (Main provider)</option>
                  <option value="fallback">Fallback (Backup provider)</option>
                  <option value="inactive">Inactive (Configured but not used)</option>
                </select>
              </div>

              {/* Validate Button */}
              <button 
                onClick={handleValidate}
                disabled={isValidating || (formData.provider_type !== 'local' && !formData.api_key)}
                className="w-full text-white font-medium py-2 px-4 rounded-lg transition"
                style={{ 
                  background: isValidating || (formData.provider_type !== 'local' && !formData.api_key) ? 'var(--theme-text-muted)' : 'var(--theme-info)',
                  opacity: isValidating || (formData.provider_type !== 'local' && !formData.api_key) ? 0.5 : 1,
                  cursor: isValidating || (formData.provider_type !== 'local' && !formData.api_key) ? 'not-allowed' : 'pointer'
                }}
                onMouseEnter={(e) => {
                  if (!isValidating && (formData.provider_type === 'local' || formData.api_key)) {
                    e.currentTarget.style.background = 'var(--theme-info)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isValidating && (formData.provider_type === 'local' || formData.api_key)) {
                    e.currentTarget.style.background = 'var(--theme-info)';
                  }
                }}
              >
                {isValidating 
                  ? 'Validating...' 
                  : validationResult?.valid 
                    ? '✓ Validated - Fetch Models' 
                    : formData.provider_type === 'local' 
                      ? 'Load Available Models' 
                      : 'Validate & Fetch Models'}
              </button>

              {/* Model Selection (disabled until validated) */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: 'var(--theme-text)' }}>
                  Model
                </label>
                <select 
                  value={formData.default_model || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, default_model: e.target.value }))}
                  disabled={!validationResult?.valid || availableModels.length === 0}
                  className="w-full border rounded-lg px-4 py-2 focus:outline-none"
                  style={{ 
                    background: 'var(--theme-surface-variant)', 
                    borderColor: 'var(--theme-border)', 
                    color: 'var(--theme-text)',
                    opacity: !validationResult?.valid || availableModels.length === 0 ? 0.5 : 1,
                    cursor: !validationResult?.valid || availableModels.length === 0 ? 'not-allowed' : 'pointer'
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = 'var(--theme-primary)'}
                  onBlur={(e) => e.currentTarget.style.borderColor = 'var(--theme-border)'}
                >
                  {availableModels.length === 0 ? (
                    <option>Validate first to fetch models</option>
                  ) : (
                    availableModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id}
                      </option>
                    ))
                  )}
                </select>
                <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                  Click "Validate" above to fetch available models
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button 
                  onClick={handleSave}
                  disabled={isSaving || !validationResult?.valid}
                  className="flex-1 text-white font-medium py-2 px-4 rounded-lg transition"
                  style={{ 
                    background: isSaving || !validationResult?.valid ? 'var(--theme-text-muted)' : 'var(--theme-success)',
                    opacity: isSaving || !validationResult?.valid ? 0.5 : 1,
                    cursor: isSaving || !validationResult?.valid ? 'not-allowed' : 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    if (!isSaving && validationResult?.valid) {
                      e.currentTarget.style.background = 'var(--theme-success-hover)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSaving && validationResult?.valid) {
                      e.currentTarget.style.background = 'var(--theme-success)';
                    }
                  }}
                >
                  {isSaving ? 'Saving...' : 'Save Provider'}
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

      {/* PROVIDER LIST */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>
          Your Providers
        </h3>

        {getSortedProviders().length === 0 ? (
          <div 
            className="rounded-lg p-12 border text-center" 
            style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}
          >
            <p style={{ color: 'var(--theme-text-secondary)' }}>
              No providers configured yet. Click "Add New Provider" above to get started.
            </p>
          </div>
        ) : (
          getSortedProviders().map(([providerKey, config]) => {
            const badge = 
              config.role === 'primary' ? { text: 'PRIMARY', color: 'var(--theme-success)' } :
              config.role === 'fallback' ? { text: `FALLBACK #${config.fallback_priority || 1}`, color: 'var(--theme-warning)' } :
              { text: 'INACTIVE', color: 'var(--theme-text-muted)' };

            const statusBadge = config.enabled 
              ? { text: '✓ Enabled', color: 'var(--theme-success)', opacity: 0.7 }
              : { text: '✗ Disabled', color: 'var(--theme-danger)', opacity: 0.7 };

            return (
              <div 
                key={providerKey}
                className="rounded-lg p-6 border" 
                style={{ 
                  background: 'var(--theme-surface)', 
                  borderColor: 'var(--theme-border)',
                  opacity: config.role === 'inactive' ? 0.6 : 1
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <ProviderIcon provider={config.provider_type} size={48} />
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>
                          {config.name || providerKey}
                        </h4>
                        <span 
                          className="text-xs px-2 py-1 rounded-full font-semibold" 
                          style={{ background: badge.color, color: 'white' }}
                        >
                          {badge.text}
                        </span>
                        <span 
                          className="text-xs px-2 py-1 rounded-full" 
                          style={{ background: statusBadge.color, color: 'white', opacity: statusBadge.opacity }}
                        >
                          {statusBadge.text}
                        </span>
                      </div>
                      <p className="text-sm mt-1" style={{ color: 'var(--theme-text-secondary)' }}>
                        {config.default_model}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => handleEdit(providerKey, config)}
                      className="text-sm px-3 py-1 rounded transition"
                      style={{ background: 'var(--theme-primary)', color: 'white' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--theme-primary-hover)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'var(--theme-primary)'}
                    >
                      Edit
                    </button>
                    <button 
                      onClick={() => handleDelete(providerKey)}
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

      {/* Global AI Settings */}
      <div>
        <h3 className="text-xl font-semibold mb-4" style={{ color: 'var(--theme-text)' }}>
          Global AI Settings
        </h3>
        <p className="text-sm mb-4" style={{ color: 'var(--theme-text-secondary)' }}>
          Configure default AI behavior and timeouts for all providers
        </p>

        {aiSettings && (
          <div className="rounded-lg p-6 border space-y-6" style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)' }}>
            {/* Request Timeout */}
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>
                Request Timeout (seconds)
              </label>
              <input
                type="number"
                min={10}
                max={600}
                value={aiSettings.request_timeout}
                onChange={(e) => setAiSettings({ ...aiSettings, request_timeout: parseInt(e.target.value) })}
                className="w-full px-4 py-2 border rounded-lg"
                style={{
                  background: 'var(--theme-surface-variant)',
                  borderColor: 'var(--theme-border)',
                  color: 'var(--theme-text)',
                }}
              />
              <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                Timeout for AI/LLM API calls (default: 120s)
              </p>
            </div>

            {/* Default Temperature */}
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>
                Default Temperature
              </label>
              <input
                type="number"
                step={0.1}
                min={0}
                max={2}
                value={aiSettings.default_temperature}
                onChange={(e) => setAiSettings({ ...aiSettings, default_temperature: parseFloat(e.target.value) })}
                className="w-full px-4 py-2 border rounded-lg"
                style={{
                  background: 'var(--theme-surface-variant)',
                  borderColor: 'var(--theme-border)',
                  color: 'var(--theme-text)',
                }}
              />
              <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                Default sampling temperature (0 = deterministic, 2 = very creative)
              </p>
            </div>

            {/* Default Max Tokens */}
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>
                Default Max Tokens
              </label>
              <input
                type="number"
                min={100}
                max={200000}
                value={aiSettings.default_max_tokens}
                onChange={(e) => setAiSettings({ ...aiSettings, default_max_tokens: parseInt(e.target.value) })}
                className="w-full px-4 py-2 border rounded-lg"
                style={{
                  background: 'var(--theme-surface-variant)',
                  borderColor: 'var(--theme-border)',
                  color: 'var(--theme-text)',
                }}
              />
              <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                Default maximum tokens for LLM responses
              </p>
            </div>

            {/* Max Retries */}
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>
                Max Retries
              </label>
              <input
                type="number"
                min={0}
                max={10}
                value={aiSettings.max_retries}
                onChange={(e) => setAiSettings({ ...aiSettings, max_retries: parseInt(e.target.value) })}
                className="w-full px-4 py-2 border rounded-lg"
                style={{
                  background: 'var(--theme-surface-variant)',
                  borderColor: 'var(--theme-border)',
                  color: 'var(--theme-text)',
                }}
              />
              <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                Maximum retry attempts for failed AI requests
              </p>
            </div>

            {/* Retry Delay */}
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>
                Retry Delay (seconds)
              </label>
              <input
                type="number"
                step={0.1}
                min={0.1}
                max={30}
                value={aiSettings.retry_delay}
                onChange={(e) => setAiSettings({ ...aiSettings, retry_delay: parseFloat(e.target.value) })}
                className="w-full px-4 py-2 border rounded-lg"
                style={{
                  background: 'var(--theme-surface-variant)',
                  borderColor: 'var(--theme-border)',
                  color: 'var(--theme-text)',
                }}
              />
              <p className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                Delay between retry attempts (seconds)
              </p>
            </div>

            {/* Save Button */}
            <button
              onClick={async () => {
                setIsSaving(true);
                try {
                  await updateAISettings(aiSettings);
                  alert('Global AI settings saved successfully!');
                  await loadData();
                } catch (err) {
                  console.error('Failed to save settings:', err);
                  alert('Failed to save settings');
                } finally {
                  setIsSaving(false);
                }
              }}
              disabled={isSaving}
              className="w-full py-2 rounded-lg font-medium transition"
              style={{
                background: isSaving ? 'var(--theme-surface-variant)' : 'var(--theme-primary)',
                color: 'white',
                cursor: isSaving ? 'not-allowed' : 'pointer',
              }}
              onMouseEnter={(e) => !isSaving && (e.currentTarget.style.background = 'var(--theme-primary-hover)')}
              onMouseLeave={(e) => !isSaving && (e.currentTarget.style.background = 'var(--theme-primary)')}
            >
              {isSaving ? 'Saving...' : 'Save Global Settings'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}


/**
 * Example: How to integrate HuggingFaceModelBrowser in ConfigPanel
 * 
 * This shows how to use the HuggingFace marketplace browser component
 * in your node configuration panel.
 */

import React from 'react';
import HuggingFaceModelBrowser from '@/components/HuggingFaceModelBrowser';
import type { ModelDetails } from '@/lib/huggingface-api';

// Example: In your ConfigPanel component
export function HuggingFaceConfigExample() {
  const [selectedModel, setSelectedModel] = React.useState<ModelDetails | null>(null);
  const [config, setConfig] = React.useState({
    model_marketplace: {
      model_id: '',
      task: '',
      model_info: null as ModelDetails | null,
    },
    inference_mode: 'local',
    common_parameters: {
      max_length: 100,
      temperature: 0.7,
    },
  });

  const handleModelSelected = (model: ModelDetails) => {
    console.log('Model selected:', model);
    
    // Update your node config
    setConfig(prev => ({
      ...prev,
      model_marketplace: {
        model_id: model.model_id,
        task: model.pipeline_tag || 'unknown',
        model_info: model,
      },
    }));
    
    setSelectedModel(model);
  };

  return (
    <div className="config-panel">
      <h3>HuggingFace Model Configuration</h3>
      
      {/* Model Selection */}
      <div className="config-section">
        <label>Select Model</label>
        <HuggingFaceModelBrowser
          onModelSelected={handleModelSelected}
          initialModelId={config.model_marketplace.model_id}
          enableFilters={true}
          itemsPerPage={20}
        />
      </div>
      
      {/* Show selected model info */}
      {selectedModel && (
        <div className="config-section">
          <label>Selected: {selectedModel.model_id}</label>
          <p>Task: {selectedModel.pipeline_tag}</p>
        </div>
      )}
      
      {/* Inference Mode */}
      <div className="config-section">
        <label>Inference Mode</label>
        <select
          value={config.inference_mode}
          onChange={(e) => setConfig(prev => ({
            ...prev,
            inference_mode: e.target.value,
          }))}
        >
          <option value="local">🖥️ Local (Download & Run)</option>
          <option value="api">🌐 API (HuggingFace Inference API)</option>
        </select>
        <small>
          {config.inference_mode === 'local'
            ? 'Download model once and run locally. Privacy-first, no API calls after download.'
            : 'Use HuggingFace Inference API. No download needed. Requires API credential.'}
        </small>
      </div>
      
      {/* Credential Selection (for API mode) */}
      {config.inference_mode === 'api' && (
        <div className="config-section">
          <label>HuggingFace API Credential</label>
          {/* Use your existing CredentialPicker component */}
          <select>
            <option value="">Select credential...</option>
            {/* Load credentials with service_type="huggingface" */}
          </select>
          <small>
            Create a HuggingFace API Key credential in Settings with service_type='huggingface'
          </small>
        </div>
      )}
      
      {/* Task-specific Parameters */}
      {selectedModel?.pipeline_tag && (
        <div className="config-section">
          <label>Parameters</label>
          <TaskSpecificParameters
            task={selectedModel.pipeline_tag}
            parameters={config.common_parameters}
            onChange={(params) => setConfig(prev => ({
              ...prev,
              common_parameters: params,
            }))}
          />
        </div>
      )}
    </div>
  );
}

// Helper component for task-specific parameters
function TaskSpecificParameters({
  task,
  parameters,
  onChange,
}: {
  task: string;
  parameters: any;
  onChange: (params: any) => void;
}) {
  // Show different parameters based on task type
  switch (task) {
    case 'text-generation':
      return (
        <>
          <div>
            <label>Max Length</label>
            <input
              type="number"
              value={parameters.max_length}
              onChange={(e) => onChange({ ...parameters, max_length: parseInt(e.target.value) })}
              min="1"
              max="2048"
            />
          </div>
          <div>
            <label>Temperature</label>
            <input
              type="range"
              value={parameters.temperature}
              onChange={(e) => onChange({ ...parameters, temperature: parseFloat(e.target.value) })}
              min="0.1"
              max="2.0"
              step="0.1"
            />
            <span>{parameters.temperature}</span>
          </div>
        </>
      );
      
    case 'text-classification':
      return (
        <div>
          <label>Return All Scores</label>
          <input
            type="checkbox"
            checked={parameters.return_all_scores || false}
            onChange={(e) => onChange({ ...parameters, return_all_scores: e.target.checked })}
          />
        </div>
      );
      
    case 'image-classification':
      return (
        <div>
          <label>Top K Results</label>
          <input
            type="number"
            value={parameters.top_k || 5}
            onChange={(e) => onChange({ ...parameters, top_k: parseInt(e.target.value) })}
            min="1"
            max="20"
          />
        </div>
      );
      
    default:
      return <p>No additional parameters for this task</p>;
  }
}

/**
 * Alternative: Simpler integration if you just need the browser
 */
export function SimpleHuggingFaceIntegration() {
  return (
    <HuggingFaceModelBrowser
      onModelSelected={(model) => {
        console.log('User selected:', model);
        // Do something with the model...
      }}
    />
  );
}


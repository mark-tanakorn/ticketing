/**
 * HuggingFace Model Browser Component
 * 
 * A marketplace-style browser for searching and selecting HuggingFace models.
 * Provides search, filtering, sorting, and model selection functionality.
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  searchModels,
  getModelDetails,
  getTasks,
  type HuggingFaceModel,
  type ModelDetails,
  type HuggingFaceTask,
} from '@/lib/huggingface-api';
import './HuggingFaceModelBrowser.css';

interface HuggingFaceModelBrowserProps {
  onModelSelected: (model: ModelDetails) => void;
  initialModelId?: string;
  enableFilters?: boolean;
  itemsPerPage?: number;
}

export default function HuggingFaceModelBrowser({
  onModelSelected,
  initialModelId,
  enableFilters = true,
  itemsPerPage = 20,
}: HuggingFaceModelBrowserProps) {
  // State
  const [models, setModels] = useState<HuggingFaceModel[]>([]);
  const [tasks, setTasks] = useState<HuggingFaceTask[]>([]);
  const [selectedModel, setSelectedModel] = useState<ModelDetails | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Search and filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [taskFilter, setTaskFilter] = useState('');
  const [libraryFilter, setLibraryFilter] = useState('');
  const [languageFilter, setLanguageFilter] = useState('');
  const [sortBy, setSortBy] = useState<'downloads' | 'likes' | 'trending' | 'lastModified'>('downloads');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  
  // Load tasks on mount
  useEffect(() => {
    loadTasks();
  }, []);
  
  // Load initial model if provided
  useEffect(() => {
    if (initialModelId) {
      handleSelectModel(initialModelId);
    }
  }, [initialModelId]);
  
  // Load models when search params change
  useEffect(() => {
    loadModels();
  }, [searchQuery, taskFilter, libraryFilter, languageFilter, sortBy, currentPage]);
  
  const loadTasks = async () => {
    try {
      const data = await getTasks();
      setTasks(data.tasks);
    } catch (err) {
      console.error('Failed to load tasks:', err);
    }
  };
  
  const loadModels = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await searchModels({
        query: searchQuery || undefined,
        task: taskFilter || undefined,
        library: libraryFilter || undefined,
        language: languageFilter || undefined,
        sort: sortBy,
        limit: itemsPerPage,
        page: currentPage,
      });
      
      setModels(data.models);
      setHasMore(data.models.length === itemsPerPage);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load models');
      setModels([]);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSelectModel = async (modelId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const details = await getModelDetails(modelId);
      setSelectedModel(details);
      
      // Pass the model details back with task information
      onModelSelected(details);
      
      // Log for debugging
      console.log('✅ Model selected:', {
        model_id: details.model_id,
        task: details.pipeline_tag,
        library: details.library_name
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load model details');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    setCurrentPage(1);
  }, []);
  
  const handleClearFilters = () => {
    setTaskFilter('');
    setLibraryFilter('');
    setLanguageFilter('');
    setCurrentPage(1);
  };
  
  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };
  
  return (
    <div className="hf-browser-container">
      {/* Search and Filter Section */}
      <div className="hf-browser-header">
        <div className="hf-search-section">
          <div className="hf-search-input-group">
            <input
              type="text"
              className="hf-search-input"
              placeholder="Search HuggingFace models (e.g., 'bert', 'gpt', 'sentiment')..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
            />
            <button 
              className="hf-search-btn"
              onClick={() => loadModels()}
            >
              <i className="fas fa-search"></i>
            </button>
          </div>
          
          {enableFilters && (
            <div className="hf-filters">
              <select
                className="hf-filter-select"
                value={taskFilter}
                onChange={(e) => {
                  setTaskFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="">All Tasks</option>
                {tasks.map((task) => (
                  <option key={task.value} value={task.value}>
                    {task.label}
                  </option>
                ))}
              </select>
              
              <select
                className="hf-filter-select"
                value={libraryFilter}
                onChange={(e) => {
                  setLibraryFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="">All Libraries</option>
                <option value="transformers">Transformers</option>
                <option value="sentence-transformers">Sentence Transformers</option>
                <option value="diffusers">Diffusers</option>
              </select>
              
              <select
                className="hf-filter-select"
                value={languageFilter}
                onChange={(e) => {
                  setLanguageFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="">All Languages</option>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="zh">Chinese</option>
                <option value="ja">Japanese</option>
              </select>
              
              <button
                className="hf-clear-filters-btn"
                onClick={handleClearFilters}
              >
                <i className="fas fa-eraser"></i> Clear
              </button>
            </div>
          )}
        </div>
        
        <div className="hf-results-info">
          <span>
            {isLoading ? 'Loading...' : `${models.length} models found`}
          </span>
          <select
            className="hf-sort-select"
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value as any);
              setCurrentPage(1);
            }}
          >
            <option value="downloads">Most Downloaded</option>
            <option value="lastModified">Recently Updated</option>
            <option value="likes">Most Liked</option>
            <option value="trending">Trending</option>
          </select>
        </div>
      </div>
      
      {/* Models Grid */}
      <div className="hf-models-section">
        {error && (
          <div className="hf-error">
            <i className="fas fa-exclamation-triangle fa-3x"></i>
            <h3>Error Loading Models</h3>
            <p>{error}</p>
            <button className="hf-retry-btn" onClick={loadModels}>
              <i className="fas fa-redo"></i> Retry
            </button>
          </div>
        )}
        
        {isLoading && models.length === 0 && (
          <div className="hf-loading">
            <div className="hf-loading-spinner"></div>
            <p>Loading HuggingFace models...</p>
          </div>
        )}
        
        {!error && !isLoading && models.length === 0 && (
          <div className="hf-no-results">
            <i className="fas fa-search fa-3x"></i>
            <h3>No models found</h3>
            <p>Try adjusting your search terms or filters</p>
            {(taskFilter || libraryFilter || languageFilter) && (
              <button
                className="hf-clear-filters-btn"
                onClick={handleClearFilters}
              >
                <i className="fas fa-eraser"></i> Clear Filters
              </button>
            )}
          </div>
        )}
        
        {!error && models.length > 0 && (
          <>
            <div className="hf-models-grid">
              {models.map((model) => (
                <ModelCard
                  key={model.model_id}
                  model={model}
                  isSelected={selectedModel?.model_id === model.model_id}
                  onSelect={handleSelectModel}
                  formatNumber={formatNumber}
                />
              ))}
            </div>
            
            {/* Pagination */}
            <div className="hf-pagination">
              <button
                className="hf-page-btn"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(p => p - 1)}
              >
                <i className="fas fa-chevron-left"></i> Previous
              </button>
              <span className="hf-page-info">
                Page {currentPage} {hasMore ? '(more available)' : '(last page)'}
              </span>
              <button
                className="hf-page-btn"
                disabled={!hasMore}
                onClick={() => setCurrentPage(p => p + 1)}
              >
                Next <i className="fas fa-chevron-right"></i>
              </button>
            </div>
          </>
        )}
      </div>
      
      {/* Selected Model Panel */}
      {selectedModel && (
        <SelectedModelPanel
          model={selectedModel}
          onClear={() => setSelectedModel(null)}
          formatNumber={formatNumber}
        />
      )}
    </div>
  );
}

// Model Card Component
interface ModelCardProps {
  model: HuggingFaceModel;
  isSelected: boolean;
  onSelect: (modelId: string) => void;
  formatNumber: (num: number) => string;
}

function ModelCard({ model, isSelected, onSelect, formatNumber }: ModelCardProps) {
  return (
    <div
      className={`hf-model-card ${isSelected ? 'selected' : ''}`}
      onClick={() => onSelect(model.model_id)}
    >
      <div className="hf-model-header">
        <div className="hf-model-title">
          <h4>{model.model_id.split('/').pop()?.replace(/-/g, ' ')}</h4>
          <span className="hf-model-author">by {model.author || 'Unknown'}</span>
        </div>
        <i className="fas fa-check-circle hf-compatible"></i>
      </div>
      
      <div className="hf-model-info">
        {model.pipeline_tag && (
          <span className="hf-task-badge">{model.pipeline_tag}</span>
        )}
        {model.library_name && (
          <span className="hf-library-badge">{model.library_name}</span>
        )}
      </div>
      
      <div className="hf-model-description">
        {model.model_id}
      </div>
      
      <div className="hf-model-stats">
        <span className="hf-stat">
          <i className="fas fa-download"></i> {formatNumber(model.downloads)}
        </span>
        <span className="hf-stat">
          <i className="fas fa-heart"></i> {formatNumber(model.likes)}
        </span>
      </div>
    </div>
  );
}

// Selected Model Panel Component
interface SelectedModelPanelProps {
  model: ModelDetails;
  onClear: () => void;
  formatNumber: (num: number) => string;
}

function SelectedModelPanel({ model, onClear, formatNumber }: SelectedModelPanelProps) {
  return (
    <div className="hf-external-selected-model">
      <div className="hf-selected-header">
        <h4>
          <i className="fas fa-check-circle"></i> Selected Model
        </h4>
        <button className="hf-clear-btn" onClick={onClear}>
          <i className="fas fa-times"></i> Clear
        </button>
      </div>
      
      <div className="hf-selected-content">
        <div className="hf-selected-details">
          <div className="hf-selected-main">
            <h3>{model.name}</h3>
            <p className="hf-selected-author">by {model.author}</p>
            <p className="hf-selected-id">{model.model_id}</p>
            
            <div className="hf-selected-badges">
              {model.pipeline_tag && (
                <span className="hf-task-badge">{model.pipeline_tag}</span>
              )}
              {model.library_name && (
                <span className="hf-library-badge">{model.library_name}</span>
              )}
              {model.gated && (
                <span className="hf-gated">🔒 Gated</span>
              )}
            </div>
            
            <div className="hf-selected-description">
              {model.description || 'No description available'}
            </div>
          </div>
          
          <div className="hf-selected-meta">
            <div className="hf-selected-stats">
              <div className="hf-stat-item">
                <i className="fas fa-download"></i>
                <span>{formatNumber(model.downloads)} downloads</span>
              </div>
              <div className="hf-stat-item">
                <i className="fas fa-heart"></i>
                <span>{formatNumber(model.likes)} likes</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


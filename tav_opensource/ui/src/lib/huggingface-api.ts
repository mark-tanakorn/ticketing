/**
 * HuggingFace API Client
 * 
 * Functions for interacting with HuggingFace model search and discovery endpoints
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export interface HuggingFaceModel {
  model_id: string;
  author: string | null;
  downloads: number;
  likes: number;
  tags: string[];
  pipeline_tag: string | null;
  library_name: string | null;
  created_at: string | null;
  last_modified: string | null;
}

export interface ModelSearchResponse {
  models: HuggingFaceModel[];
  total: number;
  query: string | null;
}

export interface ModelDetails extends HuggingFaceModel {
  name: string;
  description: string;
  private: boolean;
  gated: boolean;
}

export interface HuggingFaceTask {
  value: string;
  label: string;
  category: string;
}

export interface TasksResponse {
  tasks: HuggingFaceTask[];
}

export interface PopularModelsResponse {
  task: string;
  models: string[];
}

/**
 * Search for HuggingFace models
 */
export async function searchModels(params: {
  query?: string;
  task?: string;
  library?: string;
  language?: string;
  sort?: 'downloads' | 'likes' | 'trending' | 'lastModified';
  limit?: number;
  page?: number;
}): Promise<ModelSearchResponse> {
  const queryParams = new URLSearchParams();
  
  if (params.query) queryParams.append('query', params.query);
  if (params.task) queryParams.append('task', params.task);
  if (params.library) queryParams.append('library', params.library);
  if (params.language) queryParams.append('language', params.language);
  if (params.sort) queryParams.append('sort', params.sort);
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.page) queryParams.append('page', params.page.toString());
  
  const response = await fetch(
    `${API_BASE}/api/v1/huggingface/search?${queryParams}`,
    {
      credentials: 'include',
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to search models: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get detailed information about a specific model
 */
export async function getModelDetails(modelId: string): Promise<ModelDetails> {
  const response = await fetch(
    `${API_BASE}/api/v1/huggingface/model/${encodeURIComponent(modelId)}/info`,
    {
      credentials: 'include',
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to get model details: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data;
}

/**
 * Get model card (README) for a specific model
 */
export async function getModelCard(modelId: string): Promise<{ model_id: string; content: string }> {
  const response = await fetch(
    `${API_BASE}/api/v1/huggingface/model/${encodeURIComponent(modelId)}/card`,
    {
      credentials: 'include',
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to get model card: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get list of available tasks
 */
export async function getTasks(): Promise<TasksResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/huggingface/tasks`,
    {
      credentials: 'include',
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to get tasks: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get popular models for a specific task
 */
export async function getPopularModels(
  task: string,
  limit: number = 10
): Promise<PopularModelsResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/huggingface/popular/${encodeURIComponent(task)}?limit=${limit}`,
    {
      credentials: 'include',
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to get popular models: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get recommended models for a specific task
 */
export async function getRecommendedModels(task: string): Promise<PopularModelsResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/huggingface/recommended/${encodeURIComponent(task)}`,
    {
      credentials: 'include',
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to get recommended models: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get task-specific configuration schema
 */
export async function getTaskConfigSchema(task: string): Promise<{
  task: string;
  parameters: Record<string, any>;
}> {
  const response = await fetch(
    `${API_BASE}/api/v1/huggingface/task-config/${encodeURIComponent(task)}`,
    {
      credentials: 'include',
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to get task configuration: ${response.statusText}`);
  }
  
  return response.json();
}


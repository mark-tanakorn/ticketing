/**
 * Custom Nodes API Client
 * 
 * Functions to interact with the custom node builder backend
 */

import { getApiBaseUrl } from './api-config';

const API_BASE = getApiBaseUrl();

// ==================== Types ====================

export interface Conversation {
  id: string;
  title: string;
  status: string;
  provider: string;
  model: string;
  temperature: string | null;
  requirements: any;
  generated_code: string | null;
  node_type: string | null;
  class_name: string | null;
  validation_status: string | null;
  validation_errors: any;
  message_count: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  provider?: string;
  model?: string;
  activity?: any;
}

export interface AttachmentRef {
  file_id: string;
  filename?: string;
  mime_type?: string;
  file_category?: string;
  file_size_bytes?: number;
}

export interface StartConversationRequest {
  provider: string;
  model: string;
  temperature?: number;
  initial_message?: string;
  attachments?: AttachmentRef[];
}

export interface StartConversationStreamRequest {
  provider: string;
  model: string;
  temperature?: number;
  message: string;
  attachments?: AttachmentRef[];
}

export interface StartConversationResponse {
  success: boolean;
  conversation_id: string;
  title: string;
  assistant_message: string;
  provider: string;
  model: string;
}

export interface SendMessageRequest {
  message: string;
  attachments?: AttachmentRef[];
  provider?: string;
  model?: string;
  temperature?: number;
}

export interface SendMessageResponse {
  success: boolean;
  assistant_message: string;
  ready_to_generate: boolean;
  requirements?: any;
}

export interface ConversationDetailResponse {
  success: boolean;
  conversation: Conversation;
  messages: Message[];
}

// ==================== My Nodes (Library) Types ====================

export interface CustomNodeSummary {
  id: number;
  node_type: string;
  display_name: string;
  description?: string | null;
  category: string;
  icon?: string | null;
  version?: string | null;
  is_active: boolean;
  is_registered: boolean;
  file_path?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomNodeDetail extends CustomNodeSummary {
  code: string;
}

export interface CustomNodeListResponse {
  success: boolean;
  nodes: CustomNodeSummary[];
  total: number;
}

export interface UpdateCustomNodeCodeResponse {
  success: boolean;
  node: CustomNodeDetail;
}

export interface RegisterCustomNodeResponse {
  success: boolean;
  node: CustomNodeSummary;
  message: string;
}

export interface DeleteCustomNodeResponse {
  success: boolean;
  deleted_id: number;
  deleted_node_type: string;
  deleted_file_path?: string | null;
  message: string;
}

export interface GenerateCodeResponse {
  success: boolean;
  code: string;
  node_type: string;
  class_name: string;
  validation_status: string;
  validation_errors?: string[];
}

export interface NodeValidationRequest {
  code: string;
}

export interface ValidationErrorDetail {
  line?: number | null;
  column?: number | null;
  message: string;
  severity?: 'error' | 'warning' | 'info';
}

export interface NodeValidationResponse {
  valid: boolean;
  errors: ValidationErrorDetail[];
  warnings: ValidationErrorDetail[];
  node_type?: string | null;
  class_name?: string | null;
  message?: string | null;
}

export interface SaveNodeRequest {
  conversation_id: string;
  code?: string;
  overwrite?: boolean;
}

export interface SaveNodeResponse {
  success: boolean;
  node_type: string;
  file_path: string;
  message: string;
  registered: boolean;
}

export interface UpdateConversationCodeResponse {
  success: boolean;
  conversation: Conversation;
}

// ==================== API Functions ====================

/**
 * Start a new conversation
 */
export async function startConversation(
  request: StartConversationRequest
): Promise<StartConversationResponse> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/conversations/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start conversation');
  }

  return response.json();
}

/**
 * Send a message in a conversation
 */
export async function sendMessage(
  conversationId: string,
  request: SendMessageRequest
): Promise<SendMessageResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/custom-nodes/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send message');
  }

  return response.json();
}

/**
 * Send a message with streaming response (SSE)
 */
export async function sendMessageStream(
  conversationId: string,
  request: SendMessageRequest,
  onToken: (token: string) => void,
  onDone: (data: { ready_to_generate: boolean; requirements?: any }) => void,
  onStatus: (message: string) => void,
  onGenerationComplete: (data: { success: boolean; node_type?: string; error?: string }) => void,
  onError: (error: string) => void,
  signal?: AbortSignal,
  onEvent?: (event: any) => void
): Promise<void> {
  try {
    const response = await fetch(
      `${API_BASE}/api/v1/custom-nodes/conversations/${conversationId}/messages/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(request),
        signal, // Pass abort signal
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send message');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    // Robust SSE parsing (data lines can be split across chunks)
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Events separated by blank line
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';

      for (const rawEvent of parts) {
        const lines = rawEvent.split('\n');
        const dataLines: string[] = [];
        for (const line of lines) {
          if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trimStart());
          }
        }
        if (!dataLines.length) continue;

        const payloadText = dataLines.join('\n');
        let data: any;
        try {
          data = JSON.parse(payloadText);
        } catch {
          onEvent?.({ type: 'parse_error', raw: payloadText });
          continue;
        }

        switch (data.type) {
          case 'token':
            onToken(data.content);
            break;
          case 'done':
            onDone({
              ready_to_generate: data.ready_to_generate,
              requirements: data.requirements,
            });
            break;
          case 'status':
            onStatus(data.message);
            break;
          case 'generation_complete':
            onGenerationComplete({
              success: data.success,
              node_type: data.node_type,
              error: data.error,
            });
            break;
          case 'error':
            onError(data.message);
            break;
          default:
            onEvent?.(data);
            break;
        }
      }
    }
  } catch (error) {
    // Check if it was a user cancellation
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('Request was cancelled');
      return; // Don't call onError for user cancellations
    }
    onError(error instanceof Error ? error.message : 'Unknown error');
  }
}

/**
 * Start a conversation and stream the first assistant response (SSE).
 * Used by the welcome/new-conversation flow so Activity + tools show up consistently.
 */
export async function startConversationStream(
  request: StartConversationStreamRequest,
  onToken: (token: string) => void,
  onDone: (data: { ready_to_generate: boolean; requirements?: any }) => void,
  onStatus: (message: string) => void,
  onGenerationComplete: (data: { success: boolean; node_type?: string; error?: string }) => void,
  onError: (error: string) => void,
  signal?: AbortSignal,
  onEvent?: (event: any) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/custom-nodes/conversations/start/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(request),
      signal,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start conversation');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    // Robust SSE parsing (data lines can be split across chunks)
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Events separated by blank line
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';

      for (const rawEvent of parts) {
        const lines = rawEvent.split('\n');
        const dataLines: string[] = [];
        for (const line of lines) {
          if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trimStart());
          }
        }
        if (!dataLines.length) continue;

        const payloadText = dataLines.join('\n');
        let data: any;
        try {
          data = JSON.parse(payloadText);
        } catch {
          onEvent?.({ type: 'parse_error', raw: payloadText });
          continue;
        }

        switch (data.type) {
          case 'token':
            onToken(data.content);
            break;
          case 'done':
            onDone({
              ready_to_generate: data.ready_to_generate,
              requirements: data.requirements,
            });
            break;
          case 'status':
            onStatus(data.message);
            break;
          case 'generation_complete':
            onGenerationComplete({
              success: data.success,
              node_type: data.node_type,
              error: data.error,
            });
            break;
          case 'error':
            onError(data.message);
            break;
          default:
            onEvent?.(data);
            break;
        }
      }
    }
  } catch (error) {
    // Check if it was a user cancellation
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('Request was cancelled');
      return; // Don't call onError for user cancellations
    }
    onError(error instanceof Error ? error.message : 'Unknown error');
  }
}

/**
 * Get conversation details with full message history
 */
export async function getConversation(
  conversationId: string
): Promise<ConversationDetailResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/custom-nodes/conversations/${conversationId}`,
    {
      credentials: 'include',
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get conversation');
  }

  return response.json();
}

/**
 * List all conversations
 */
export async function listConversations(status?: string): Promise<Conversation[]> {
  const url = new URL(`${API_BASE}/api/v1/custom-nodes/conversations`);
  if (status) {
    url.searchParams.append('status', status);
  }

  const response = await fetch(url.toString(), {
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to list conversations');
  }

  const data = await response.json();
  return data.conversations;
}

/**
 * Delete a conversation
 */
export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/v1/custom-nodes/conversations/${conversationId}`,
    {
      method: 'DELETE',
      credentials: 'include',
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete conversation');
  }
}

/**
 * Generate code from conversation
 */
export async function generateCode(
  conversationId: string
): Promise<GenerateCodeResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/custom-nodes/conversations/${conversationId}/generate`,
    {
      method: 'POST',
      credentials: 'include',
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate code');
  }

  return response.json();
}

/**
 * Validate custom node code
 */
export async function validateNodeCode(code: string): Promise<NodeValidationResponse> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ code } satisfies NodeValidationRequest),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to validate code');
  }

  return response.json();
}

/**
 * Save (and hot-reload/register) a validated custom node
 */
export async function saveCustomNode(request: SaveNodeRequest): Promise<SaveNodeResponse> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to save node');
  }

  return response.json();
}

/**
 * Save edited code back to the conversation (no filesystem write / no register)
 */
export async function updateConversationCode(
  conversationId: string,
  code: string
): Promise<UpdateConversationCodeResponse> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/conversations/${conversationId}/code`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ code }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to save code');
  }

  return response.json();
}

// ==================== My Nodes (Library) API ====================

export async function listMyCustomNodes(): Promise<CustomNodeListResponse> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/library`, {
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to list custom nodes');
  }
  return response.json();
}

export async function getMyCustomNode(customNodeId: number): Promise<CustomNodeDetail> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/library/${customNodeId}`, {
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get custom node');
  }
  return response.json();
}

export async function updateMyCustomNodeCode(customNodeId: number, code: string): Promise<UpdateCustomNodeCodeResponse> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/library/${customNodeId}/code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ code }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update custom node code');
  }
  return response.json();
}

export async function validateMyCustomNode(customNodeId: number): Promise<NodeValidationResponse> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/library/${customNodeId}/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to validate custom node');
  }
  return response.json();
}

export async function registerMyCustomNode(customNodeId: number): Promise<RegisterCustomNodeResponse> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/library/${customNodeId}/register`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to register custom node');
  }
  return response.json();
}

export async function deleteMyCustomNode(customNodeId: number): Promise<DeleteCustomNodeResponse> {
  const response = await fetch(`${API_BASE}/api/v1/custom-nodes/library/${customNodeId}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete custom node');
  }
  return response.json();
}

/**
 * Get available AI providers
 */
export async function getAvailableProviders(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/ai/providers/available`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to fetch AI providers');
  }

  return response.json();
}

/**
 * Get models for a provider
 */
export async function getProviderModels(provider: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/ai/providers/${provider}/models`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to fetch provider models');
  }

  return response.json();
}


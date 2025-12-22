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
}

export interface StartConversationRequest {
  provider: string;
  model: string;
  temperature?: number;
  initial_message?: string;
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

export interface GenerateCodeResponse {
  success: boolean;
  code: string;
  node_type: string;
  class_name: string;
  validation_status: string;
  validation_errors?: string[];
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
  signal?: AbortSignal
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

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));

          switch (data.type) {
            case 'token':
              onToken(data.content);
              break;
            case 'done':
              onDone({
                ready_to_generate: data.ready_to_generate,
                requirements: data.requirements
              });
              break;
            case 'status':
              onStatus(data.message);
              break;
            case 'generation_complete':
              onGenerationComplete({
                success: data.success,
                node_type: data.node_type,
                error: data.error
              });
              break;
            case 'error':
              onError(data.message);
              break;
          }
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


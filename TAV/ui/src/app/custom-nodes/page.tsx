'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import 'highlight.js/styles/github-dark.css'; // Syntax highlighting theme

import {
  startConversation,
  sendMessage,
  sendMessageStream,
  getConversation,
  listConversations,
  deleteConversation,
  getAvailableProviders,
  getProviderModels,
  type Conversation,
  type Message,
} from '@/lib/custom-nodes';

export default function CustomNodesPage() {
  const router = useRouter();
  
  // State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  
  // AI Provider selection
  const [providers, setProviders] = useState<any[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('anthropic');
  const [selectedModel, setSelectedModel] = useState('claude-3-5-sonnet-20241022');
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  
  // UI state
  const [showSettings, setShowSettings] = useState(false);
  const [temperature, setTemperature] = useState(0.3);
  const [showCode, setShowCode] = useState(false);
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // Load conversations on mount
  useEffect(() => {
    loadConversations();
    loadProviders();
  }, []);
  
  // Auto-scroll to bottom only when sending new messages
  useEffect(() => {
    if (shouldAutoScrollRef.current && messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      shouldAutoScrollRef.current = false;
    }
  }, [messages]);
  
  // Load providers
  async function loadProviders() {
    try {
      const data = await getAvailableProviders();
      console.log('Loaded providers:', data);
      
      // Backend returns { providers: { openai: {...}, anthropic: {...} } }
      // Convert object to array
      let providersList: any[] = [];
      
      if (data.providers && typeof data.providers === 'object') {
        providersList = Object.values(data.providers);
      } else if (Array.isArray(data)) {
        providersList = data;
      } else if (Array.isArray(data.providers)) {
        providersList = data.providers;
      }
      
      console.log('Providers list:', providersList);
      setProviders(providersList);
      
      // Set default provider if we have any
      if (providersList.length > 0) {
        const defaultProvider = providersList[0].name;
        setSelectedProvider(defaultProvider);
        
        // Load models for default provider
        const modelsData = await getProviderModels(defaultProvider);
        console.log('Loaded models:', modelsData);
        
        let modelsList: any[] = [];
        if (Array.isArray(modelsData)) {
          modelsList = modelsData;
        } else if (Array.isArray(modelsData.models)) {
          modelsList = modelsData.models;
        }
        
        console.log('Models list:', modelsList);
        setAvailableModels(modelsList);
        
        // Set default model
        if (modelsList.length > 0) {
          setSelectedModel(modelsList[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
      // Set fallback defaults
      setProviders([{ name: 'anthropic', display_name: 'Anthropic' }]);
      setAvailableModels([{ id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet' }]);
      setSelectedProvider('anthropic');
      setSelectedModel('claude-3-5-sonnet-20241022');
    }
  }
  
  // Load conversations
  async function loadConversations() {
    try {
      const convos = await listConversations();
      setConversations(convos);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }

  // Delete conversation
  async function handleDeleteConversation(e: React.MouseEvent, conversationId: string) {
    e.stopPropagation(); // Prevent opening the conversation
    
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    
    try {
      await deleteConversation(conversationId);
      
      // If deleted active conversation, clear it
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
      
      await loadConversations();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      alert('Failed to delete conversation');
    }
  }
  
  // Load conversation details
  async function loadConversation(conversationId: string) {
    try {
      setIsLoading(true);
      const data = await getConversation(conversationId);
      setCurrentConversation(data.conversation);
      
      // Sort messages by created_at to ensure correct order (oldest first)
      const sortedMessages = (data.messages || []).sort((a: Message, b: Message) => {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      });
      
      setMessages(sortedMessages);
      
      // Don't auto-scroll when loading - let users see from the top
    } catch (error) {
      console.error('Failed to load conversation:', error);
      alert('Failed to load conversation');
    } finally {
      setIsLoading(false);
    }
  }
  
  // Cancel ongoing request
  function handleCancelRequest() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsSending(false);
      
      // Remove the partial/empty assistant message
      setMessages(prev => {
        // Find and remove the last assistant message if it's empty or very short
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content.length < 10) {
          return prev.slice(0, -1);
        }
        return prev;
      });
      
      console.log('🛑 Request cancelled by user');
    }
  }
  
  // Send message (auto-creates conversation if needed)
  async function handleSendMessage() {
    if (!inputMessage.trim()) return;
    
    const userMessage = inputMessage.trim();
    setInputMessage('');
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    
    try {
      setIsSending(true);
      
      // If no current conversation, create one with optimistic UI
      if (!currentConversation) {
        // 1. IMMEDIATELY show the chat UI (optimistic)
        const tempId = 'temp-' + Date.now();
        
        setCurrentConversation({
          id: tempId,
          title: 'New Conversation',
          status: 'active',
          provider: selectedProvider,
          model: selectedModel,
          temperature: temperature.toString(),
          requirements: null,
          generated_code: null,
          node_type: null,
          class_name: null,
          validation_status: null,
          validation_errors: null,
          message_count: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          completed_at: null
        });
        
        // 2. Show user message immediately
        const userMsg: Message = {
          id: Date.now(),
          role: 'user',
          content: userMessage,
          created_at: new Date().toISOString(),
        };
        
        // 3. Show assistant placeholder for streaming
        const assistantMessageId = Date.now() + 1;
        const assistantPlaceholder: Message = {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          created_at: new Date().toISOString(),
        };
        
        setMessages([userMsg, assistantPlaceholder]);
        shouldAutoScrollRef.current = true;
        
        // 4. Create conversation in background (don't block UI)
        startConversation({
          provider: selectedProvider,
          model: selectedModel,
          temperature: temperature,
          initial_message: userMessage,
        }).then(async (response) => {
          // Update with real conversation ID
          setCurrentConversation(prev => prev ? {
            ...prev,
            id: response.conversation_id,
            title: response.title
          } : null);
          
          // Stream the AI response into the placeholder
          abortControllerRef.current = new AbortController();
          
          // Get the initial AI response and stream it character by character for smooth effect
          const aiResponse = response.assistant_message;
          let charIndex = 0;
          
          const streamChars = () => {
            if (charIndex < aiResponse.length) {
              const chunk = aiResponse.slice(charIndex, Math.min(charIndex + 3, aiResponse.length));
              setMessages(prev => prev.map(msg => 
                msg.id === assistantMessageId 
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              ));
              charIndex += 3;
              shouldAutoScrollRef.current = true;
              setTimeout(streamChars, 10); // Smooth streaming effect
            } else {
              abortControllerRef.current = null;
              setIsSending(false);
            }
          };
          
          streamChars();
          
          // Reload conversations list
          await loadConversations();
        }).catch(error => {
          console.error('Failed to create conversation:', error);
          alert('Failed to start conversation: ' + error.message);
          setIsSending(false);
        });
        
        return;
      }
      
      // Add user message to UI immediately
      const tempUserMessage: Message = {
        id: Date.now(),
        role: 'user',
        content: userMessage,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, tempUserMessage]);
      
      // Enable auto-scroll for new messages
      shouldAutoScrollRef.current = true;
      
      // Create placeholder for assistant message that will stream in
      // Use a special temporary ID that we'll recognize
      const assistantMessageId = Date.now() + 1;
      const assistantPlaceholder: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantPlaceholder]);
      
      // Create abort controller for this request
      abortControllerRef.current = new AbortController();
      
      let messageComplete = false;
      
      // Use streaming API
      await sendMessageStream(
        currentConversation.id,
        { message: userMessage },
        // onToken: append each token to the message
        (token: string) => {
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, content: msg.content + token }
              : msg
          ));
          shouldAutoScrollRef.current = true;
        },
        // onDone: conversation response done
        (data) => {
          console.log('✨ Message done, ready_to_generate:', data.ready_to_generate);
          messageComplete = true;
        },
        // onStatus: generation status
        (statusMessage) => {
          console.log('📊 Status:', statusMessage);
        },
        // onGenerationComplete: code generation finished
        async (data) => {
          if (data.success) {
            console.log('✅ Code generated:', data.node_type);
            // Reload conversation to get the generated code
            const convId = currentConversation.id;
            await loadConversation(convId);
            // Auto-open code panel on completion
            setShowCode(true);
          } else {
            console.error('❌ Generation failed:', data.error);
            alert('Code generation failed: ' + data.error);
          }
        },
        // onError
        (error) => {
          console.error('❌ Stream error:', error);
          // If not complete and there's an error, remove the placeholder
          if (!messageComplete) {
            setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId));
          }
          alert('Failed to send message: ' + error);
        },
        // AbortSignal
        abortControllerRef.current.signal
      );
      
      // Clear abort controller after completion
      abortControllerRef.current = null;
      
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message: ' + (error as Error).message);
    } finally {
      setIsSending(false);
    }
  }
  
  // Handle provider change
  async function handleProviderChange(provider: string) {
    setSelectedProvider(provider);
    
    try {
      const modelsData = await getProviderModels(provider);
      console.log('Models for', provider, ':', modelsData);
      
      let modelsList: any[] = [];
      if (Array.isArray(modelsData)) {
        modelsList = modelsData;
      } else if (Array.isArray(modelsData.models)) {
        modelsList = modelsData.models;
      }
      
      console.log('Parsed models list:', modelsList);
      setAvailableModels(modelsList);
      
      // Auto-select first model
      if (modelsList.length > 0) {
        setSelectedModel(modelsList[0].id);
      }
    } catch (error) {
      console.error('Failed to load models:', error);
      // Fallback to a default model
      setAvailableModels([{ id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet' }]);
      setSelectedModel('claude-3-5-sonnet-20241022');
    }
  }
  
  return (
    <div className="flex overflow-hidden h-full" style={{ background: 'var(--theme-background)' }}>
      {/* Sidebar - Conversations List - Fixed height with internal scroll */}
      <div className="w-80 flex flex-col border-r flex-shrink-0" style={{ 
        background: 'var(--theme-card-bg)',
        borderColor: 'var(--theme-border)'
      }}>
        {/* Sticky header */}
        <div className="p-4 border-b flex-shrink-0" style={{ borderColor: 'var(--theme-border)' }}>
          <h1 className="text-xl font-bold mb-3 flex items-center gap-2" style={{ color: 'var(--theme-text)' }}>
            <i className="fa-solid fa-wand-magic-sparkles"></i>
            Custom Node Builder
          </h1>
          <button
            onClick={() => {
              setCurrentConversation(null);
              setMessages([]);
              setInputMessage('');
            }}
            className="w-full text-white px-4 py-2 rounded-lg transition-colors font-medium flex items-center justify-center gap-2"
            style={{ background: "var(--theme-button-primary)" }}
          >
            <i className="fa-solid fa-plus"></i>
            New Conversation
          </button>
        </div>
        
        {/* Scrollable conversation list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2" style={{ 
          overflowY: 'auto',
          minHeight: 0
        }}>
          {conversations.length === 0 ? (
            <p className="text-sm text-center mt-8" style={{ color: 'var(--theme-text-muted)' }}>
              No conversations yet.
              <br />
              Start a new one!
            </p>
          ) : (
            conversations.map((convo) => (
              <div
                key={convo.id}
                onClick={() => loadConversation(convo.id)}
                className={`w-full text-left p-3 rounded-lg transition-colors cursor-pointer group relative ${
                  currentConversation?.id === convo.id
                    ? 'border-2'
                    : 'border-2 border-transparent hover:opacity-100'
                }`}
                style={currentConversation?.id === convo.id ? {
                  background: 'var(--theme-card-selected)',
                  borderColor: 'var(--theme-border-primary)'
                } : {
                  background: 'var(--theme-card-bg-secondary)'
                }}
              >
                <div className="flex justify-between items-start gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate" style={{ color: 'var(--theme-text)' }}>{convo.title}</div>
                    <div className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                      {convo.message_count} messages • {convo.status}
                    </div>
                    <div className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                      {new Date(convo.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteConversation(e, convo.id)}
                    className="p-1.5 rounded-md hover:bg-red-500/10 text-gray-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                    title="Delete conversation"
                  >
                    <i className="fa-solid fa-trash text-sm"></i>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      
      {/* Main Chat Area - Fixed height with internal scroll */}
      <div className="flex-1 flex flex-col" style={{ minHeight: 0, minWidth: 0 }}>
        {currentConversation && (
          <div className="p-4 border-b flex-shrink-0" style={{ 
            background: 'var(--theme-card-bg)',
            borderColor: 'var(--theme-border)'
          }}>
            <h2 className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>{currentConversation.title}</h2>
            <p className="text-sm" style={{ color: 'var(--theme-text-muted)' }}>
              {currentConversation.provider} • {currentConversation.model}
            </p>
          </div>
        )}
        
        {/* Messages or Welcome */}
        {currentConversation ? (
          <>
            {/* Toggle button for code view */}
            {currentConversation.generated_code && (
              <div className="p-2 border-b flex justify-center" style={{
                background: 'var(--theme-card-bg-secondary)',
                borderColor: 'var(--theme-border)'
              }}>
                <button
                  onClick={() => setShowCode(!showCode)}
                  className="px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                  style={{
                    background: showCode ? 'var(--theme-button-primary)' : 'transparent',
                    color: showCode ? 'white' : 'var(--theme-text)',
                    border: showCode ? 'none' : `1px solid var(--theme-border)`
                  }}
                >
                  <i className={`fa-solid fa-${showCode ? 'message' : 'code'}`}></i>
                  {showCode ? 'Back to Chat' : 'View Generated Code'}
                </button>
              </div>
            )}
            
            {showCode && currentConversation.generated_code ? (
              /* Code View */
              <div className="flex-1 overflow-y-auto p-6" style={{
                background: 'var(--theme-background)',
                overflowY: 'auto',
                minHeight: 0
              }}>
                <div className="max-w-5xl mx-auto">
                  <div className="mb-4 flex justify-between items-center">
                    <div>
                      <h3 className="text-xl font-bold mb-1" style={{ color: 'var(--theme-text)' }}>
                        Generated Node: {currentConversation.node_type || 'Custom Node'}
                      </h3>
                      <div className="flex items-center gap-2 text-sm">
                        <span className={`px-2 py-0.5 rounded ${
                          currentConversation.validation_status === 'valid' ? 'bg-green-500/20 text-green-600' : 'bg-red-500/20 text-red-600'
                        }`}>
                          {currentConversation.validation_status === 'valid' ? '✓ Valid' : '✗ Invalid'}
                        </span>
                        {currentConversation.class_name && (
                          <span style={{ color: 'var(--theme-text-muted)' }}>
                            Class: {currentConversation.class_name}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(currentConversation.generated_code!);
                        alert('Code copied to clipboard!');
                      }}
                      className="px-3 py-1.5 rounded-md border transition-colors flex items-center gap-2"
                      style={{
                        background: 'var(--theme-card-bg)',
                        borderColor: 'var(--theme-border)',
                        color: 'var(--theme-text)'
                      }}
                    >
                      <i className="fa-solid fa-copy"></i>
                      Copy Code
                    </button>
                  </div>
                  <pre className="p-4 rounded-lg overflow-x-auto" style={{
                    background: 'var(--theme-card-bg)',
                    border: '1px solid var(--theme-border)',
                    color: 'var(--theme-text)'
                  }}>
                    <code>{currentConversation.generated_code}</code>
                  </pre>
                </div>
              </div>
            ) : (
            /* Messages - Scrollable area only */
            <div className="flex-1 overflow-y-auto" style={{ 
              overflowY: 'auto',
              minHeight: 0
            }}>
              <div className="max-w-3xl mx-auto w-full p-4 space-y-6">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className="flex gap-4 group"
                  >
                    {/* Avatar Column */}
                    <div className="flex-shrink-0 mt-1">
                      <div 
                        className="w-8 h-8 rounded-full flex items-center justify-center text-sm"
                        style={message.role === 'user' ? {
                          background: 'var(--theme-button-primary)',
                          color: 'white'
                        } : {
                          background: 'var(--theme-card-bg-secondary)',
                          color: 'var(--theme-text)',
                          border: '1px solid var(--theme-border)'
                        }}
                      >
                        {message.role === 'user' ? (
                          <i className="fa-solid fa-user"></i>
                        ) : (
                          <i className="fa-solid fa-robot"></i>
                        )}
                      </div>
                    </div>

                    {/* Content Column */}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold mb-1 opacity-90" style={{ color: 'var(--theme-text)' }}>
                        {message.role === 'user' ? 'You' : 'AI Assistant'}
                      </div>
                      <div 
                        className="text-base leading-relaxed markdown-body" 
                        style={{ color: 'var(--theme-text)' }}
                      >
                        {message.content ? (
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeHighlight]}
                            components={{
                              // Style code blocks
                              pre: ({node, ...props}) => (
                                <div className="relative my-4 rounded-lg overflow-hidden" style={{ background: '#1e1e1e', border: '1px solid var(--theme-border)' }}>
                                  <pre {...props} className="p-4 overflow-x-auto text-sm" />
                                </div>
                              ),
                              code: ({node, className, children, ...props}: any) => {
                                const match = /language-(\w+)/.exec(className || '')
                                const isInline = !match && !String(children).includes('\n')
                                
                                return isInline ? (
                                  <code className="px-1.5 py-0.5 rounded text-sm font-mono" style={{ background: 'var(--theme-card-bg-secondary)', color: 'var(--theme-button-primary)' }} {...props}>
                                    {children}
                                  </code>
                                ) : (
                                  <code className={className} {...props}>
                                    {children}
                                  </code>
                                )
                              },
                              // Style headings
                              h1: ({node, ...props}) => <h1 className="text-2xl font-bold mt-6 mb-4" {...props} />,
                              h2: ({node, ...props}) => <h2 className="text-xl font-bold mt-5 mb-3" {...props} />,
                              h3: ({node, ...props}) => <h3 className="text-lg font-bold mt-4 mb-2" {...props} />,
                              // Style lists
                              ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-4 space-y-1" {...props} />,
                              ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-4 space-y-1" {...props} />,
                              li: ({node, ...props}) => <li className="mb-1" {...props} />,
                              // Style paragraphs
                              p: ({node, ...props}) => <p className="mb-4 last:mb-0" {...props} />,
                              // Style links
                              a: ({node, ...props}) => <a className="underline hover:opacity-80 transition-colors" style={{ color: 'var(--theme-button-primary)' }} target="_blank" rel="noopener noreferrer" {...props} />,
                              // Style tables
                              table: ({node, ...props}) => <div className="overflow-x-auto my-4"><table className="min-w-full border-collapse text-sm" {...props} /></div>,
                              thead: ({node, ...props}) => <thead className="bg-gray-800/50" {...props} />,
                              th: ({node, ...props}) => <th className="border p-2 text-left font-semibold" style={{ borderColor: 'var(--theme-border)' }} {...props} />,
                              td: ({node, ...props}) => <td className="border p-2" style={{ borderColor: 'var(--theme-border)' }} {...props} />,
                              blockquote: ({node, ...props}) => <blockquote className="border-l-4 pl-4 italic my-4" style={{ borderColor: 'var(--theme-border-primary)', color: 'var(--theme-text-muted)' }} {...props} />,
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        ) : (message.role === 'assistant' && isSending ? (
                          <span className="flex items-center gap-2" style={{ color: 'var(--theme-text-muted)' }}>
                            <i className="fa-solid fa-spinner fa-spin"></i>
                            Thinking...
                          </span>
                        ) : null)}
                      </div>
                    </div>
                  </div>
                ))}
                
                <div ref={messagesEndRef} />
              </div>
            </div>
            )}
            
            {/* Input - Sticky at bottom */}
            <div className="flex-shrink-0" style={{ 
              background: 'var(--theme-card-bg)',
              borderTop: '1px solid var(--theme-border)'
            }}>
              <div className="max-w-3xl mx-auto w-full p-4">
                {/* Input Box with controls inside */}
                <div className="rounded-xl border-2 shadow-lg hover:border-opacity-80 focus-within:border-opacity-100 transition-colors" style={{
                  background: 'var(--theme-input-bg)',
                  borderColor: 'var(--theme-border-primary)'
                }}>
                  {/* Main input area */}
                  <textarea
                    ref={textareaRef}
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder="Type your message..."
                    disabled={isSending}
                    rows={1}
                    className="w-full px-4 pt-4 pb-2 focus:outline-none bg-transparent resize-none overflow-hidden"
                    style={{ 
                      color: 'var(--theme-text)',
                      minHeight: '48px',
                      maxHeight: '200px' 
                    }}
                    onInput={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      target.style.height = 'auto';
                      target.style.height = Math.min(target.scrollHeight, 200) + 'px';
                    }}
                    autoFocus
                  />
                  
                  {/* Bottom controls bar */}
                  <div className="flex items-center justify-between px-3 pb-3 pt-1 border-t" style={{ borderColor: 'var(--theme-border)' }}>
                    {/* Left side controls */}
                    <div className="flex items-center gap-2">
                      {/* Attachment button (placeholder) */}
                      <button
                        type="button"
                        className="p-2 hover:opacity-80 rounded-lg transition-colors"
                        style={{ color: 'var(--theme-text-muted)' }}
                        title="Add attachment (coming soon)"
                      >
                        <i className="fa-solid fa-plus text-sm"></i>
                      </button>
                      
                      {/* Settings dropdown */}
                      <div className="relative">
                        <button
                          type="button"
                          onClick={() => setShowSettings(!showSettings)}
                          className="p-2 hover:opacity-80 rounded-lg transition-colors"
                          style={{ color: 'var(--theme-text-muted)' }}
                          title="Settings"
                        >
                          <i className="fa-solid fa-sliders text-sm"></i>
                        </button>
                        
                        {showSettings && (
                          <div className="absolute bottom-full left-0 mb-2 border rounded-lg shadow-lg p-4 w-64 z-50" style={{
                            background: 'var(--theme-card-bg)',
                            borderColor: 'var(--theme-border)'
                          }}>
                            <div className="mb-3">
                              <label className="block text-xs font-medium mb-1" style={{ color: 'var(--theme-text)' }}>
                                Temperature: {temperature}
                              </label>
                              <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.1"
                                value={temperature}
                                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                                className="w-full accent-blue-600"
                                style={{
                                  accentColor: 'var(--theme-button-primary)'
                                }}
                              />
                              <div className="flex justify-between text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                                <span>Precise</span>
                                <span>Creative</span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Right side controls */}
                    <div className="flex items-center gap-2">
                      {/* Provider selector */}
                      <select
                        value={selectedProvider}
                        onChange={(e) => handleProviderChange(e.target.value)}
                        className="px-2 py-1 text-xs border rounded-md focus:outline-none focus:ring-1"
                        style={{
                          background: 'var(--theme-input-bg)',
                          borderColor: 'var(--theme-border-secondary)',
                          color: 'var(--theme-text)',
                          '--tw-ring-color': 'var(--theme-border-primary)'
                        } as any}
                      >
                        {Array.isArray(providers) && providers.length > 0 ? (
                          providers.map((provider) => (
                            <option key={provider.name} value={provider.name}>
                              {provider.display_name}
                            </option>
                          ))
                        ) : (
                          <option value="anthropic">Anthropic</option>
                        )}
                      </select>
                      
                      {/* Model selector */}
                      <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="px-2 py-1 text-xs border rounded-md focus:outline-none focus:ring-1"
                        style={{
                          background: 'var(--theme-input-bg)',
                          borderColor: 'var(--theme-border-secondary)',
                          color: 'var(--theme-text)',
                          '--tw-ring-color': 'var(--theme-border-primary)'
                        } as any}
                      >
                        {Array.isArray(availableModels) && availableModels.length > 0 ? (
                          availableModels.map((model) => (
                            <option key={model.id} value={model.id}>
                              {model.name || model.id}
                            </option>
                          ))
                        ) : (
                          <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                        )}
                      </select>
                      
                      {/* Send/Stop button */}
                      {isSending ? (
                        <button
                          onClick={handleCancelRequest}
                          className="text-white p-2 rounded-lg transition-colors flex items-center justify-center ml-1 bg-red-500 hover:bg-red-600"
                          title="Stop generating"
                        >
                          <i className="fa-solid fa-stop text-sm"></i>
                        </button>
                      ) : (
                        <button
                          onClick={handleSendMessage}
                          disabled={!inputMessage.trim()}
                          className="text-white p-2 rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center ml-1"
                          style={{ background: inputMessage.trim() ? "var(--theme-button-primary)" : undefined }}
                          title="Send message"
                        >
                          <i className="fa-solid fa-arrow-up text-sm"></i>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-xs text-center mt-2 opacity-60" style={{ color: 'var(--theme-text-muted)' }}>
                  AI can make mistakes. Please verify important information.
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-6" style={{ 
            overflowY: 'auto',
            minHeight: 0
          }}>
            {/* Centered Welcome Content */}
            <div className="text-center max-w-2xl mb-12">
              <div className="mb-6" style={{ color: 'var(--theme-text-accent)' }}>
                <i className="fa-solid fa-wand-magic-sparkles text-6xl"></i>
              </div>
              <h2 className="text-3xl font-bold mb-3" style={{ color: 'var(--theme-text)' }}>
                Build Your Custom Node
              </h2>
              <p className="mb-6" style={{ color: 'var(--theme-text-muted)' }}>
                Describe what you want your node to do, and I'll help you design and generate it.
              </p>
              <div className="border rounded-lg p-4 text-left" style={{
                background: 'var(--theme-card-bg)',
                borderColor: 'var(--theme-border-secondary)'
              }}>
                <p className="text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>Example prompts:</p>
                <ul className="text-sm space-y-1" style={{ color: 'var(--theme-text-muted)' }}>
                  <li>• "Create a node that fetches weather data from OpenWeatherMap"</li>
                  <li>• "I need a node to parse CSV files and extract columns"</li>
                  <li>• "Build a node that sends Slack notifications"</li>
                </ul>
              </div>
            </div>
            
            {/* Centered Input Area */}
            <div className="w-full max-w-3xl">
              {/* Input Box with controls inside */}
              <div className="rounded-xl border-2 shadow-lg hover:border-opacity-80 focus-within:border-opacity-100 transition-colors" style={{
                background: 'var(--theme-input-bg)',
                borderColor: 'var(--theme-border-primary)'
              }}>
                {/* Main input area */}
                <textarea
                  ref={textareaRef}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder="Describe your custom node idea..."
                  disabled={isSending}
                  rows={3}
                  className="w-full px-4 pt-4 pb-2 focus:outline-none bg-transparent resize-none"
                  style={{ color: 'var(--theme-text)' }}
                  autoFocus
                />
                
                {/* Bottom controls bar */}
                <div className="flex items-center justify-between px-3 pb-3 pt-1 border-t" style={{ borderColor: 'var(--theme-border)' }}>
                  {/* Left side controls */}
                  <div className="flex items-center gap-2">
                    {/* Attachment button (placeholder) */}
                    <button
                      type="button"
                      className="p-2 hover:opacity-80 rounded-lg transition-colors"
                      style={{ color: 'var(--theme-text-muted)' }}
                      title="Add attachment (coming soon)"
                    >
                      <i className="fa-solid fa-plus text-sm"></i>
                    </button>
                    
                    {/* Settings dropdown */}
                    <div className="relative">
                      <button
                        type="button"
                        onClick={() => setShowSettings(!showSettings)}
                        className="p-2 hover:opacity-80 rounded-lg transition-colors"
                        style={{ color: 'var(--theme-text-muted)' }}
                        title="Settings"
                      >
                        <i className="fa-solid fa-sliders text-sm"></i>
                      </button>
                      
                      {showSettings && (
                        <div className="absolute bottom-full left-0 mb-2 border rounded-lg shadow-lg p-4 w-64 z-50" style={{
                          background: 'var(--theme-card-bg)',
                          borderColor: 'var(--theme-border)'
                        }}>
                          <div className="mb-3">
                            <label className="block text-xs font-medium mb-1" style={{ color: 'var(--theme-text)' }}>
                              Temperature: {temperature}
                            </label>
                            <input
                              type="range"
                              min="0"
                              max="1"
                              step="0.1"
                              value={temperature}
                              onChange={(e) => setTemperature(parseFloat(e.target.value))}
                              className="w-full"
                            />
                            <div className="flex justify-between text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>
                              <span>Precise</span>
                              <span>Creative</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Right side controls */}
                  <div className="flex items-center gap-2">
                    {/* Provider selector */}
                    <select
                      value={selectedProvider}
                      onChange={(e) => handleProviderChange(e.target.value)}
                      className="px-2 py-1 text-xs border rounded-md focus:outline-none focus:ring-1"
                      style={{
                        background: 'var(--theme-input-bg)',
                        borderColor: 'var(--theme-border-secondary)',
                        color: 'var(--theme-text)',
                        '--tw-ring-color': 'var(--theme-border-primary)'
                      } as any}
                    >
                      {Array.isArray(providers) && providers.length > 0 ? (
                        providers.map((provider) => (
                          <option key={provider.name} value={provider.name}>
                            {provider.display_name}
                          </option>
                        ))
                      ) : (
                        <option value="anthropic">Anthropic</option>
                      )}
                    </select>
                    
                    {/* Model selector */}
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="px-2 py-1 text-xs border rounded-md focus:outline-none focus:ring-1"
                      style={{
                        background: 'var(--theme-input-bg)',
                        borderColor: 'var(--theme-border-secondary)',
                        color: 'var(--theme-text)',
                        '--tw-ring-color': 'var(--theme-border-primary)'
                      } as any}
                    >
                      {Array.isArray(availableModels) && availableModels.length > 0 ? (
                        availableModels.map((model) => (
                          <option key={model.id} value={model.id}>
                            {model.name || model.id}
                          </option>
                        ))
                      ) : (
                        <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                      )}
                    </select>
                    
                    {/* Send/Stop button */}
                    {isSending ? (
                      <button
                        onClick={handleCancelRequest}
                        className="text-white p-2 rounded-lg transition-colors flex items-center justify-center ml-1 bg-red-500 hover:bg-red-600"
                        title="Stop generating"
                      >
                        <i className="fa-solid fa-stop text-sm"></i>
                      </button>
                    ) : (
                      <button
                        onClick={handleSendMessage}
                        disabled={!inputMessage.trim()}
                        className="text-white p-2 rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center ml-1"
                        style={{ background: inputMessage.trim() ? "var(--theme-button-primary)" : undefined }}
                        title="Send message"
                      >
                        <i className="fa-solid fa-arrow-up text-sm"></i>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


'use client';

import { useState, useEffect, useRef, useMemo, memo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import 'highlight.js/styles/github-dark.css'; // Syntax highlighting theme

import {
  startConversation,
  sendMessage,
  sendMessageStream,
  startConversationStream,
  getConversation,
  listConversations,
  deleteConversation,
  getAvailableProviders,
  getProviderModels,
  validateNodeCode,
  saveCustomNode,
  updateConversationCode,
  type NodeValidationResponse,
  type Conversation,
  type Message,
  type AttachmentRef,
} from '@/lib/custom-nodes';
import { createWorkflow } from '@/lib/editor';
import { uploadFile, formatFileSize, getFileDownloadUrl, type FileMetadata, type FileCategory } from '@/lib/files';

type TraceItem =
  | { kind: 'status'; at: string; message: string }
  | { kind: 'tool_start'; at: string; tool: any }
  | { kind: 'tool_end'; at: string; tool: any }
  | { kind: 'event'; at: string; event: any };

type MessageWithActivity = Omit<Message, 'activity'> & { activity?: TraceItem[] };

type PendingAttachment = {
  localId: string;
  file: File;
  status: 'uploading' | 'ready' | 'error';
  progress: number; // 0-100
  meta?: FileMetadata;
  error?: string;
};

const MessagesPanel = memo(function MessagesPanel({
  messages,
  isSending,
  activityExpanded,
  setActivityExpanded,
  workflowDraftByMessageId,
  onCreateWorkflowDraft,
  creatingWorkflowFor,
  onCopyWorkflowDraft,
  markdownComponents,
  messagesEndRef,
  onActivityClick,
  containerRef,
}: {
  messages: MessageWithActivity[];
  isSending: boolean;
  activityExpanded: Record<number, boolean>;
  setActivityExpanded: React.Dispatch<React.SetStateAction<Record<number, boolean>>>;
  workflowDraftByMessageId: Record<number, any>;
  onCreateWorkflowDraft: (messageId: number) => void;
  creatingWorkflowFor: number | null;
  onCopyWorkflowDraft: (messageId: number) => void;
  markdownComponents: any;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  onActivityClick: (item: TraceItem) => void;
  containerRef: React.RefObject<HTMLDivElement | null>;
}) {
  function getAttachmentIcon(mimeType?: string, category?: string) {
    const m = (mimeType || '').toLowerCase();
    const c = (category || '').toLowerCase();
    if (m.startsWith('image/') || c === 'image') return 'fa-file-image';
    if (m.startsWith('audio/') || c === 'audio') return 'fa-file-audio';
    if (m.startsWith('video/') || c === 'video') return 'fa-file-video';
    if (m === 'application/pdf') return 'fa-file-pdf';
    if (m.includes('word') || m.includes('officedocument.wordprocessingml') || c === 'document') return 'fa-file-lines';
    return 'fa-paperclip';
  }

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto" style={{ overflowY: 'auto', minHeight: 0 }}>
      <div className="max-w-3xl mx-auto w-full p-4 space-y-6">
        {messages.map((message) => (
          <div key={message.id} className="flex gap-4 group">
            {/* Avatar Column */}
            <div className="flex-shrink-0 mt-1">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-sm"
                style={
                  message.role === 'user'
                    ? { background: 'var(--theme-button-primary)', color: 'white' }
                    : {
                        background: 'var(--theme-card-bg-secondary)',
                        color: 'var(--theme-text)',
                        border: '1px solid var(--theme-border)',
                      }
                }
              >
                {message.role === 'user' ? <i className="fa-solid fa-user"></i> : <i className="fa-solid fa-robot"></i>}
              </div>
            </div>

            {/* Content Column */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2 text-sm font-semibold mb-1 opacity-90" style={{ color: 'var(--theme-text)' }}>
                <span>{message.role === 'user' ? 'You' : 'AI Assistant'}</span>
                {message.role === 'assistant' && message.activity?.length ? (
                  <button
                    type="button"
                    className="text-xs px-2 py-1 rounded-md border"
                    style={{
                      borderColor: 'var(--theme-border)',
                      background: 'var(--theme-card-bg-secondary)',
                      color: 'var(--theme-text-muted)',
                    }}
                    onClick={() => setActivityExpanded((prev) => ({ ...prev, [message.id]: !prev[message.id] }))}
                    title="Toggle activity"
                  >
                    Activity ({message.activity.length}) {!activityExpanded[message.id] ? '▸' : '▾'}
                  </button>
                ) : null}
              </div>

              {/* Expandable activity / breadcrumbs (status + tool events) */}
              {message.role === 'assistant' && message.activity?.length && activityExpanded[message.id] ? (
                <div
                  className="mt-2 rounded-md border p-2 text-xs space-y-1"
                  style={{
                    borderColor: 'var(--theme-border)',
                    background: 'var(--theme-card-bg)',
                    color: 'var(--theme-text-muted)',
                  }}
                >
                  {message.activity.map((a, idx) => {
                    const label =
                      a.kind === 'status'
                        ? a.message
                        : a.kind === 'tool_start'
                          ? `tool_start: ${a.tool?.name ?? ''}`
                          : a.kind === 'tool_end'
                            ? `tool_end: ${a.tool?.name ?? ''}`
                            : a.event?.type
                              ? `event: ${a.event.type}`
                              : 'event';
                    const clickable = a.kind !== 'status';
                    return (
                      <div key={idx} className="flex gap-2 items-start">
                        <span style={{ opacity: 0.7, minWidth: 70 }}>{new Date(a.at).toLocaleTimeString()}</span>
                        {clickable ? (
                          <button
                            type="button"
                            className="underline hover:opacity-80 text-left"
                            style={{ color: 'var(--theme-text-muted)' }}
                            onClick={() => onActivityClick(a)}
                          >
                            {label}
                          </button>
                        ) : (
                          <span>{label}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : null}

              {/* Workflow draft actions (only present when backend emits workflow_draft) */}
              {message.role === 'assistant' && workflowDraftByMessageId[message.id] ? (
                <div
                  className="mt-2 rounded-md border p-2 text-xs flex items-center justify-between gap-2"
                  style={{
                    borderColor: 'var(--theme-border)',
                    background: 'var(--theme-card-bg)',
                    color: 'var(--theme-text-muted)',
                  }}
                >
                  <div className="min-w-0 truncate">
                    <span className="font-semibold" style={{ color: 'var(--theme-text)' }}>
                      Workflow draft ready
                    </span>
                    <span style={{ opacity: 0.7 }}> (create it in the editor)</span>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      type="button"
                      className="text-xs px-2 py-1 rounded-md border cursor-pointer hover:opacity-90 transition-opacity"
                      style={{
                        borderColor: 'var(--theme-border)',
                        background: 'var(--theme-card-bg-secondary)',
                        color: 'var(--theme-text)',
                      }}
                      onClick={() => onCopyWorkflowDraft(message.id)}
                      title="Copy workflow JSON"
                    >
                      Copy JSON
                    </button>
                    <button
                      type="button"
                      disabled={creatingWorkflowFor === message.id}
                      className="text-xs px-2 py-1 rounded-md border cursor-pointer hover:opacity-90 transition-opacity disabled:opacity-60"
                      style={{
                        borderColor: 'var(--theme-border)',
                        background: 'var(--theme-button-primary)',
                        color: 'white',
                      }}
                      onClick={() => onCreateWorkflowDraft(message.id)}
                      title="Create workflow draft in DB and open editor"
                    >
                      {creatingWorkflowFor === message.id ? 'Creating…' : 'Create Draft'}
                    </button>
                  </div>
                </div>
              ) : null}

              <div className="text-base leading-relaxed markdown-body" style={{ color: 'var(--theme-text)' }}>
                {message.role === 'user' && Array.isArray((message as any).activity?.attachments) && (message as any).activity.attachments.length > 0 ? (
                  <div className="mb-3 flex flex-wrap gap-2">
                    {(message as any).activity.attachments.map((a: any, idx: number) => {
                      const fileId = a?.file_id;
                      const filename = a?.filename || fileId || `attachment-${idx + 1}`;
                      const mime = a?.mime_type;
                      const category = a?.file_category;
                      const size = typeof a?.file_size_bytes === 'number' ? a.file_size_bytes : undefined;
                      const href = fileId ? getFileDownloadUrl(String(fileId)) : null;

                      return (
                        <div
                          key={`${fileId || filename}-${idx}`}
                          className="text-xs border rounded-lg px-2 py-1 flex items-center gap-2 max-w-full"
                          style={{ borderColor: 'var(--theme-border)', background: 'var(--theme-card-bg-secondary)', color: 'var(--theme-text)' }}
                          title={filename}
                        >
                          <i className={`fa-solid ${getAttachmentIcon(mime, category)}`} style={{ opacity: 0.85 }} />
                          <span className="truncate max-w-[240px]">{filename}</span>
                          {size != null ? <span style={{ color: 'var(--theme-text-muted)' }}>{formatFileSize(size)}</span> : null}
                          {href ? (
                            <a
                              className="ml-1 underline hover:opacity-80"
                              style={{ color: 'var(--theme-text-muted)' }}
                              href={href}
                              target="_blank"
                              rel="noopener noreferrer"
                              title="Download"
                            >
                              download
                            </a>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                ) : null}

                {message.content ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                    components={markdownComponents as any}
                  >
                    {message.content}
                  </ReactMarkdown>
                ) : message.role === 'assistant' && isSending ? (
                  <span className="flex items-center gap-2" style={{ color: 'var(--theme-text-muted)' }}>
                    <i className="fa-solid fa-spinner fa-spin"></i>
                    Thinking...
                  </span>
                ) : null}
              </div>
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
});

export default function CustomNodesPage() {
  const router = useRouter();
  
  // State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [activityExpanded, setActivityExpanded] = useState<Record<number, boolean>>({});
  const [traceModalOpen, setTraceModalOpen] = useState(false);
  const [selectedTrace, setSelectedTrace] = useState<TraceItem | null>(null);
  const [workflowDraftByMessageId, setWorkflowDraftByMessageId] = useState<Record<number, any>>({});
  const [creatingWorkflowFor, setCreatingWorkflowFor] = useState<number | null>(null);
  const [showWorkflow, setShowWorkflow] = useState(false);
  const [workflowDraftText, setWorkflowDraftText] = useState('');
  const [isEditingWorkflow, setIsEditingWorkflow] = useState(false);
  const [editedWorkflowText, setEditedWorkflowText] = useState('');
  
  // AI Provider selection
  const [providers, setProviders] = useState<any[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('anthropic');
  const [selectedModel, setSelectedModel] = useState('claude-3-5-sonnet-20241022');
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  
  // UI state
  const [showSettings, setShowSettings] = useState(false);
  const [temperature, setTemperature] = useState(0.3);
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [showValidationDetails, setShowValidationDetails] = useState(false);
  const [isEditingCode, setIsEditingCode] = useState(false);
  const [editedCode, setEditedCode] = useState('');
  const [codeValidation, setCodeValidation] = useState<NodeValidationResponse | null>(null);
  const [isValidatingCode, setIsValidatingCode] = useState(false);
  const [isSavingCode, setIsSavingCode] = useState(false);

  // Attachments
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  
  // Refs
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollRafRef = useRef<number | null>(null);
  const shouldAutoScrollRef = useRef(false);
  const autoScrollEnabledRef = useRef(true);
  const [loadedCount, setLoadedCount] = useState(8);
  const loadingOlderRef = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const attachMenuRef = useRef<HTMLDivElement | null>(null);
  const dragDepthRef = useRef(0);

  const markdownComponents = useMemo(() => {
    return {
      // Style code blocks
      pre: ({ node, ...props }: any) => (
        <div
          className="relative my-4 rounded-lg overflow-hidden"
          style={{ background: '#1e1e1e', border: '1px solid var(--theme-border)' }}
        >
          <pre {...props} className="p-4 overflow-x-auto text-sm" />
        </div>
      ),
      code: ({ node, className, children, ...props }: any) => {
        const match = /language-(\w+)/.exec(className || '');
        const isInline = !match && !String(children).includes('\n');

      return isInline ? (
        <code
          className="px-1.5 py-0.5 rounded text-sm font-mono"
          style={{
            background: 'var(--theme-card-bg-secondary)',
            color: 'var(--theme-button-primary)',
          }}
          {...props}
        >
          {children}
        </code>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
    // Style headings
    h1: ({ node, ...props }: any) => <h1 className="text-2xl font-bold mt-6 mb-4" {...props} />,
    h2: ({ node, ...props }: any) => <h2 className="text-xl font-bold mt-5 mb-3" {...props} />,
    h3: ({ node, ...props }: any) => <h3 className="text-lg font-bold mt-4 mb-2" {...props} />,
    // Style lists
    ul: ({ node, ...props }: any) => <ul className="list-disc pl-5 mb-4 space-y-1" {...props} />,
    ol: ({ node, ...props }: any) => <ol className="list-decimal pl-5 mb-4 space-y-1" {...props} />,
    li: ({ node, ...props }: any) => <li className="mb-1" {...props} />,
    // Style paragraphs
    p: ({ node, ...props }: any) => <p className="mb-4 last:mb-0" {...props} />,
    // Style links
    a: ({ node, ...props }: any) => (
      <a
        className="underline hover:opacity-80 transition-colors"
        style={{ color: 'var(--theme-button-primary)' }}
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      />
    ),
    // Style tables
    table: ({ node, ...props }: any) => (
      <div className="overflow-x-auto my-4">
        <table className="min-w-full border-collapse text-sm" {...props} />
      </div>
    ),
    thead: ({ node, ...props }: any) => <thead className="bg-gray-800/50" {...props} />,
    th: ({ node, ...props }: any) => (
      <th className="border p-2 text-left font-semibold" style={{ borderColor: 'var(--theme-border)' }} {...props} />
    ),
    td: ({ node, ...props }: any) => (
      <td className="border p-2" style={{ borderColor: 'var(--theme-border)' }} {...props} />
    ),
    blockquote: ({ node, ...props }: any) => (
      <blockquote
        className="border-l-4 pl-4 italic my-4"
        style={{ borderColor: 'var(--theme-border-primary)', color: 'var(--theme-text-muted)' }}
        {...props}
      />
    ),
    };
  }, []);

  const isUploadingAttachments = attachments.some((a) => a.status === 'uploading');
  const hasAttachmentError = attachments.some((a) => a.status === 'error');

  function inferFileCategory(file: File): FileCategory | undefined {
    const t = (file.type || '').toLowerCase();
    if (t.startsWith('image/')) return 'image';
    if (t.startsWith('audio/')) return 'audio';
    if (t.startsWith('video/')) return 'video';
    if (t.startsWith('text/')) return 'document';
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    if (['pdf', 'docx', 'doc', 'txt', 'md', 'csv', 'json', 'xlsx', 'xls', 'xlsm', 'pptx', 'ppt'].includes(ext)) return 'document';
    return 'other';
  }

  async function addAndUploadFiles(files: File[]) {
    if (!files.length) return;
    // Hard guardrail
    const remaining = Math.max(0, 5 - attachments.length);
    const next = files.slice(0, remaining);
    if (!next.length) {
      alert('Max 5 attachments per message.');
      return;
    }

    // Add placeholders immediately
    const locals: PendingAttachment[] = next.map((f) => ({
      localId: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
      file: f,
      status: 'uploading',
      progress: 0,
    }));
    setAttachments((prev) => [...prev, ...locals]);

    await Promise.all(
      locals.map(async (att) => {
        try {
          const category = inferFileCategory(att.file);
          const meta = await uploadFile({
            file: att.file,
            fileType: 'upload',
            fileCategory: category,
            onProgress: (p) => {
              setAttachments((prev) =>
                prev.map((x) => (x.localId === att.localId ? { ...x, progress: Math.max(0, Math.min(100, p)) } : x))
              );
            },
          });
          setAttachments((prev) => prev.map((x) => (x.localId === att.localId ? { ...x, status: 'ready', meta, progress: 100 } : x)));
        } catch (e) {
          const msg = e instanceof Error ? e.message : 'Upload failed';
          setAttachments((prev) => prev.map((x) => (x.localId === att.localId ? { ...x, status: 'error', error: msg } : x)));
        }
      })
    );
  }

  function buildAttachmentRefs(): AttachmentRef[] {
    return attachments
      .filter((a) => a.status === 'ready' && a.meta)
      .map((a) => ({
        file_id: a.meta!.id,
        filename: a.meta!.filename,
        mime_type: a.meta!.mime_type,
        file_category: a.meta!.file_category,
        file_size_bytes: a.meta!.file_size_bytes,
      }));
  }

  function removeAttachment(localId: string) {
    setAttachments((prev) => prev.filter((a) => a.localId !== localId));
  }

  // Close the attach menu when clicking outside
  useEffect(() => {
    function onDocMouseDown(e: MouseEvent) {
      const el = attachMenuRef.current;
      if (!el) return;
      if (showAttachMenu && !el.contains(e.target as Node)) {
        setShowAttachMenu(false);
      }
    }
    document.addEventListener('mousedown', onDocMouseDown);
    return () => document.removeEventListener('mousedown', onDocMouseDown);
  }, [showAttachMenu]);

  function getValidationErrorsList(): string[] {
    const raw: any = currentConversation?.validation_errors;
    if (!raw) return [];
    if (Array.isArray(raw)) {
      return raw
        .map((e) => {
          if (typeof e === 'string') return e;
          if (e && typeof e === 'object') return e.message || e.detail || JSON.stringify(e);
          return String(e);
        })
        .filter(Boolean);
    }
    if (typeof raw === 'string') return [raw];
    return [JSON.stringify(raw)];
  }

  const codeIsDirty =
    isEditingCode &&
    !!currentConversation?.generated_code &&
    editedCode !== (currentConversation?.generated_code ?? '');

  async function handleValidateEditedCode() {
    if (!isEditingCode) return;
    setIsValidatingCode(true);
    try {
      const result = await validateNodeCode(editedCode);
      setCodeValidation(result);

      // Also reflect status/errors on the conversation so the badge + modal make sense immediately.
      if (currentConversation) {
        setCurrentConversation({
          ...currentConversation,
          validation_status: result.valid ? 'valid' : 'invalid',
          validation_errors: (result.errors || []).map((e) => e.message),
          node_type: result.node_type || currentConversation.node_type,
          class_name: result.class_name || currentConversation.class_name,
        });
      }

      if (!result.valid) {
        setShowValidationDetails(true);
      } else {
        alert('✅ Code is valid');
      }
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to validate code');
    } finally {
      setIsValidatingCode(false);
    }
  }

  async function handleSaveEditedCode() {
    if (!currentConversation) return;
    if (!isEditingCode) return;

    setIsSavingCode(true);
    try {
      // Save edits onto the conversation only (no register). Backend validates and updates status/errors.
      const res = await updateConversationCode(currentConversation.id, editedCode);
      setCurrentConversation(res.conversation);
      setCodeValidation(null);

      setIsEditingCode(false);
      alert('✅ Code saved to conversation. Use Register when you’re ready to add it to the system.');
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to save node');
    } finally {
      setIsSavingCode(false);
    }
  }

  async function handleRegisterNode() {
    if (!currentConversation) return;

    if (isEditingCode && codeIsDirty) {
      alert('You have unsaved code edits. Please Save changes before registering.');
      return;
    }

    if (currentConversation.validation_status !== 'valid') {
      setShowValidationDetails(true);
      alert('Code must be valid before registering.');
      return;
    }

    setIsSavingCode(true);
    try {
      const res = await saveCustomNode({
        conversation_id: currentConversation.id,
        overwrite: false,
      });
      alert(`${res.message}${res.registered ? ' (Registered ✅)' : ' (Saved, but reload failed ⚠️)'}`);

      // Refresh conversation from backend (status, saved node id, etc.)
      const refreshed = await getConversation(currentConversation.id);
      setCurrentConversation(refreshed.conversation);
      setMessages(refreshed.messages || []);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.toLowerCase().includes('already exists') || msg.toLowerCase().includes('409')) {
        const ok = confirm('A node with this node_type already exists. Overwrite it?');
        if (!ok) return;
        const res = await saveCustomNode({
          conversation_id: currentConversation.id,
          overwrite: true,
        });
        alert(`${res.message}${res.registered ? ' (Registered ✅)' : ' (Saved, but reload failed ⚠️)'}`);
      } else {
        throw err;
      }
    } finally {
      setIsSavingCode(false);
    }
  }
  
  // Load conversations on mount
  useEffect(() => {
    loadConversations();
    loadProviders();
  }, []);

  // When switching conversations, reset windowing + workflow preview state
  useEffect(() => {
    setLoadedCount(8);
    setShowWorkflow(false);
    setIsEditingWorkflow(false);
    setEditedWorkflowText('');
  }, [currentConversation?.id]);
  
  function scrollToBottom() {
    if (scrollRafRef.current) {
      cancelAnimationFrame(scrollRafRef.current);
    }
    scrollRafRef.current = requestAnimationFrame(() => {
      const el = messagesContainerRef.current;
      if (!el) return;
      el.scrollTo({ top: el.scrollHeight, behavior: 'auto' });
    });
  }

  function isNearBottom(el: HTMLDivElement, thresholdPx = 24) {
    const distance = el.scrollHeight - (el.scrollTop + el.clientHeight);
    return distance <= thresholdPx;
  }

  // Stop auto-scroll when user scrolls up; resume when they scroll back to bottom.
  useEffect(() => {
    const el = messagesContainerRef.current;
    if (!el) return;

    const onScroll = () => {
      autoScrollEnabledRef.current = isNearBottom(el);
      // Lazy-load older messages when scrolling near top
      if (el.scrollTop < 40 && !loadingOlderRef.current) {
        const hasMore = messages.length > loadedCount;
        if (hasMore) {
          loadingOlderRef.current = true;
          const before = el.scrollHeight;
          setLoadedCount((prev) => Math.min(messages.length, prev + 20));
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              const after = el.scrollHeight;
              el.scrollTop = el.scrollTop + (after - before);
              loadingOlderRef.current = false;
            });
          });
        }
      }
    };

    el.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => el.removeEventListener('scroll', onScroll);
  }, [currentConversation?.id, messages.length, loadedCount]);

  // Auto-scroll to bottom only when we are "sticky" to bottom
  useEffect(() => {
    if (shouldAutoScrollRef.current && messages.length > 0 && autoScrollEnabledRef.current) {
      scrollToBottom();
      shouldAutoScrollRef.current = false;
    }
  }, [messages]);

  const visibleMessages = useMemo(() => {
    const start = Math.max(0, messages.length - loadedCount);
    return messages.slice(start);
  }, [messages, loadedCount]);
  
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
      // Clear workflow draft UI state while we load the conversation (prevents showing stale draft from another chat)
      setWorkflowDraftByMessageId({});
      setWorkflowDraftText('');
      const data = await getConversation(conversationId);
      setCurrentConversation(data.conversation);
      
      // Sort messages by created_at to ensure correct order (oldest first)
      const sortedMessages = (data.messages || []).sort((a: Message, b: Message) => {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      });
      
      setMessages(sortedMessages);

      // Rehydrate workflow drafts from persisted message activity
      try {
        const draftById: Record<number, any> = {};
        let latestDraftText = '';
        for (const m of sortedMessages as any[]) {
          if (!m || m.role !== 'assistant') continue;
          const activity = m.activity;
          if (!Array.isArray(activity)) continue;
          for (const a of activity) {
            if (a?.kind === 'event' && a?.event?.type === 'workflow_draft' && a?.event?.workflow) {
              draftById[m.id] = a.event.workflow;
              latestDraftText = JSON.stringify(a.event.workflow, null, 2);
            }
          }
        }
        setWorkflowDraftByMessageId(draftById);
        setWorkflowDraftText(latestDraftText);
      } catch {
        // ignore rehydrate errors; chat should still load
      }

      // When opening a conversation, start at the latest message (bottom)
      autoScrollEnabledRef.current = true;
      shouldAutoScrollRef.current = true;
      // Ensure DOM is updated before scrolling
      requestAnimationFrame(() => scrollToBottom());
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
    if (isUploadingAttachments) {
      alert('Please wait for attachments to finish uploading.');
      return;
    }
    if (hasAttachmentError) {
      alert('Please remove failed attachments before sending.');
      return;
    }
    
    const userMessage = inputMessage.trim();
    setInputMessage('');
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    
    try {
      setIsSending(true);
      const attachmentRefs = buildAttachmentRefs();
      
      // If no current conversation, create one with optimistic UI
      if (!currentConversation) {
        // 1) Optimistic UI: show user message + assistant placeholder
        const userMsg: Message = {
          id: Date.now(),
          role: 'user',
          content: userMessage,
          created_at: new Date().toISOString(),
          activity: attachmentRefs.length ? { attachments: attachmentRefs } : undefined,
        };
        
        const assistantMessageId = Date.now() + 1;
        const assistantPlaceholder: Message = {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          created_at: new Date().toISOString(),
        };
        
        setMessages([userMsg, assistantPlaceholder]);
        shouldAutoScrollRef.current = true;

        // 2) Use real SSE start-stream endpoint so Activity + tool traces show up on the first message too
        abortControllerRef.current = new AbortController();
        let realConversationId: string | null = null;
        let messageComplete = false;

        const appendTrace = (item: TraceItem) => {
          setMessages((prev) =>
            prev.map((msg: any) => (msg.id === assistantMessageId ? { ...msg, activity: [...(msg.activity || []), item] } : msg))
          );
        };

        await startConversationStream(
          {
            provider: selectedProvider,
            model: selectedModel,
            temperature,
            message: userMessage,
            attachments: attachmentRefs.length ? attachmentRefs : undefined,
          },
          (token: string) => {
            setMessages((prev) =>
              prev.map((msg) => (msg.id === assistantMessageId ? { ...msg, content: msg.content + token } : msg))
            );
            shouldAutoScrollRef.current = true;
          },
          async () => {
            messageComplete = true;
            setIsSending(false);
            try {
              abortControllerRef.current?.abort();
            } catch {
              // ignore
            }
            abortControllerRef.current = null;

            if (realConversationId) {
              await loadConversation(realConversationId);
              await loadConversations();
            }
          },
          (statusMessage) => {
            setActivityExpanded((prev) => ({ ...prev, [assistantMessageId]: true }));
            appendTrace({ kind: 'status', message: statusMessage, at: new Date().toISOString() });
          },
          async (data) => {
            if (!data || typeof data !== 'object') {
              console.error('❌ generation_complete malformed:', data);
              alert('Code generation failed (malformed response)');
              return;
            }
            if ((data as any).success) {
              if (realConversationId) {
                await loadConversation(realConversationId);
                setShowCode(true);
              }
            } else {
              const err = (data as any).error || 'Unknown error';
              console.error('❌ Generation failed:', err);
              alert('Code generation failed: ' + err);
            }
          },
          (error) => {
            console.error('❌ Stream error:', error);
            if (!messageComplete) {
              setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
            }
            alert('Failed to start conversation: ' + error);
          },
          abortControllerRef.current.signal,
          (evt: any) => {
            if (evt?.type === 'conversation_started') {
              realConversationId = evt.conversation_id;
              setCurrentConversation({
                id: evt.conversation_id,
                title: evt.title || 'New Conversation',
                status: 'active',
                provider: evt.provider || selectedProvider,
                model: evt.model || selectedModel,
                temperature: (evt.temperature ?? temperature).toString(),
                requirements: null,
                generated_code: null,
                node_type: null,
                class_name: null,
                validation_status: null,
                validation_errors: null,
                message_count: 2,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                completed_at: null,
              });
              return;
            }

            if (evt?.type === 'workflow_draft') {
              setWorkflowDraftByMessageId((prev) => ({ ...prev, [assistantMessageId]: evt.workflow }));
              try {
                const text = JSON.stringify(evt.workflow, null, 2);
                setWorkflowDraftText(text);
                setEditedWorkflowText(text);
                setShowWorkflow(true);
                setShowCode(false);
                setIsEditingWorkflow(false);
              } catch {
                // ignore
              }
              // Stop the spinner immediately when we have a workflow draft
              setIsSending(false);
              try {
                abortControllerRef.current?.abort();
              } catch {
                // ignore
              }
              abortControllerRef.current = null;
            }

            const at = new Date().toISOString();
            if (evt?.type === 'tool_start') {
              appendTrace({ kind: 'tool_start', tool: evt.tool, at });
            } else if (evt?.type === 'tool_end') {
              appendTrace({ kind: 'tool_end', tool: evt.tool, at });
            } else {
              appendTrace({ kind: 'event', event: evt, at });
            }
          }
        );

        abortControllerRef.current = null;
        setAttachments([]);
        return;
      }
      
      // Add user message to UI immediately
      const tempUserMessage: Message = {
        id: Date.now(),
        role: 'user',
        content: userMessage,
        created_at: new Date().toISOString(),
        activity: attachmentRefs.length ? { attachments: attachmentRefs } : undefined,
      };
      setMessages(prev => [...prev, tempUserMessage]);
      
      // Enable auto-scroll for new messages (sending should "re-stick" to bottom)
      autoScrollEnabledRef.current = true;
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

      const appendTrace = (item: TraceItem) => {
        setMessages((prev) =>
          prev.map((msg: any) => (msg.id === assistantMessageId ? { ...msg, activity: [...(msg.activity || []), item] } : msg))
        );
      };
      
      // Use streaming API
      await sendMessageStream(
        currentConversation.id,
        {
          message: userMessage,
          attachments: attachmentRefs.length ? attachmentRefs : undefined,
          provider: selectedProvider,
          model: selectedModel,
          temperature,
        },
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
          // Stop UI "sending" immediately on done (don't wait for user actions)
          setIsSending(false);
          try {
            abortControllerRef.current?.abort();
          } catch {
            // ignore
          }
          abortControllerRef.current = null;
        },
        // onStatus: generation status
        (statusMessage) => {
          // Attach status/activity breadcrumbs to the in-flight assistant message
          setActivityExpanded(prev => ({ ...prev, [assistantMessageId]: true }));
          appendTrace({ kind: 'status', message: statusMessage, at: new Date().toISOString() });
        },
        // onGenerationComplete: code generation finished
        async (data) => {
          if (!data || typeof data !== 'object') {
            console.error('❌ generation_complete malformed:', data);
            alert('Code generation failed (malformed response)');
            return;
          }
          if ((data as any).success) {
            console.log('✅ Code generated:', data.node_type);
            // Reload conversation to get the generated code
            const convId = currentConversation.id;
            await loadConversation(convId);
            // Auto-open code panel on completion
            setShowCode(true);
          } else {
            const err = (data as any).error || 'Unknown error';
            console.error('❌ Generation failed:', err);
            alert('Code generation failed: ' + err);
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
        abortControllerRef.current.signal,
        // onEvent (workflow_draft + node draft events)
        (evt: any) => {
          if (evt?.type === 'workflow_draft') {
            setWorkflowDraftByMessageId((prev) => ({ ...prev, [assistantMessageId]: evt.workflow }));
            try {
              const text = JSON.stringify(evt.workflow, null, 2);
              setWorkflowDraftText(text);
              setEditedWorkflowText(text);
              setShowWorkflow(true);
              setShowCode(false);
              setIsEditingWorkflow(false);
            } catch {
              // ignore
            }
          }
          const at = new Date().toISOString();
          if (evt?.type === 'tool_start') {
            appendTrace({ kind: 'tool_start', tool: evt.tool, at });
          } else if (evt?.type === 'tool_end') {
            appendTrace({ kind: 'tool_end', tool: evt.tool, at });
          } else {
            appendTrace({ kind: 'event', event: evt, at });
          }
        }
      );
      setAttachments([]);
      
      // Clear abort controller after completion
      abortControllerRef.current = null;
      
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message: ' + (error as Error).message);
    } finally {
      setIsSending(false);
    }
  }

  const handleActivityClick = useCallback((item: TraceItem) => {
    setSelectedTrace(item);
    setTraceModalOpen(true);
  }, []);

  const handleCreateWorkflowDraftFromMessage = useCallback(async (messageId: number) => {
    const draft = workflowDraftByMessageId[messageId];
    if (!draft) return;

    const ok = confirm('Create this workflow draft in your workspace and open it in the editor?');
    if (!ok) return;

    setCreatingWorkflowFor(messageId);
    try {
      const tags = Array.isArray(draft.tags) ? draft.tags : [];
      const mergedTags = Array.from(new Set([...tags, 'ai_draft']));
      const metadata = {
        ...(draft.metadata || {}),
        created_by: 'builder',
        source_conversation_id: currentConversation?.id || null,
      };

      const created = await createWorkflow({
        name: draft.name || 'Untitled Workflow',
        description: draft.description || '',
        version: draft.version || '1.0',
        nodes: draft.nodes || [],
        connections: draft.connections || [],
        canvas_objects: draft.canvas_objects || [],
        tags: mergedTags,
        metadata,
        execution_config: draft.execution_config || null,
      });

      const url = `${window.location.origin}/editor-page?workflow=${created.id}`;
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to create workflow draft');
    } finally {
      setCreatingWorkflowFor(null);
    }
  }, [workflowDraftByMessageId, currentConversation?.id]);

  const handleCopyWorkflowDraft = useCallback(async (messageId: number) => {
    const draft = workflowDraftByMessageId[messageId];
    if (!draft) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(draft, null, 2));
    } catch {
      prompt('Copy workflow JSON:', JSON.stringify(draft, null, 2));
    }
  }, [workflowDraftByMessageId]);

  // (intentionally removed legacy non-memoized workflow handlers; use the useCallback versions above)

  function renderTraceModal() {
    if (!traceModalOpen || !selectedTrace) return null;
    const json = JSON.stringify(selectedTrace, null, 2);
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: 'rgba(0,0,0,0.5)' }}
        onClick={() => setTraceModalOpen(false)}
        role="dialog"
        aria-modal="true"
      >
        <div
          className="w-full max-w-3xl rounded-xl border shadow-lg overflow-hidden"
          style={{
            background: 'var(--theme-card-bg)',
            borderColor: 'var(--theme-border)',
            color: 'var(--theme-text)',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--theme-border)' }}>
            <div>
              <div className="font-semibold">Activity event details</div>
              <div className="text-sm" style={{ color: 'var(--theme-text-muted)' }}>
                Raw payload captured during streaming.
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="px-3 py-1.5 rounded-md border cursor-pointer hover:opacity-90 transition-opacity"
                style={{ background: 'transparent', borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(json);
                  } catch {
                    // ignore
                  }
                }}
              >
                Copy JSON
              </button>
              <button
                type="button"
                className="px-3 py-1.5 rounded-md border cursor-pointer hover:opacity-90 transition-opacity"
                style={{ background: 'transparent', borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}
                onClick={() => setTraceModalOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
          <pre
            className="p-4 text-xs overflow-auto"
            style={{
              maxHeight: '70vh',
              background: '#0b1220',
              color: '#c9d1d9',
              margin: 0,
            }}
          >
            {json}
          </pre>
        </div>
      </div>
    );
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
    <div
      className="flex overflow-hidden h-full"
      style={{ background: 'var(--theme-background)' }}
      onDragEnter={(e) => {
        if (!e.dataTransfer?.types?.includes('Files')) return;
        e.preventDefault();
        dragDepthRef.current += 1;
        setIsDragOver(true);
      }}
      onDragOver={(e) => {
        if (!e.dataTransfer?.types?.includes('Files')) return;
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={(e) => {
        if (!e.dataTransfer?.types?.includes('Files')) return;
        e.preventDefault();
        dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
        if (dragDepthRef.current === 0) setIsDragOver(false);
      }}
      onDrop={async (e) => {
        if (!e.dataTransfer?.files?.length) return;
        e.preventDefault();
        dragDepthRef.current = 0;
        setIsDragOver(false);
        await addAndUploadFiles(Array.from(e.dataTransfer.files));
      }}
    >
      {isDragOver && (
        <div className="absolute inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.55)' }}>
          <div className="border rounded-xl px-6 py-4 text-center" style={{ borderColor: 'var(--theme-border)', background: 'var(--theme-card-bg)' }}>
            <div className="text-lg font-semibold" style={{ color: 'var(--theme-text)' }}>Drop files to attach</div>
            <div className="text-xs mt-1" style={{ color: 'var(--theme-text-muted)' }}>Up to 5 files. Upload starts immediately.</div>
          </div>
        </div>
      )}
      {/* Sidebar - Conversations List - Fixed height with internal scroll */}
      <div className="w-80 flex flex-col border-r flex-shrink-0" style={{ 
        background: 'var(--theme-card-bg)',
        borderColor: 'var(--theme-border)'
      }}>
        {/* Top nav */}
        <div className="p-3 border-b flex items-center justify-between gap-2" style={{ borderColor: 'var(--theme-border)' }}>
          <div className="text-sm font-semibold" style={{ color: 'var(--theme-text)' }}>Builder</div>
          <button
            type="button"
            onClick={() => router.push('/builder/library')}
            className="text-xs px-2 py-1 rounded border cursor-pointer hover:opacity-90 transition-opacity"
            style={{
              borderColor: 'var(--theme-border)',
              background: 'var(--theme-card-bg-secondary)',
              color: 'var(--theme-text-muted)',
            }}
            title="Open My Nodes library"
          >
            My Nodes
          </button>
        </div>

        {/* Sticky header */}
        <div className="p-4 border-b flex-shrink-0" style={{ borderColor: 'var(--theme-border)' }}>
          <h1 className="text-xl font-bold mb-3 flex items-center gap-2" style={{ color: 'var(--theme-text)' }}>
            <i className="fa-solid fa-hammer"></i>
            Builder
          </h1>
          <button
            onClick={() => {
              setCurrentConversation(null);
              setMessages([]);
              setInputMessage('');
              setWorkflowDraftByMessageId({});
              setWorkflowDraftText('');
              setShowWorkflow(false);
              setIsEditingWorkflow(false);
              setEditedWorkflowText('');
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
            {/* Mode tabs (Chat / Node Code / Workflow Draft) */}
            {(currentConversation.generated_code || workflowDraftText) && (
              <div
                className="p-2 border-b flex justify-center gap-2"
                style={{ background: 'var(--theme-card-bg-secondary)', borderColor: 'var(--theme-border)' }}
              >
                <button
                  type="button"
                  onClick={() => {
                    setShowCode(false);
                    setShowWorkflow(false);
                  }}
                  className="px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                  style={{
                    background: !showCode && !showWorkflow ? 'var(--theme-button-primary)' : 'transparent',
                    color: !showCode && !showWorkflow ? 'white' : 'var(--theme-text)',
                    border: !showCode && !showWorkflow ? 'none' : `1px solid var(--theme-border)`,
                  }}
                >
                  <i className="fa-solid fa-message"></i>
                  Chat
                </button>

                {currentConversation.generated_code && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowCode(true);
                      setShowWorkflow(false);
                    }}
                    className="px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                    style={{
                      background: showCode ? 'var(--theme-button-primary)' : 'transparent',
                      color: showCode ? 'white' : 'var(--theme-text)',
                      border: showCode ? 'none' : `1px solid var(--theme-border)`,
                    }}
                  >
                    <i className="fa-solid fa-code"></i>
                    Node Code
                  </button>
                )}

                {!!workflowDraftText && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowWorkflow(true);
                      setShowCode(false);
                    }}
                    className="px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                    style={{
                      background: showWorkflow ? 'var(--theme-button-primary)' : 'transparent',
                      color: showWorkflow ? 'white' : 'var(--theme-text)',
                      border: showWorkflow ? 'none' : `1px solid var(--theme-border)`,
                    }}
                  >
                    <i className="fa-solid fa-diagram-project"></i>
                    Workflow Draft
                  </button>
                )}
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
                        <button
                          type="button"
                          onClick={() => {
                            // Treat anything non-"valid" as clickable so users can see details
                            // (some conversations may have null/undefined status but still have errors).
                            if (currentConversation.validation_status !== 'valid') {
                              setShowValidationDetails(true);
                            }
                          }}
                          className={`px-2 py-0.5 rounded ${
                            currentConversation.validation_status === 'valid'
                              ? 'bg-green-500/20 text-green-600'
                              : 'bg-red-500/20 text-red-600'
                          } ${currentConversation.validation_status !== 'valid' ? 'cursor-pointer hover:opacity-90' : 'cursor-default'}`}
                          title={
                            currentConversation.validation_status !== 'valid'
                              ? 'Click to see validation errors'
                              : undefined
                          }
                        >
                          {currentConversation.validation_status === 'valid' ? '✓ Valid' : '✗ Invalid'}
                        </button>
                        {currentConversation.class_name && (
                          <span style={{ color: 'var(--theme-text-muted)' }}>
                            Class: {currentConversation.class_name}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          const text = isEditingCode ? editedCode : currentConversation.generated_code!;
                          navigator.clipboard.writeText(text);
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
                        Copy
                      </button>

                      {!isEditingCode ? (
                        <button
                          onClick={() => {
                            setIsEditingCode(true);
                            setEditedCode(currentConversation.generated_code || '');
                            setCodeValidation(null);
                          }}
                          className="px-3 py-1.5 rounded-md border transition-colors flex items-center gap-2"
                          style={{
                            background: 'var(--theme-button-primary)',
                            borderColor: 'var(--theme-button-primary)',
                            color: 'white',
                          }}
                        >
                          <i className="fa-solid fa-pen"></i>
                          Edit
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={handleValidateEditedCode}
                            disabled={isValidatingCode}
                            className="px-3 py-1.5 rounded-md border transition-colors flex items-center gap-2 disabled:opacity-60"
                            style={{
                              background: 'transparent',
                              borderColor: 'var(--theme-border)',
                              color: 'var(--theme-text)',
                            }}
                          >
                            <i className={`fa-solid fa-${isValidatingCode ? 'spinner fa-spin' : 'check'}`}></i>
                            Validate
                          </button>

                          <button
                            onClick={handleSaveEditedCode}
                            disabled={isSavingCode || !codeIsDirty}
                            className="px-3 py-1.5 rounded-md border transition-colors flex items-center gap-2 disabled:opacity-60"
                            style={{
                              background: 'var(--theme-button-primary)',
                              borderColor: 'var(--theme-button-primary)',
                              color: 'white',
                            }}
                            title={!codeIsDirty ? 'No changes to save' : undefined}
                          >
                            <i className={`fa-solid fa-${isSavingCode ? 'spinner fa-spin' : 'floppy-disk'}`}></i>
                            Save
                          </button>

                          <button
                            onClick={() => {
                              const ok = !codeIsDirty || confirm('Discard your changes?');
                              if (!ok) return;
                              setIsEditingCode(false);
                              setEditedCode('');
                              setCodeValidation(null);
                            }}
                            className="px-3 py-1.5 rounded-md border transition-colors flex items-center gap-2"
                            style={{
                              background: 'transparent',
                              borderColor: 'var(--theme-border)',
                              color: 'var(--theme-text)',
                            }}
                          >
                            Cancel
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Validation details modal */}
                  {showValidationDetails && (
                    <div
                      className="fixed inset-0 z-50 flex items-center justify-center p-4"
                      style={{ background: 'rgba(0,0,0,0.5)' }}
                      onClick={() => setShowValidationDetails(false)}
                      role="dialog"
                      aria-modal="true"
                    >
                      <div
                        className="w-full max-w-2xl rounded-xl border shadow-lg"
                        style={{
                          background: 'var(--theme-card-bg)',
                          borderColor: 'var(--theme-border)',
                          color: 'var(--theme-text)',
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div
                          className="flex items-center justify-between px-4 py-3 border-b"
                          style={{ borderColor: 'var(--theme-border)' }}
                        >
                          <div>
                            <div className="font-semibold">Why is this code marked invalid?</div>
                            <div className="text-sm" style={{ color: 'var(--theme-text-muted)' }}>
                              Validation errors returned by the backend.
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => setShowValidationDetails(false)}
                            className="px-2 py-1 rounded-md border"
                            style={{
                              background: 'transparent',
                              borderColor: 'var(--theme-border)',
                              color: 'var(--theme-text)',
                            }}
                          >
                            Close
                          </button>
                        </div>

                        <div className="p-4 max-h-[60vh] overflow-auto">
                          {getValidationErrorsList().length ? (
                            <ul className="list-disc pl-5 space-y-2">
                              {getValidationErrorsList().map((err, idx) => (
                                <li key={idx} className="text-sm" style={{ color: 'var(--theme-text)' }}>
                                  {err}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div className="text-sm" style={{ color: 'var(--theme-text-muted)' }}>
                              No validation error details were provided for this conversation.
                            </div>
                          )}

                          {codeValidation?.warnings?.length ? (
                            <div className="mt-4">
                              <div className="font-semibold mb-2">Warnings</div>
                              <ul className="list-disc pl-5 space-y-2">
                                {codeValidation.warnings.map((w, idx) => (
                                  <li key={`w-${idx}`} className="text-sm" style={{ color: 'var(--theme-text)' }}>
                                    {w.message}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  )}

                  {isEditingCode ? (
                    <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--theme-border)' }}>
                      <div className="px-3 py-2 text-xs flex items-center justify-between" style={{ background: 'var(--theme-card-bg-secondary)', color: 'var(--theme-text-muted)' }}>
                        <span>Editing code (Python)</span>
                        <span>{codeIsDirty ? 'Unsaved changes' : 'No changes'}</span>
                      </div>
                      <textarea
                        value={editedCode}
                        onChange={(e) => setEditedCode(e.target.value)}
                        className="w-full font-mono text-sm p-3 outline-none"
                        style={{
                          minHeight: 520,
                          background: '#0b1220',
                          color: '#e5e7eb',
                        }}
                      />
                    </div>
                  ) : (
                    <div className="markdown-body" style={{ color: 'var(--theme-text)' }}>
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeHighlight]}
                        components={markdownComponents as any}
                      >
                        {currentConversation.generated_code.includes('```')
                          ? currentConversation.generated_code
                          : `\`\`\`python\n${currentConversation.generated_code}\n\`\`\``}
                      </ReactMarkdown>
                    </div>
                  )}

                  {/* Register action (separate from saving edits) */}
                  <div className="mt-6 flex justify-end">
                    <button
                      onClick={handleRegisterNode}
                      disabled={isSavingCode || currentConversation.validation_status !== 'valid' || (isEditingCode && codeIsDirty)}
                      className="px-4 py-2 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-60"
                      style={{
                        background:
                          currentConversation.validation_status === 'valid'
                            ? 'var(--theme-button-primary)'
                            : 'transparent',
                        border: `1px solid var(--theme-border)`,
                        color:
                          currentConversation.validation_status === 'valid'
                            ? 'white'
                            : 'var(--theme-text-muted)',
                      }}
                      title={
                        isEditingCode && codeIsDirty
                          ? 'Save your edits before registering'
                          : currentConversation.validation_status !== 'valid'
                            ? 'Code must be valid before registering'
                            : 'Register this node into the system'
                      }
                    >
                      <i className={`fa-solid fa-${isSavingCode ? 'spinner fa-spin' : 'plug-circle-check'}`}></i>
                      Register Node
                    </button>
                  </div>
                </div>
              </div>
            ) : showWorkflow && workflowDraftText ? (
              /* Workflow Draft View */
              <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--theme-background)', overflowY: 'auto', minHeight: 0 }}>
                <div className="max-w-5xl mx-auto">
                  <div className="mb-4 flex justify-between items-center">
                    <div>
                      <h3 className="text-xl font-bold mb-1" style={{ color: 'var(--theme-text)' }}>
                        Workflow Draft (JSON)
                      </h3>
                      <div className="text-sm" style={{ color: 'var(--theme-text-muted)' }}>
                        Edit if needed, then create a workflow draft in your workspace.
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(isEditingWorkflow ? editedWorkflowText : workflowDraftText);
                          alert('Workflow JSON copied to clipboard!');
                        }}
                        className="px-3 py-1.5 rounded-md border transition-colors flex items-center gap-2"
                        style={{ background: 'var(--theme-card-bg)', borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}
                      >
                        <i className="fa-solid fa-copy"></i>
                        Copy
                      </button>

                      {!isEditingWorkflow ? (
                        <button
                          type="button"
                          onClick={() => {
                            setIsEditingWorkflow(true);
                            setEditedWorkflowText(workflowDraftText);
                          }}
                          className="px-3 py-1.5 rounded-md border transition-colors flex items-center gap-2"
                          style={{ background: 'var(--theme-button-primary)', borderColor: 'var(--theme-button-primary)', color: 'white' }}
                        >
                          <i className="fa-solid fa-pen"></i>
                          Edit
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            setIsEditingWorkflow(false);
                            setEditedWorkflowText(workflowDraftText);
                          }}
                          className="px-3 py-1.5 rounded-md border transition-colors flex items-center gap-2"
                          style={{ background: 'transparent', borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}
                        >
                          Cancel
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            const raw = isEditingWorkflow ? editedWorkflowText : workflowDraftText;
                            const draft = JSON.parse(raw);
                            const created = await createWorkflow({
                              name: draft.name || 'Untitled Workflow',
                              description: draft.description || '',
                              version: draft.version || '1.0',
                              nodes: draft.nodes || [],
                              connections: draft.connections || [],
                              canvas_objects: draft.canvas_objects || [],
                              tags: Array.from(new Set([...(draft.tags || []), 'ai_draft'])),
                              metadata: { ...(draft.metadata || {}), created_by: 'builder', source_conversation_id: currentConversation?.id || null },
                              execution_config: draft.execution_config || null,
                            });
                            window.open(`${window.location.origin}/editor-page?workflow=${created.id}`, '_blank', 'noopener,noreferrer');
                          } catch (e) {
                            alert(e instanceof Error ? e.message : 'Invalid workflow JSON');
                          }
                        }}
                        className="px-3 py-1.5 rounded-md border transition-colors flex items-center gap-2"
                        style={{ background: 'var(--theme-button-primary)', borderColor: 'var(--theme-button-primary)', color: 'white' }}
                      >
                        <i className="fa-solid fa-hammer"></i>
                        Create Draft
                      </button>
                    </div>
                  </div>

                  <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--theme-border)' }}>
                    <div className="px-3 py-2 text-xs flex items-center justify-between" style={{ background: 'var(--theme-card-bg-secondary)', color: 'var(--theme-text-muted)' }}>
                      <span>{isEditingWorkflow ? 'Editing workflow JSON' : 'Workflow JSON'}</span>
                      <span>{(isEditingWorkflow ? editedWorkflowText : workflowDraftText).length.toLocaleString()} chars</span>
                    </div>
                    {isEditingWorkflow ? (
                      <textarea
                        value={editedWorkflowText}
                        onChange={(e) => setEditedWorkflowText(e.target.value)}
                        className="w-full font-mono text-xs p-3 outline-none"
                        style={{ minHeight: 520, background: '#0b1220', color: '#e5e7eb' }}
                      />
                    ) : (
                      <pre className="p-3 text-xs overflow-auto" style={{ minHeight: 520, background: '#0b1220', color: '#c9d1d9', margin: 0 }}>
                        {workflowDraftText}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
            ) : (
            <MessagesPanel
              messages={visibleMessages as any}
              isSending={isSending}
              activityExpanded={activityExpanded}
              setActivityExpanded={setActivityExpanded}
              workflowDraftByMessageId={workflowDraftByMessageId}
              onCreateWorkflowDraft={handleCreateWorkflowDraftFromMessage}
              creatingWorkflowFor={creatingWorkflowFor}
              onCopyWorkflowDraft={handleCopyWorkflowDraft}
              markdownComponents={markdownComponents}
              messagesEndRef={messagesEndRef}
              onActivityClick={handleActivityClick}
              containerRef={messagesContainerRef}
            />
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

                  {attachments.length > 0 && (
                    <div className="px-4 pb-2 flex flex-wrap gap-2">
                      {attachments.map((a) => (
                        <div
                          key={a.localId}
                          className="text-xs border rounded-lg px-2 py-1 flex items-center gap-2 max-w-full"
                          style={{ borderColor: 'var(--theme-border)', background: 'var(--theme-card-bg-secondary)', color: 'var(--theme-text)' }}
                          title={a.file.name}
                        >
                          <i className="fa-solid fa-paperclip" style={{ opacity: 0.8 }} />
                          <span className="truncate max-w-[220px]">{a.file.name}</span>
                          <span style={{ color: 'var(--theme-text-muted)' }}>{formatFileSize(a.file.size)}</span>
                          {a.status === 'uploading' ? (
                            <span style={{ color: 'var(--theme-text-muted)' }}>{Math.round(a.progress)}%</span>
                          ) : a.status === 'error' ? (
                            <span style={{ color: '#ef4444' }}>failed</span>
                          ) : (
                            <span style={{ color: '#22c55e' }}>ready</span>
                          )}
                          <button
                            type="button"
                            className="ml-1 hover:opacity-80"
                            style={{ color: 'var(--theme-text-muted)' }}
                            onClick={() => removeAttachment(a.localId)}
                            disabled={a.status === 'uploading'}
                            title={a.status === 'uploading' ? 'Uploading…' : 'Remove'}
                          >
                            <i className="fa-solid fa-xmark" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* Bottom controls bar */}
                  <div className="flex items-center justify-between px-3 pb-3 pt-1 border-t" style={{ borderColor: 'var(--theme-border)' }}>
                    {/* Left side controls */}
                    <div className="flex items-center gap-2">
                      {/* Attachment button */}
                      <div className="relative" ref={attachMenuRef}>
                        <button
                          type="button"
                          onClick={() => setShowAttachMenu((v) => !v)}
                          className="p-2 hover:opacity-80 rounded-lg transition-colors"
                          style={{ color: 'var(--theme-text-muted)' }}
                          title="Add attachment"
                          disabled={isSending}
                        >
                          <i className="fa-solid fa-plus text-sm"></i>
                        </button>

                        {showAttachMenu && (
                          <div
                            className="absolute bottom-full left-0 mb-2 border rounded-lg shadow-lg p-2 w-56 z-50"
                            style={{ background: 'var(--theme-card-bg)', borderColor: 'var(--theme-border)' }}
                          >
                            <button
                              type="button"
                              className="w-full text-left px-3 py-2 rounded hover:opacity-90 transition-opacity"
                              style={{ color: 'var(--theme-text)' }}
                              onClick={() => {
                                setShowAttachMenu(false);
                                fileInputRef.current?.click();
                              }}
                            >
                              Add photos and files
                            </button>
                          </div>
                        )}
                      </div>

                      <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        className="hidden"
                        accept="image/*,audio/*,video/*,.pdf,.docx,.doc,.txt,.md,.csv,.json"
                        onChange={async (e) => {
                          const files = e.target.files ? Array.from(e.target.files) : [];
                          // reset so selecting same file again works
                          e.target.value = '';
                          await addAndUploadFiles(files);
                        }}
                      />
                      
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
                          disabled={!inputMessage.trim() || isUploadingAttachments || hasAttachmentError}
                          className="text-white p-2 rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center ml-1"
                          style={{
                            background:
                              inputMessage.trim() && !isUploadingAttachments && !hasAttachmentError
                                ? "var(--theme-button-primary)"
                                : undefined,
                          }}
                          title={
                            isUploadingAttachments
                              ? 'Uploading attachments…'
                              : hasAttachmentError
                                ? 'Remove failed attachments before sending'
                                : 'Send message'
                          }
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
                <i className="fa-solid fa-hammer text-6xl"></i>
              </div>
              <h2 className="text-3xl font-bold mb-3" style={{ color: 'var(--theme-text)' }}>
                Build Nodes & Workflows
              </h2>
              <p className="mb-6" style={{ color: 'var(--theme-text-muted)' }}>
                Describe what you want to build — a custom node (Python) or a workflow draft (workflow JSON) — and I’ll help you generate it.
              </p>
              <div className="border rounded-lg p-4 text-left" style={{
                background: 'var(--theme-card-bg)',
                borderColor: 'var(--theme-border-secondary)'
              }}>
                <p className="text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>Example prompts:</p>
                <ul className="text-sm space-y-1" style={{ color: 'var(--theme-text-muted)' }}>
                  <li>• "Create a workflow: Text Input → Telegram: Send Message → Text Display"</li>
                  <li>• "Draft a workflow JSON that watches a folder and emails a report"</li>
                  <li>• "Create a node that fetches weather data from OpenWeatherMap"</li>
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
                  placeholder="Describe what you want to build (node or workflow)..."
                  disabled={isSending}
                  rows={3}
                  className="w-full px-4 pt-4 pb-2 focus:outline-none bg-transparent resize-none"
                  style={{ color: 'var(--theme-text)' }}
                  autoFocus
                />

                {attachments.length > 0 && (
                  <div className="px-4 pb-2 flex flex-wrap gap-2">
                    {attachments.map((a) => (
                      <div
                        key={a.localId}
                        className="text-xs border rounded-lg px-2 py-1 flex items-center gap-2 max-w-full"
                        style={{ borderColor: 'var(--theme-border)', background: 'var(--theme-card-bg-secondary)', color: 'var(--theme-text)' }}
                        title={a.file.name}
                      >
                        <i className="fa-solid fa-paperclip" style={{ opacity: 0.8 }} />
                        <span className="truncate max-w-[220px]">{a.file.name}</span>
                        <span style={{ color: 'var(--theme-text-muted)' }}>{formatFileSize(a.file.size)}</span>
                        {a.status === 'uploading' ? (
                          <span style={{ color: 'var(--theme-text-muted)' }}>{Math.round(a.progress)}%</span>
                        ) : a.status === 'error' ? (
                          <span style={{ color: '#ef4444' }}>failed</span>
                        ) : (
                          <span style={{ color: '#22c55e' }}>ready</span>
                        )}
                        <button
                          type="button"
                          className="ml-1 hover:opacity-80"
                          style={{ color: 'var(--theme-text-muted)' }}
                          onClick={() => removeAttachment(a.localId)}
                          disabled={a.status === 'uploading'}
                          title={a.status === 'uploading' ? 'Uploading…' : 'Remove'}
                        >
                          <i className="fa-solid fa-xmark" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Bottom controls bar */}
                <div className="flex items-center justify-between px-3 pb-3 pt-1 border-t" style={{ borderColor: 'var(--theme-border)' }}>
                  {/* Left side controls */}
                  <div className="flex items-center gap-2">
                    {/* Attachment button */}
                    <div className="relative" ref={attachMenuRef}>
                      <button
                        type="button"
                        onClick={() => setShowAttachMenu((v) => !v)}
                        className="p-2 hover:opacity-80 rounded-lg transition-colors"
                        style={{ color: 'var(--theme-text-muted)' }}
                        title="Add attachment"
                        disabled={isSending}
                      >
                        <i className="fa-solid fa-plus text-sm"></i>
                      </button>

                      {showAttachMenu && (
                        <div
                          className="absolute bottom-full left-0 mb-2 border rounded-lg shadow-lg p-2 w-56 z-50"
                          style={{ background: 'var(--theme-card-bg)', borderColor: 'var(--theme-border)' }}
                        >
                          <button
                            type="button"
                            className="w-full text-left px-3 py-2 rounded hover:opacity-90 transition-opacity"
                            style={{ color: 'var(--theme-text)' }}
                            onClick={() => {
                              setShowAttachMenu(false);
                              fileInputRef.current?.click();
                            }}
                          >
                            Add photos and files
                          </button>
                        </div>
                      )}
                    </div>

                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      className="hidden"
                      accept="image/*,audio/*,video/*,.pdf,.docx,.doc,.txt,.md,.csv,.json"
                      onChange={async (e) => {
                        const files = e.target.files ? Array.from(e.target.files) : [];
                        e.target.value = '';
                        await addAndUploadFiles(files);
                      }}
                    />
                    
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
                        disabled={!inputMessage.trim() || isUploadingAttachments || hasAttachmentError}
                        className="text-white p-2 rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center ml-1"
                        style={{
                          background:
                            inputMessage.trim() && !isUploadingAttachments && !hasAttachmentError
                              ? "var(--theme-button-primary)"
                              : undefined,
                        }}
                        title={
                          isUploadingAttachments
                            ? 'Uploading attachments…'
                            : hasAttachmentError
                              ? 'Remove failed attachments before sending'
                              : 'Send message'
                        }
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

      {renderTraceModal()}
    </div>
  );
}


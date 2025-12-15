'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { use } from 'react';
import { getApiBaseUrl } from '@/lib/api-config';
import { FilePicker } from '@/components/FilePicker';
import type { FileMetadata } from '@/lib/files';

interface Attachment {
  filename: string;
  content_type: string;
  size?: number;
  data?: string; // base64 encoded data
  path?: string; // file path on server
  file_id?: string; // file ID for newly uploaded files
  is_new?: boolean; // flag to indicate newly uploaded file
}

interface EmailDraft {
  recipient: string;
  subject: string;
  body: string;
  attachments?: Attachment[];
}

interface InteractionData {
  interaction_id: string;
  status: string;
  original_draft: EmailDraft;
  expires_at: string;
  time_remaining_seconds: number;
  is_expired: boolean;
}

export default function ReviewEmailPage({ params }: { params: Promise<{ interaction_id: string }> }) {
  // Unwrap params Promise using React.use()
  const { interaction_id } = use(params);
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const [interaction, setInteraction] = useState<InteractionData | null>(null);
  const [draft, setDraft] = useState<EmailDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState<string>('');
  const [previewAttachment, setPreviewAttachment] = useState<Attachment | null>(null);
  const [showAddAttachment, setShowAddAttachment] = useState(false);

  useEffect(() => {
    if (!token) {
      setError('Missing security token');
      setLoading(false);
      return;
    }

    // Fetch interaction data
    fetchInteraction();
  }, [interaction_id, token]);

  // Update countdown timer
  useEffect(() => {
    if (!interaction) return;

    const updateTimer = () => {
      const remaining = interaction.time_remaining_seconds;
      if (remaining <= 0) {
        setTimeRemaining('Expired');
        return;
      }

      const hours = Math.floor(remaining / 3600);
      const minutes = Math.floor((remaining % 3600) / 60);
      const seconds = remaining % 60;

      setTimeRemaining(`${hours}h ${minutes}m ${seconds}s`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [interaction]);

  const fetchInteraction = async () => {
    try {
      const response = await fetch(
        `${getApiBaseUrl()}/api/v1/email-interactions/${interaction_id}?token=${token}`
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to fetch interaction');
      }

      const data: InteractionData = await response.json();
      setInteraction(data);
      setDraft(data.original_draft);
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to load email draft');
      setLoading(false);
    }
  };

  const handleSubmit = async (action: 'approve' | 'reject') => {
    if (!draft || !token) return;

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(
        `${getApiBaseUrl()}/api/v1/email-interactions/${interaction_id}/submit`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            token,
            action,
            edited_draft: draft,
          }),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Submission failed');
      }

      const result = await response.json();
      setSuccess(true);

      // Show success message for 2 seconds then close
      setTimeout(() => {
        window.close();
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to submit');
      setSubmitting(false);
    }
  };

  const handleAttachmentClick = async (attachment: Attachment, index: number) => {
    console.log('Attachment clicked:', attachment.filename, 'at index', index);
    
    try {
      console.log('Fetching attachment from server...');
      
      let response;
      
      // Check if this is a newly uploaded file
      if (attachment.is_new && attachment.file_id) {
        // Use file API for newly uploaded files
        console.log('Fetching from file API (newly uploaded):', attachment.file_id);
        response = await fetch(
          `${getApiBaseUrl()}/api/v1/files/${attachment.file_id}/view`,
          { credentials: 'include' }
        );
      } else {
        // Use email interaction endpoint for original attachments
        console.log('Fetching from email interaction API (original):', index);
        response = await fetch(
          `${getApiBaseUrl()}/api/v1/email-interactions/${interaction_id}/attachments/${index}?token=${token}`
        );
      }
      
      if (!response.ok) {
        throw new Error(`Failed to fetch attachment: ${response.statusText}`);
      }
      
      // Get the blob from response with correct content type
      const contentType = response.headers.get('content-type') || attachment.content_type || 'application/octet-stream';
      const blob = await response.blob();
      
      // Create a new blob with the correct content type
      const typedBlob = new Blob([blob], { type: contentType });
      const url = URL.createObjectURL(typedBlob);
      
      console.log(`Created blob URL with content type: ${contentType}`);
      
      // Determine if browser can view this type inline
      // CSV, Excel, Word docs etc should be downloaded, not viewed inline
      const shouldDownload = contentType.includes('csv') ||
                            contentType.includes('excel') ||
                            contentType.includes('spreadsheet') ||
                            contentType.includes('msword') ||
                            contentType.includes('wordprocessingml') ||
                            contentType.includes('zip') ||
                            contentType.includes('compressed') ||
                            contentType === 'application/octet-stream';
      
      const canViewInline = !shouldDownload && (
                           contentType.startsWith('image/') || 
                           contentType.includes('pdf') ||
                           contentType.startsWith('video/') ||
                           contentType.startsWith('audio/') ||
                           (contentType.startsWith('text/') && !contentType.includes('csv'))
                           );
      
      if (canViewInline) {
        // Try to open in new tab for preview
        const newWindow = window.open(url, '_blank');
        if (!newWindow) {
          console.log('Popup blocked, downloading instead');
          // Popup blocked - download with proper filename
          const link = document.createElement('a');
          link.href = url;
          link.download = attachment.filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        } else {
          console.log('Successfully opened in new window');
          // Set document title in new window to filename
          setTimeout(() => {
            try {
              if (newWindow.document) {
                newWindow.document.title = attachment.filename;
              }
            } catch (e) {
              // Cross-origin security - ignore
            }
            URL.revokeObjectURL(url);
          }, 60000);
        }
      } else {
        // Can't view inline - download with proper filename
        console.log('Not viewable inline, downloading with filename:', attachment.filename);
        const link = document.createElement('a');
        link.href = url;
        link.download = attachment.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(url), 100);
      }
    } catch (err) {
      console.error('Error opening attachment:', err);
      setError(`Failed to open attachment: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleDeleteAttachment = (index: number) => {
    if (!draft) return;
    
    const attachmentName = draft.attachments?.[index]?.filename || `attachment ${index + 1}`;
    
    if (!confirm(`Remove "${attachmentName}" from this email?\n\nThe file will not be included when the email is sent.`)) {
      return;
    }
    
    // Remove attachment from draft
    const newAttachments = [...(draft.attachments || [])];
    newAttachments.splice(index, 1);
    
    setDraft({
      ...draft,
      attachments: newAttachments
    });
  };

  const handleAddAttachment = (fileId: string | null, file: FileMetadata | null) => {
    if (!fileId || !file || !draft) return;
    
    // Add to attachments array with file_id for newly uploaded files
    const newAttachment: Attachment = {
      filename: file.filename,
      content_type: file.mime_type,
      size: file.file_size_bytes,
      path: file.storage_path,
      file_id: fileId, // Store the file ID
      is_new: true // Mark as newly uploaded
    };
    
    setDraft({
      ...draft,
      attachments: [...(draft.attachments || []), newAttachment]
    });
    
    // Hide the file picker
    setShowAddAttachment(false);
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'Unknown size';
    const kb = bytes / 1024;
    const mb = kb / 1024;
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    return `${kb.toFixed(2)} KB`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading email draft...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
          <div className="text-center">
            <div className="text-red-600 text-5xl mb-4">⚠️</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Error</h1>
            <p className="text-gray-600">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
          <div className="text-center">
            <div className="text-green-600 text-5xl mb-4">✅</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Success!</h1>
            <p className="text-gray-600">Email has been processed and workflow resumed.</p>
            <p className="text-sm text-gray-500 mt-2">This window will close shortly...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!draft) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 overflow-y-auto">
      <div className="max-w-3xl mx-auto pb-8">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Review Email Draft</h1>
              <p className="text-sm text-gray-600 mt-1">Review and edit the email before sending</p>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium text-gray-700">Time Remaining</div>
              <div className={`text-lg font-bold ${
                interaction && interaction.time_remaining_seconds < 3600 
                  ? 'text-red-600' 
                  : 'text-green-600'
              }`}>
                {timeRemaining}
              </div>
            </div>
          </div>

          {interaction?.is_expired && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              ⚠️ This review link has expired. The workflow has been terminated.
            </div>
          )}
        </div>

        {/* Email Form */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <form onSubmit={(e) => e.preventDefault()}>
            {/* Recipient */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                To (Recipient)
              </label>
              <input
                type="email"
                value={draft.recipient}
                onChange={(e) => setDraft({ ...draft, recipient: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={submitting || interaction?.is_expired}
                required
              />
            </div>

            {/* Subject */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Subject
              </label>
              <input
                type="text"
                value={draft.subject}
                onChange={(e) => setDraft({ ...draft, subject: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={submitting || interaction?.is_expired}
                required
              />
            </div>

            {/* Body */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Message
              </label>
              <textarea
                value={draft.body}
                onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                rows={12}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm resize-y overflow-y-auto"
                style={{ minHeight: '200px', maxHeight: '400px' }}
                disabled={submitting || interaction?.is_expired}
                required
              />
            </div>

            {/* Attachments Info */}
            {draft.attachments && draft.attachments.length > 0 && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm font-medium text-blue-900">
                    📎 Attachments ({draft.attachments.length})
                  </div>
                  {!submitting && !interaction?.is_expired && !showAddAttachment && (
                    <button
                      onClick={() => setShowAddAttachment(true)}
                      className="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors flex items-center gap-1"
                    >
                      <i className="fas fa-plus"></i>
                      <span>Add File</span>
                    </button>
                  )}
                </div>
                
                {/* File Picker for adding new attachment */}
                {showAddAttachment && (
                  <div className="mb-3 p-3 bg-white border border-blue-300 rounded-md">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-blue-900">Select file to attach:</span>
                      <button
                        onClick={() => setShowAddAttachment(false)}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        <i className="fas fa-times"></i>
                      </button>
                    </div>
                    <FilePicker
                      value=""
                      onChange={handleAddAttachment}
                      placeholder="Choose a file or upload new..."
                    />
                  </div>
                )}
                
                <div className="space-y-2">
                  {draft.attachments.map((att, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 bg-white border border-blue-300 rounded-md hover:bg-blue-50 transition-all"
                    >
                      <div 
                        className="flex items-center gap-3 flex-1 cursor-pointer"
                        onClick={() => handleAttachmentClick(att, idx)}
                      >
                        <span className="text-2xl">
                          {att.content_type?.startsWith('image/') ? '🖼️' :
                           att.content_type?.includes('pdf') ? '📄' :
                           att.content_type?.includes('csv') ? '📊' :
                           att.content_type?.includes('excel') || att.content_type?.includes('spreadsheet') ? '📊' :
                           att.content_type?.includes('word') ? '📝' :
                           att.content_type?.startsWith('video/') ? '🎥' :
                           att.content_type?.startsWith('audio/') ? '🎵' : '📎'}
                        </span>
                        <div className="flex-1">
                          <div className="text-sm font-medium text-blue-900">
                            {att.filename || `Attachment ${idx + 1}`}
                          </div>
                          <div className="text-xs text-blue-600">
                            {att.content_type} • {formatFileSize(att.size)}
                          </div>
                        </div>
                        <div className="text-blue-600">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </div>
                      </div>
                      {!submitting && !interaction?.is_expired && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteAttachment(idx);
                          }}
                          className="ml-3 px-2 py-1 text-xs rounded bg-red-500 text-white hover:bg-red-600 transition-colors"
                          title="Remove attachment"
                        >
                          <i className="fas fa-times"></i>
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <p className="text-xs text-blue-700 mt-3 italic">
                  💡 Click to preview/download • Click ✕ to remove
                </p>
              </div>
            )}

            {/* Add Attachment button when no attachments */}
            {(!draft.attachments || draft.attachments.length === 0) && !submitting && !interaction?.is_expired && (
              <div className="mb-6">
                {!showAddAttachment ? (
                  <button
                    onClick={() => setShowAddAttachment(true)}
                    className="w-full p-4 border-2 border-dashed border-blue-300 rounded-md hover:border-blue-400 hover:bg-blue-50 transition-all flex items-center justify-center gap-2 text-blue-700"
                  >
                    <i className="fas fa-paperclip text-xl"></i>
                    <span className="font-medium">Add Attachment</span>
                  </button>
                ) : (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-blue-900">Select file to attach:</span>
                      <button
                        onClick={() => setShowAddAttachment(false)}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        <i className="fas fa-times"></i>
                      </button>
                    </div>
                    <FilePicker
                      value=""
                      onChange={handleAddAttachment}
                      placeholder="Choose a file or upload new..."
                    />
                  </div>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => handleSubmit('approve')}
                disabled={submitting || interaction?.is_expired}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-md transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {submitting ? '⏳ Processing...' : '✅ Approve & Send'}
              </button>
              <button
                type="button"
                onClick={() => handleSubmit('reject')}
                disabled={submitting || interaction?.is_expired}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-3 px-6 rounded-md transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {submitting ? '⏳ Processing...' : '❌ Reject'}
              </button>
            </div>

            {error && (
              <div className="mt-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}
          </form>
        </div>

        {/* Help Text */}
        <div className="mt-6 text-center text-sm text-gray-600">
          <p>Make any necessary changes to the email above, then click "Approve & Send" to send it.</p>
          <p className="mt-2">Click "Reject" to cancel without sending.</p>
        </div>
      </div>
    </div>
  );
}


/**
 * Media Viewer Configuration Component
 * 
 * Comprehensive viewer for all media types in the configuration panel:
 * - Documents (PDF, DOCX, etc.)
 * - Images (PNG, JPEG, GIF, WebP, etc.)
 * - Video (MP4, WebM, etc.)
 * - Audio (MP3, WAV, OGG, etc.)
 * 
 * Auto-detects media type from file extension/MIME type and renders appropriate viewer.
 */

import React from 'react';
import { getApiBaseUrl } from '@/lib/api-config';
import type { FileCategory } from '@/lib/files';

interface MediaViewerConfigProps {
  fileId: string;
  fileCategory?: FileCategory;
  accept?: string; // MIME types or file extensions (e.g., '.pdf,.docx', 'image/*')
  height?: string; // CSS height (default: '500px')
  className?: string;
  onClick?: () => void; // Click handler to open modal
}

/**
 * Detects media type from accept string or file category
 */
function detectMediaType(
  fileCategory?: FileCategory,
  accept?: string
): 'document' | 'image' | 'video' | 'audio' | 'unknown' {
  // Priority 1: Use explicit file category
  if (fileCategory) {
    // Map FileCategory to viewer type
    if (fileCategory === 'archive' || fileCategory === 'other') {
      return 'unknown'; // Archive and other files use fallback viewer
    }
    return fileCategory as 'document' | 'image' | 'video' | 'audio';
  }

  // Priority 2: Auto-detect from accept string
  if (!accept) {
    return 'unknown';
  }

  const lower = accept.toLowerCase();

  // Check for document types
  if (
    lower.includes('pdf') ||
    lower.includes('doc') ||
    lower.includes('docx') ||
    lower.includes('application/pdf') ||
    lower.includes('application/msword') ||
    lower.includes('application/vnd.openxmlformats-officedocument')
  ) {
    return 'document';
  }

  // Check for image types
  if (
    lower.includes('image/') ||
    lower.includes('png') ||
    lower.includes('jpg') ||
    lower.includes('jpeg') ||
    lower.includes('gif') ||
    lower.includes('webp') ||
    lower.includes('svg')
  ) {
    return 'image';
  }

  // Check for video types
  if (
    lower.includes('video/') ||
    lower.includes('mp4') ||
    lower.includes('webm') ||
    lower.includes('ogg') ||
    lower.includes('mov') ||
    lower.includes('avi')
  ) {
    return 'video';
  }

  // Check for audio types
  if (
    lower.includes('audio/') ||
    lower.includes('mp3') ||
    lower.includes('wav') ||
    lower.includes('ogg') ||
    lower.includes('m4a') ||
    lower.includes('flac')
  ) {
    return 'audio';
  }

  return 'unknown';
}

/**
 * Document Viewer Component (PDF, DOCX, etc.)
 */
function DocumentViewer({ fileId, height = '500px', onClick }: { fileId: string; height?: string; onClick?: () => void }) {
  return (
    <div className="relative">
      <div
        className="border rounded overflow-hidden"
        style={{
          borderColor: 'var(--theme-border)',
          background: 'var(--theme-surface)',
        }}
      >
        <object
          data={`${getApiBaseUrl()}/api/v1/files/${fileId}/view#toolbar=0&navpanes=0`}
          type="application/pdf"
          className="w-full"
          style={{ height }}
        >
          <div className="p-4 text-center" style={{ color: 'var(--theme-text-secondary)' }}>
            <i className="fas fa-file-pdf text-3xl mb-2" style={{ opacity: 0.5 }}></i>
            <p className="text-sm mb-2">Document preview not available in your browser.</p>
            <a
              href={`${getApiBaseUrl()}/api/v1/files/${fileId}/download`}
              className="text-blue-500 underline text-sm"
              target="_blank"
              rel="noopener noreferrer"
            >
              <i className="fas fa-download mr-1"></i>
              Click here to download and view
            </a>
          </div>
        </object>
      </div>
      {/* Expand button overlay */}
      {onClick && (
        <button
          onClick={onClick}
          className="absolute top-2 right-2 p-2 rounded-lg transition-all"
          style={{
            background: 'rgba(0, 0, 0, 0.6)',
            color: 'white',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(0, 0, 0, 0.8)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(0, 0, 0, 0.6)';
          }}
          title="Open in full screen"
        >
          <i className="fas fa-expand text-sm"></i>
        </button>
      )}
    </div>
  );
}

/**
 * Image Viewer Component
 */
function ImageViewer({ fileId, height = '500px', onClick }: { fileId: string; height?: string; onClick?: () => void }) {
  return (
    <div className="relative">
      <div
        className="border rounded overflow-hidden flex items-center justify-center"
        style={{
          borderColor: 'var(--theme-border)',
          background: 'var(--theme-surface)',
          height,
        }}
      >
        <img
          src={`${getApiBaseUrl()}/api/v1/files/${fileId}/view`}
          alt="Preview"
          className="max-w-full max-h-full object-contain"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            const container = target.parentElement;
            if (container) {
              container.innerHTML = `
                <div class="p-4 text-center" style="color: var(--theme-text-secondary)">
                  <i class="fas fa-image text-3xl mb-2" style="opacity: 0.5"></i>
                  <p class="text-sm mb-2">Image preview not available.</p>
                  <a
                    href="${getApiBaseUrl()}/api/v1/files/${fileId}/download"
                    class="text-blue-500 underline text-sm"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <i class="fas fa-download mr-1"></i>
                    Click here to download
                  </a>
                </div>
              `;
            }
          }}
        />
      </div>
      {/* Expand button overlay */}
      {onClick && (
        <button
          onClick={onClick}
          className="absolute top-2 right-2 p-2 rounded-lg transition-all"
          style={{
            background: 'rgba(0, 0, 0, 0.6)',
            color: 'white',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(0, 0, 0, 0.8)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(0, 0, 0, 0.6)';
          }}
          title="Open in full screen"
        >
          <i className="fas fa-expand text-sm"></i>
        </button>
      )}
    </div>
  );
}

/**
 * Video Viewer Component
 */
function VideoViewer({ fileId, height = '500px' }: { fileId: string; height?: string }) {
  return (
    <div
      className="border rounded overflow-hidden"
      style={{
        borderColor: 'var(--theme-border)',
        background: 'var(--theme-surface)',
      }}
    >
      <video
        controls
        className="w-full"
        style={{ height, maxHeight: height }}
        onError={(e) => {
          const target = e.target as HTMLVideoElement;
          target.style.display = 'none';
          const container = target.parentElement;
          if (container) {
            container.innerHTML = `
              <div class="p-4 text-center" style="color: var(--theme-text-secondary)">
                <i class="fas fa-video text-3xl mb-2" style="opacity: 0.5"></i>
                <p class="text-sm mb-2">Video preview not available in your browser.</p>
                <a
                  href="${getApiBaseUrl()}/api/v1/files/${fileId}/download"
                  class="text-blue-500 underline text-sm"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <i class="fas fa-download mr-1"></i>
                  Click here to download and view
                </a>
              </div>
            `;
          }
        }}
      >
        <source src={`${getApiBaseUrl()}/api/v1/files/${fileId}/view`} />
        <p className="p-4 text-center text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
          Your browser doesn't support video playback.
          <a
            href={`${getApiBaseUrl()}/api/v1/files/${fileId}/download`}
            className="text-blue-500 underline ml-1"
            target="_blank"
            rel="noopener noreferrer"
          >
            Download video
          </a>
        </p>
      </video>
    </div>
  );
}

/**
 * Audio Viewer Component
 */
function AudioViewer({ fileId, height = '80px' }: { fileId: string; height?: string }) {
  return (
    <div
      className="border rounded overflow-hidden p-4"
      style={{
        borderColor: 'var(--theme-border)',
        background: 'var(--theme-surface)',
      }}
    >
      <div className="flex items-center gap-3">
        <i
          className="fas fa-music text-2xl"
          style={{ color: 'var(--theme-primary)', opacity: 0.7 }}
        ></i>
        <div className="flex-1">
          <audio
            controls
            className="w-full"
            style={{ height }}
            onError={(e) => {
              const target = e.target as HTMLAudioElement;
              target.style.display = 'none';
              const container = target.parentElement?.parentElement;
              if (container) {
                container.innerHTML = `
                  <div class="p-4 text-center" style="color: var(--theme-text-secondary)">
                    <i class="fas fa-headphones text-3xl mb-2" style="opacity: 0.5"></i>
                    <p class="text-sm mb-2">Audio preview not available in your browser.</p>
                    <a
                      href="${getApiBaseUrl()}/api/v1/files/${fileId}/download"
                      class="text-blue-500 underline text-sm"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <i class="fas fa-download mr-1"></i>
                      Click here to download and listen
                    </a>
                  </div>
                `;
              }
            }}
          >
            <source src={`${getApiBaseUrl()}/api/v1/files/${fileId}/view`} />
            <p className="text-sm" style={{ color: 'var(--theme-text-secondary)' }}>
              Your browser doesn't support audio playback.
              <a
                href={`${getApiBaseUrl()}/api/v1/files/${fileId}/download`}
                className="text-blue-500 underline ml-1"
                target="_blank"
                rel="noopener noreferrer"
              >
                Download audio
              </a>
            </p>
          </audio>
        </div>
      </div>
    </div>
  );
}

/**
 * Unknown/Fallback Viewer Component
 */
function UnknownViewer({ fileId }: { fileId: string }) {
  return (
    <div
      className="border rounded p-6 text-center"
      style={{
        borderColor: 'var(--theme-border)',
        background: 'var(--theme-surface)',
      }}
    >
      <i
        className="fas fa-file text-4xl mb-3"
        style={{ color: 'var(--theme-text-muted)', opacity: 0.5 }}
      ></i>
      <p className="text-sm mb-2" style={{ color: 'var(--theme-text)' }}>
        Preview not available for this file type.
      </p>
      <a
        href={`${getApiBaseUrl()}/api/v1/files/${fileId}/download`}
        className="inline-flex items-center gap-2 text-sm px-3 py-2 rounded transition-colors"
        style={{
          background: 'var(--theme-primary)',
          color: 'white',
        }}
        target="_blank"
        rel="noopener noreferrer"
        onMouseEnter={(e) => {
          e.currentTarget.style.opacity = '0.9';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.opacity = '1';
        }}
      >
        <i className="fas fa-download"></i>
        Download File
      </a>
    </div>
  );
}

/**
 * Main Media Viewer Component
 * 
 * Auto-detects media type and renders appropriate viewer.
 */
export function MediaViewerConfig({
  fileId,
  fileCategory,
  accept,
  height = '500px',
  className = '',
  onClick,
}: MediaViewerConfigProps) {
  if (!fileId) {
    return null;
  }

  const mediaType = detectMediaType(fileCategory, accept);

  return (
    <div className={`mt-3 ${className}`}>
      <div className="text-sm font-medium mb-2" style={{ color: 'var(--theme-text)' }}>
        {mediaType === 'document' && 'Document Preview:'}
        {mediaType === 'image' && 'Image Preview:'}
        {mediaType === 'video' && 'Video Preview:'}
        {mediaType === 'audio' && 'Audio Preview:'}
        {mediaType === 'unknown' && 'File Preview:'}
      </div>

      {mediaType === 'document' && <DocumentViewer fileId={fileId} height={height} onClick={onClick} />}
      {mediaType === 'image' && <ImageViewer fileId={fileId} height={height} onClick={onClick} />}
      {mediaType === 'video' && <VideoViewer fileId={fileId} height={height} />}
      {mediaType === 'audio' && <AudioViewer fileId={fileId} />}
      {mediaType === 'unknown' && <UnknownViewer fileId={fileId} />}
    </div>
  );
}

// Export individual viewers for custom use
export { DocumentViewer, ImageViewer, VideoViewer, AudioViewer, UnknownViewer };


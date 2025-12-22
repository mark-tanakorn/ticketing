/**
 * Media Output Viewer Component
 * 
 * Displays MediaFormat objects in the Output tab with rich previews.
 * Detects MediaFormat structure and renders appropriate viewer.
 */

import React from 'react';
import { getApiBaseUrl } from '@/lib/api-config';

export interface MediaFormat {
  type: 'image' | 'audio' | 'video' | 'document';
  format: string;
  data: string;
  data_type: 'base64' | 'url' | 'file_path';
  metadata?: Record<string, any>;
}

interface MediaOutputViewerProps {
  data: any;
  portName?: string;
  onMediaClick?: (mediaFormat: MediaFormat, index?: number) => void;
}

/**
 * Check if an object is MediaFormat
 */
function isMediaFormat(obj: any): boolean {
  if (!obj || typeof obj !== 'object') return false;
  
  return (
    typeof obj.type === 'string' &&
    typeof obj.format === 'string' &&
    typeof obj.data === 'string' &&
    typeof obj.data_type === 'string' &&
    ['image', 'audio', 'video', 'document'].includes(obj.type)
  );
}

/**
 * Extract file ID from MediaFormat data
 */
function getFileIdFromMediaFormat(mediaFormat: any): string | null {
  // Check metadata for file_id
  if (mediaFormat.metadata?.file_id) {
    return mediaFormat.metadata.file_id;
  }
  
  // If data_type is file_path, try to extract file ID from path
  if (mediaFormat.data_type === 'file_path') {
    // Path might be like "data/uploads/abc-123-def/file.pdf"
    // We need the file_id from metadata or path
    const path = mediaFormat.data;
    // Try to find UUID pattern
    const uuidMatch = path.match(/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i);
    if (uuidMatch) {
      return uuidMatch[1];
    }
  }
  
  return null;
}

/**
 * Render Document Preview
 */
function DocumentPreview({ mediaFormat, onClick }: { mediaFormat: any; onClick?: () => void }) {
  const fileId = getFileIdFromMediaFormat(mediaFormat);
  const filename = mediaFormat.metadata?.filename || 'document';
  
  if (!fileId) {
    return (
      <div className="text-sm p-3 rounded" style={{ background: 'var(--theme-surface-variant)', color: 'var(--theme-text-secondary)' }}>
        <i className="fas fa-file-pdf mr-2"></i>
        Document: {filename} (File ID not available for preview)
      </div>
    );
  }

  return (
    <div className="mt-2 relative">
      <div className="text-xs mb-2" style={{ color: 'var(--theme-text-secondary)' }}>
        <i className="fas fa-file-pdf mr-1"></i>
        {filename}
      </div>
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
          style={{ height: '400px' }}
        >
          <div className="p-4 text-center" style={{ color: 'var(--theme-text-secondary)' }}>
            <p className="text-sm">Document preview not available.</p>
            <a
              href={`${getApiBaseUrl()}/api/v1/files/${fileId}/download`}
              className="text-blue-500 underline text-sm"
              target="_blank"
              rel="noopener noreferrer"
            >
              Download document
            </a>
          </div>
        </object>
      </div>
      {/* Expand button overlay */}
      {onClick && (
        <button
          onClick={onClick}
          className="absolute top-8 right-2 p-2 rounded-lg transition-all"
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
 * Render Image Preview
 */
function ImagePreview({ mediaFormat, onClick }: { mediaFormat: any; onClick?: () => void }) {
  const fileId = getFileIdFromMediaFormat(mediaFormat);
  const filename = mediaFormat.metadata?.filename || 'image';
  const width = mediaFormat.metadata?.width;
  const height = mediaFormat.metadata?.height;

  if (!fileId) {
    return (
      <div className="text-sm p-3 rounded" style={{ background: 'var(--theme-surface-variant)', color: 'var(--theme-text-secondary)' }}>
        <i className="fas fa-image mr-2"></i>
        Image: {filename} {width && height && `(${width}x${height})`}
      </div>
    );
  }

  return (
    <div className="mt-2 relative">
      <div className="text-xs mb-2" style={{ color: 'var(--theme-text-secondary)' }}>
        <i className="fas fa-image mr-1"></i>
        {filename} {width && height && `(${width}x${height})`}
      </div>
      <div
        className="border rounded overflow-hidden flex items-center justify-center"
        style={{
          borderColor: 'var(--theme-border)',
          background: 'var(--theme-surface)',
          maxHeight: '400px',
        }}
      >
        <img
          src={`${getApiBaseUrl()}/api/v1/files/${fileId}/view`}
          alt={filename}
          className="max-w-full max-h-full object-contain"
          style={{ maxHeight: '400px' }}
        />
      </div>
      {/* Expand button overlay */}
      {onClick && (
        <button
          onClick={onClick}
          className="absolute top-8 right-2 p-2 rounded-lg transition-all"
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
 * Render Video Preview
 */
function VideoPreview({ mediaFormat }: { mediaFormat: any }) {
  const fileId = getFileIdFromMediaFormat(mediaFormat);
  const filename = mediaFormat.metadata?.filename || 'video';

  if (!fileId) {
    return (
      <div className="text-sm p-3 rounded" style={{ background: 'var(--theme-surface-variant)', color: 'var(--theme-text-secondary)' }}>
        <i className="fas fa-video mr-2"></i>
        Video: {filename}
      </div>
    );
  }

  return (
    <div className="mt-2">
      <div className="text-xs mb-2" style={{ color: 'var(--theme-text-secondary)' }}>
        <i className="fas fa-video mr-1"></i>
        {filename}
      </div>
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
          style={{ maxHeight: '400px' }}
        >
          <source src={`${getApiBaseUrl()}/api/v1/files/${fileId}/view`} />
        </video>
      </div>
    </div>
  );
}

/**
 * Render Audio Preview
 */
function AudioPreview({ mediaFormat }: { mediaFormat: any }) {
  const fileId = getFileIdFromMediaFormat(mediaFormat);
  const filename = mediaFormat.metadata?.filename || 'audio';

  if (!fileId) {
    return (
      <div className="text-sm p-3 rounded" style={{ background: 'var(--theme-surface-variant)', color: 'var(--theme-text-secondary)' }}>
        <i className="fas fa-music mr-2"></i>
        Audio: {filename}
      </div>
    );
  }

  return (
    <div className="mt-2">
      <div className="text-xs mb-2" style={{ color: 'var(--theme-text-secondary)' }}>
        <i className="fas fa-music mr-1"></i>
        {filename}
      </div>
      <div
        className="border rounded p-3"
        style={{
          borderColor: 'var(--theme-border)',
          background: 'var(--theme-surface)',
        }}
      >
        <audio controls className="w-full">
          <source src={`${getApiBaseUrl()}/api/v1/files/${fileId}/view`} />
        </audio>
      </div>
    </div>
  );
}

/**
 * Main Media Output Viewer Component
 */
export function MediaOutputViewer({ data, portName, onMediaClick }: MediaOutputViewerProps) {
  // Check if single MediaFormat object
  if (isMediaFormat(data)) {
    return (
      <div>
        {portName && (
          <div className="text-xs font-semibold mb-2" style={{ color: 'var(--theme-text-secondary)' }}>
            {portName}:
          </div>
        )}
        {data.type === 'document' && (
          <DocumentPreview 
            mediaFormat={data} 
            onClick={() => onMediaClick?.(data as MediaFormat)}
          />
        )}
        {data.type === 'image' && (
          <ImagePreview 
            mediaFormat={data}
            onClick={() => onMediaClick?.(data as MediaFormat)}
          />
        )}
        {data.type === 'video' && <VideoPreview mediaFormat={data} />}
        {data.type === 'audio' && <AudioPreview mediaFormat={data} />}
      </div>
    );
  }

  // Check if array of MediaFormat objects
  if (Array.isArray(data) && data.length > 0 && isMediaFormat(data[0])) {
    return (
      <div>
        {portName && (
          <div className="text-xs font-semibold mb-2" style={{ color: 'var(--theme-text-secondary)' }}>
            {portName} ({data.length} items):
          </div>
        )}
        <div className="space-y-3">
          {data.map((item, index) => (
            <div key={index}>
              <div className="text-xs mb-1" style={{ color: 'var(--theme-text-muted)' }}>
                Item {index + 1}:
              </div>
              {item.type === 'document' && (
                <DocumentPreview 
                  mediaFormat={item}
                  onClick={() => onMediaClick?.(item as MediaFormat, index)}
                />
              )}
              {item.type === 'image' && (
                <ImagePreview 
                  mediaFormat={item}
                  onClick={() => onMediaClick?.(item as MediaFormat, index)}
                />
              )}
              {item.type === 'video' && <VideoPreview mediaFormat={item} />}
              {item.type === 'audio' && <AudioPreview mediaFormat={item} />}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return null; // Not MediaFormat, let caller handle
}

/**
 * Helper to check if output contains any MediaFormat
 */
export function hasMediaFormat(data: any): boolean {
  if (isMediaFormat(data)) return true;
  
  if (Array.isArray(data) && data.length > 0 && isMediaFormat(data[0])) {
    return true;
  }
  
  if (typeof data === 'object' && data !== null) {
    return Object.values(data).some(value => hasMediaFormat(value));
  }
  
  return false;
}


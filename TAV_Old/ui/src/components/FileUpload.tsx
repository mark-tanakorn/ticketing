/**
 * File Upload Component
 * Drag-and-drop file uploader with progress tracking
 */

import React, { useState, useRef, useCallback } from 'react';
import { uploadFile, formatFileSize, isFileTypeAccepted, autoDetectFileCategory, type FileMetadata, type FileCategory } from '@/lib/files';

export interface FileUploadProps {
  accept?: string;
  maxSizeMB?: number;
  fileCategory?: FileCategory;
  workflowId?: string;
  multiple?: boolean;
  onUploadComplete?: (file: FileMetadata) => void;
  onUploadError?: (error: Error) => void;
  disabled?: boolean;
  className?: string;
}

interface UploadingFile {
  file: File;
  progress: number;
  error?: string;
}

export function FileUpload({
  accept,
  maxSizeMB = 100,
  fileCategory,
  workflowId,
  multiple = false,
  onUploadComplete,
  onUploadError,
  disabled = false,
  className = '',
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<Map<string, UploadingFile>>(new Map());
  const fileInputRef = useRef<HTMLInputElement>(null);

  const maxSizeBytes = maxSizeMB * 1024 * 1024;

  // Handle file selection/drop
  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;

      const filesToUpload = Array.from(files).slice(0, multiple ? files.length : 1);

      for (const file of filesToUpload) {
        // Validate file type
        if (accept && !isFileTypeAccepted(file.name, accept)) {
          const error = new Error(`File type not accepted: ${file.name}`);
          onUploadError?.(error);
          continue;
        }

        // Validate file size
        if (file.size > maxSizeBytes) {
          const error = new Error(`File too large: ${file.name} (max ${maxSizeMB}MB)`);
          onUploadError?.(error);
          continue;
        }

        // Add to uploading files
        const fileId = `${file.name}-${Date.now()}`;
        setUploadingFiles((prev) => {
          const newMap = new Map(prev);
          newMap.set(fileId, { file, progress: 0 });
          return newMap;
        });

        try {
          // Upload file
          const metadata = await uploadFile({
            file,
            fileType: 'upload',
            fileCategory: fileCategory || autoDetectFileCategory(file.name),
            workflowId,
            onProgress: (percent) => {
              setUploadingFiles((prev) => {
                const newMap = new Map(prev);
                const existing = newMap.get(fileId);
                if (existing) {
                  newMap.set(fileId, { ...existing, progress: percent });
                }
                return newMap;
              });
            },
          });

          // Remove from uploading files
          setUploadingFiles((prev) => {
            const newMap = new Map(prev);
            newMap.delete(fileId);
            return newMap;
          });

          // Notify parent
          onUploadComplete?.(metadata);
        } catch (error) {
          // Mark as error
          setUploadingFiles((prev) => {
            const newMap = new Map(prev);
            const existing = newMap.get(fileId);
            if (existing) {
              newMap.set(fileId, {
                ...existing,
                error: error instanceof Error ? error.message : 'Upload failed',
              });
            }
            return newMap;
          });

          onUploadError?.(error as Error);

          // Remove after delay
          setTimeout(() => {
            setUploadingFiles((prev) => {
              const newMap = new Map(prev);
              newMap.delete(fileId);
              return newMap;
            });
          }, 3000);
        }
      }
    },
    [accept, maxSizeBytes, maxSizeMB, multiple, fileCategory, workflowId, onUploadComplete, onUploadError]
  );

  // Handle drag events
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (!disabled) {
      handleFiles(e.dataTransfer.files);
    }
  };

  // Handle click to browse
  const handleClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  };

  const uploadingArray = Array.from(uploadingFiles.values());
  const hasUploading = uploadingArray.length > 0;

  return (
    <div className={`file-upload ${className}`}>
      {/* Drop zone */}
      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleClick}
        style={{
          border: `2px dashed ${isDragging ? 'var(--theme-primary)' : 'var(--theme-border)'}`,
          borderRadius: '8px',
          padding: '24px',
          textAlign: 'center',
          cursor: disabled ? 'not-allowed' : 'pointer',
          background: isDragging
            ? 'rgba(var(--theme-primary-rgb), 0.05)'
            : 'var(--theme-surface-variant)',
          transition: 'all 0.2s ease',
          opacity: disabled ? 0.6 : 1,
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '12px', opacity: 0.5 }}>📁</div>
        <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '8px', color: 'var(--theme-text)' }}>
          {isDragging ? 'Drop files here' : 'Drag & drop files here'}
        </div>
        <div style={{ fontSize: '12px', color: 'var(--theme-text-secondary)' }}>
          or click to browse
        </div>
        {accept && (
          <div style={{ fontSize: '11px', color: 'var(--theme-text-secondary)', marginTop: '8px' }}>
            Accepted: {accept}
          </div>
        )}
        {maxSizeMB && (
          <div style={{ fontSize: '11px', color: 'var(--theme-text-secondary)' }}>
            Max size: {maxSizeMB}MB
          </div>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
        disabled={disabled}
      />

      {/* Upload progress */}
      {hasUploading && (
        <div style={{ marginTop: '16px' }}>
          {uploadingArray.map((item, index) => (
            <div
              key={index}
              style={{
                padding: '12px',
                marginBottom: '8px',
                borderRadius: '6px',
                background: 'var(--theme-surface-variant)',
                border: `1px solid ${item.error ? '#ef4444' : 'var(--theme-border)'}`,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px',
                }}
              >
                <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--theme-text)' }}>
                  {item.file.name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--theme-text-secondary)' }}>
                  {formatFileSize(item.file.size)}
                </div>
              </div>

              {item.error ? (
                <div style={{ fontSize: '12px', color: '#ef4444' }}>❌ {item.error}</div>
              ) : (
                <>
                  <div
                    style={{
                      height: '4px',
                      background: 'var(--theme-border)',
                      borderRadius: '2px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        background: 'var(--theme-primary)',
                        width: `${item.progress}%`,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--theme-text-secondary)', marginTop: '4px' }}>
                    {Math.round(item.progress)}%
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .drop-zone:hover:not(.disabled) {
          border-color: var(--theme-primary);
          background: rgba(var(--theme-primary-rgb), 0.03);
        }
      `}</style>
    </div>
  );
}


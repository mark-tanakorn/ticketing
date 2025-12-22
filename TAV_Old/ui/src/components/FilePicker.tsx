/**
 * File Picker Component
 * File selection dialog with upload capability
 */

import React, { useState, useEffect } from 'react';
import { FileUpload } from './FileUpload';
import {
  listFiles,
  getFileDownloadUrl,
  deleteFile,
  formatFileSize,
  type FileMetadata,
  type FileCategory,
} from '@/lib/files';

export interface FilePickerProps {
  value?: string; // Selected file ID
  onChange: (fileId: string | null, file: FileMetadata | null) => void;
  accept?: string;
  maxSizeMB?: number;
  fileCategory?: FileCategory;
  workflowId?: string;
  disabled?: boolean;
  placeholder?: string;
}

export function FilePicker({
  value,
  onChange,
  accept,
  maxSizeMB,
  fileCategory,
  workflowId,
  disabled = false,
  placeholder = 'Select or upload a file',
}: FilePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileMetadata | null>(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<'list' | 'upload'>('list');

  // Load files when opened
  useEffect(() => {
    if (isOpen) {
      loadFiles();
    }
  }, [isOpen, fileCategory]);

  // Load selected file metadata when value changes
  useEffect(() => {
    if (value) {
      loadSelectedFile(value);
    } else {
      setSelectedFile(null);
    }
  }, [value]);

  const loadFiles = async () => {
    setLoading(true);
    try {
      const response = await listFiles({
        fileCategory,
        workflowId,
        limit: 100,
      });
      setFiles(response.files);
    } catch (error) {
      console.error('Failed to load files:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSelectedFile = async (fileId: string) => {
    try {
      // First check if we already have it in the loaded files
      const existingFile = files.find((f) => f.id === fileId);
      if (existingFile) {
        setSelectedFile(existingFile);
        return;
      }

      // If not in list yet, fetch all files to find it
      const response = await listFiles({
        fileCategory,
        workflowId,
        limit: 100,
      });
      
      const file = response.files.find((f) => f.id === fileId);
      if (file) {
        setSelectedFile(file);
        // Also update files list for when modal opens
        setFiles(response.files);
      } else {
        // File no longer exists (maybe wiped on restart)
        console.warn(`File ${fileId} not found in storage`);
        setSelectedFile(null);
      }
    } catch (error) {
      console.error('Failed to load selected file:', error);
      setSelectedFile(null);
    }
  };

  const handleSelect = (file: FileMetadata) => {
    setSelectedFile(file);
    onChange(file.id, file);
    setIsOpen(false);
  };

  const handleUploadComplete = (file: FileMetadata) => {
    setFiles((prev) => [file, ...prev]);
    setSelectedFile(file);
    onChange(file.id, file);
    setView('list');
  };

  const handleDelete = async (fileId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this file?')) return;

    try {
      await deleteFile(fileId);
      setFiles((prev) => prev.filter((f) => f.id !== fileId));
      if (selectedFile?.id === fileId) {
        setSelectedFile(null);
        onChange(null, null);
      }
    } catch (error) {
      console.error('Failed to delete file:', error);
      alert('Failed to delete file');
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    onChange(null, null);
  };

  return (
    <div className="file-picker">
      {/* Selected file display / trigger button */}
      <div
        onClick={() => !disabled && setIsOpen(true)}
        style={{
          padding: '8px 12px',
          border: '1px solid var(--theme-border)',
          borderRadius: '6px',
          background: disabled ? 'var(--theme-surface)' : 'var(--theme-surface-variant)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          opacity: disabled ? 0.6 : 1,
        }}
      >
        <div style={{ fontSize: '13px', color: 'var(--theme-text)', flex: 1 }}>
          {selectedFile ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📄</span>
              <span>{selectedFile.filename}</span>
              <span style={{ color: 'var(--theme-text-secondary)', fontSize: '11px' }}>
                ({formatFileSize(selectedFile.file_size_bytes)})
              </span>
            </div>
          ) : (
            <span style={{ color: 'var(--theme-text-secondary)' }}>{placeholder}</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          {selectedFile && !disabled && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleClear();
              }}
              style={{
                padding: '4px 8px',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--theme-text-secondary)',
                fontSize: '12px',
              }}
              title="Clear selection"
            >
              ✕
            </button>
          )}
          {!disabled && (
            <span style={{ color: 'var(--theme-text-secondary)', fontSize: '12px' }}>▼</span>
          )}
        </div>
      </div>

      {/* File picker modal */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000,
          }}
          onClick={() => setIsOpen(false)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'var(--theme-surface)',
              borderRadius: '12px',
              width: '90%',
              maxWidth: '600px',
              maxHeight: '60vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
            }}
          >
            {/* Header */}
            <div
              style={{
                padding: '16px 20px',
                borderBottom: '1px solid var(--theme-border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => setView('list')}
                  style={{
                    padding: '6px 12px',
                    background: view === 'list' ? 'var(--theme-primary)' : 'transparent',
                    color: view === 'list' ? 'white' : 'var(--theme-text)',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '13px',
                  }}
                >
                  📁 Browse Files
                </button>
                <button
                  onClick={() => setView('upload')}
                  style={{
                    padding: '6px 12px',
                    background: view === 'upload' ? 'var(--theme-primary)' : 'transparent',
                    color: view === 'upload' ? 'white' : 'var(--theme-text)',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '13px',
                  }}
                >
                  ⬆️ Upload New
                </button>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  padding: '6px 12px',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--theme-text-secondary)',
                  fontSize: '18px',
                }}
              >
                ✕
              </button>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
              {view === 'list' ? (
                <div>
                  {loading ? (
                    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--theme-text-secondary)' }}>
                      Loading files...
                    </div>
                  ) : files.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--theme-text-secondary)' }}>
                      No files found. Upload one to get started.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {files.map((file) => (
                        <div
                          key={file.id}
                          onClick={() => handleSelect(file)}
                          style={{
                            padding: '12px',
                            border: `1px solid ${
                              selectedFile?.id === file.id ? 'var(--theme-primary)' : 'var(--theme-border)'
                            }`,
                            borderRadius: '8px',
                            background:
                              selectedFile?.id === file.id
                                ? 'rgba(var(--theme-primary-rgb), 0.1)'
                                : 'var(--theme-surface-variant)',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <div style={{ flex: 1 }}>
                            <div
                              style={{
                                fontSize: '13px',
                                fontWeight: 500,
                                color: 'var(--theme-text)',
                                marginBottom: '4px',
                              }}
                            >
                              📄 {file.filename}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--theme-text-secondary)' }}>
                              {formatFileSize(file.file_size_bytes)} •{' '}
                              {new Date(file.uploaded_at).toLocaleDateString()}
                            </div>
                          </div>
                          <button
                            onClick={(e) => handleDelete(file.id, e)}
                            style={{
                              padding: '4px 8px',
                              background: 'transparent',
                              border: 'none',
                              cursor: 'pointer',
                              color: '#ef4444',
                              fontSize: '16px',
                            }}
                            title="Delete file"
                          >
                            🗑️
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <FileUpload
                  accept={accept}
                  maxSizeMB={maxSizeMB}
                  fileCategory={fileCategory}
                  workflowId={workflowId}
                  onUploadComplete={handleUploadComplete}
                  onUploadError={(error) => {
                    console.error('Upload error:', error);
                    alert(error.message);
                  }}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


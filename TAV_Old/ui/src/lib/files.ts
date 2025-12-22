/**
 * File Management API
 * Handles file uploads, downloads, and management
 */

import { getApiBaseUrl } from './api-config';
import { apiFetch } from './api';
import { getAuthToken } from './auth';

// ===== TYPES =====

export interface FileMetadata {
  id: string;
  filename: string;
  file_size_bytes: number;
  mime_type: string;
  file_type: 'upload' | 'artifact' | 'temporary' | 'permanent';
  file_category: 'document' | 'image' | 'audio' | 'video' | 'archive' | 'other';
  storage_path: string;
  uploaded_at: string;
  expires_at: string | null;
  access_count: number;
  workflow_id: string | null;
  download_url: string;
}

export interface FileListResponse {
  files: FileMetadata[];
  total: number;
}

export interface StorageStatsResponse {
  by_type: Record<string, { count: number; total_bytes: number }>;
  total_files: number;
  total_bytes: number;
  total_mb: number;
  total_gb: number;
}

export type FileCategory = 'document' | 'image' | 'audio' | 'video' | 'archive' | 'other';

// ===== FILE UPLOAD =====

export interface UploadFileOptions {
  file: File;
  fileType?: 'upload' | 'artifact' | 'temporary' | 'permanent';
  fileCategory?: FileCategory;
  workflowId?: string;
  executionId?: string;
  makePermanent?: boolean;
  onProgress?: (percent: number) => void;
}

/**
 * Upload a file to the server
 */
export async function uploadFile(options: UploadFileOptions): Promise<FileMetadata> {
  const {
    file,
    fileType = 'upload',
    fileCategory,
    workflowId,
    executionId,
    makePermanent = false,
    onProgress,
  } = options;

  const formData = new FormData();
  formData.append('file', file);

  // Build query parameters
  const params = new URLSearchParams();
  params.append('file_type', fileType);
  if (fileCategory) params.append('file_category', fileCategory);
  if (workflowId) params.append('workflow_id', workflowId);
  if (executionId) params.append('execution_id', executionId);
  if (makePermanent) params.append('make_permanent', 'true');

  const url = `${getApiBaseUrl()}/api/v1/files/upload?${params.toString()}`;

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Track upload progress
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percentComplete = (e.loaded / e.total) * 100;
        onProgress(percentComplete);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve(data);
        } catch (error) {
          reject(new Error('Failed to parse response'));
        }
      } else {
        try {
          const error = JSON.parse(xhr.responseText);
          reject(new Error(error.detail || `Upload failed: ${xhr.statusText}`));
        } catch {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Network error'));
    });

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload cancelled'));
    });

    xhr.open('POST', url);
    
    // Add authentication header
    const token = getAuthToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }
    
    xhr.send(formData);
  });
}

// ===== FILE RETRIEVAL =====

/**
 * Get file metadata by ID
 */
export async function getFileMetadata(fileId: string): Promise<FileMetadata> {
  return await apiFetch<FileMetadata>(`${getApiBaseUrl()}/api/v1/files/${fileId}`);
}

/**
 * List uploaded files with optional filtering
 */
export async function listFiles(options?: {
  fileType?: string;
  fileCategory?: FileCategory;
  workflowId?: string;
  limit?: number;
  offset?: number;
}): Promise<FileListResponse> {
  const params = new URLSearchParams();
  if (options?.fileType) params.append('file_type', options.fileType);
  if (options?.fileCategory) params.append('file_category', options.fileCategory);
  if (options?.workflowId) params.append('workflow_id', options.workflowId);
  if (options?.limit) params.append('limit', options.limit.toString());
  if (options?.offset) params.append('offset', options.offset.toString());

  const url = `${getApiBaseUrl()}/api/v1/files?${params.toString()}`;
  return await apiFetch<FileListResponse>(url);
}

/**
 * Get file download URL
 */
export function getFileDownloadUrl(fileId: string): string {
  return `${getApiBaseUrl()}/api/v1/files/${fileId}/download`;
}

/**
 * Download a file (triggers browser download)
 */
export async function downloadFile(fileId: string, filename?: string): Promise<void> {
  const url = getFileDownloadUrl(fileId);
  const link = document.createElement('a');
  link.href = url;
  if (filename) {
    link.download = filename;
  }
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// ===== FILE MANAGEMENT =====

/**
 * Delete a file
 */
export async function deleteFile(fileId: string): Promise<void> {
  await apiFetch<void>(`${getApiBaseUrl()}/api/v1/files/${fileId}`, {
    method: 'DELETE',
  });
}

/**
 * Get storage statistics
 */
export async function getStorageStats(): Promise<StorageStatsResponse> {
  return await apiFetch<StorageStatsResponse>(`${getApiBaseUrl()}/api/v1/files/stats/storage`);
}

/**
 * Trigger cleanup job (admin)
 */
export async function triggerCleanup(): Promise<any> {
  return await apiFetch<any>(`${getApiBaseUrl()}/api/v1/files/cleanup`, {
    method: 'POST',
  });
}

// ===== HELPER FUNCTIONS =====

/**
 * Format file size in human-readable format
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Get file extension from filename
 */
export function getFileExtension(filename: string): string {
  const parts = filename.split('.');
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
}

/**
 * Check if file type is accepted
 */
export function isFileTypeAccepted(filename: string, accept: string): boolean {
  if (!accept || accept === '*') return true;

  const ext = '.' + getFileExtension(filename);
  const acceptedTypes = accept.split(',').map((t) => t.trim().toLowerCase());

  return acceptedTypes.some((type) => {
    if (type === ext) return true;
    // Handle wildcard MIME types (e.g., "image/*")
    if (type.includes('/*')) {
      const category = type.split('/')[0];
      const mimeCategory = getMimeCategory(filename);
      return category === mimeCategory;
    }
    return false;
  });
}

/**
 * Get MIME category from filename
 */
function getMimeCategory(filename: string): string {
  const ext = getFileExtension(filename);
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff'];
  const audioExts = ['mp3', 'wav', 'm4a', 'ogg', 'flac', 'webm'];
  const videoExts = ['mp4', 'avi', 'mov', 'mkv', 'webm'];

  if (imageExts.includes(ext)) return 'image';
  if (audioExts.includes(ext)) return 'audio';
  if (videoExts.includes(ext)) return 'video';
  return 'application';
}

/**
 * Auto-detect file category from filename
 */
export function autoDetectFileCategory(filename: string): FileCategory {
  const ext = getFileExtension(filename);

  // Document extensions
  if (['pdf', 'doc', 'docx', 'txt', 'md', 'csv', 'json', 'xlsx', 'xls', 'xlsm'].includes(ext)) {
    return 'document';
  }

  // Image extensions
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff'].includes(ext)) {
    return 'image';
  }

  // Audio extensions
  if (['mp3', 'wav', 'm4a', 'ogg', 'flac', 'webm'].includes(ext)) {
    return 'audio';
  }

  // Video extensions
  if (['mp4', 'avi', 'mov', 'mkv', 'webm'].includes(ext)) {
    return 'video';
  }

  // Archive extensions
  if (['zip', 'tar', 'gz', 'rar', '7z'].includes(ext)) {
    return 'archive';
  }

  return 'other';
}


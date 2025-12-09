/**
 * Media Full Screen Modal
 * 
 * Full-screen modal for viewing and editing media (images, PDFs).
 * 
 * Modes:
 * - 'view': Read-only viewing with zoom/pan
 * - 'edit': Annotation mode with drawing tools (freehand, highlighter, text)
 * 
 * Features:
 * - ESC to close
 * - Click backdrop to close
 * - Navigation for arrays of media
 * - Download button
 * - Annotation saving (edit mode)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { ImageAnnotationEditor, ImageAnnotationEditorRef } from './ImageAnnotationEditor';
import { DocumentAnnotationEditor } from './DocumentAnnotationEditor';

export interface MediaFormat {
  type: 'image' | 'audio' | 'video' | 'document';
  format: string;
  data: string;
  data_type: 'base64' | 'url' | 'file_path';
  metadata?: Record<string, any>;
}

export interface Annotation {
  id: string;
  type: 'freehand' | 'highlight' | 'text' | 'rectangle';
  color: string;
  data: any; // Fabric.js object data
  bounds?: { x: number; y: number; width: number; height: number };
  label?: string; // For AI processing
  instruction?: string; // For AI processing
}

export interface AnnotationData {
  page?: number;
  annotations: Annotation[];
}

interface MediaFullScreenModalProps {
  isOpen: boolean;
  onClose: () => void;
  mediaData: MediaFormat | MediaFormat[];
  mode: 'view' | 'edit';
  initialIndex?: number;
  existingAnnotations?: AnnotationData[];
  onSave?: (annotations: AnnotationData[]) => void;
}

export function MediaFullScreenModal({
  isOpen,
  onClose,
  mediaData,
  mode,
  initialIndex = 0,
  existingAnnotations = [],
  onSave,
}: MediaFullScreenModalProps) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [annotations, setAnnotations] = useState<AnnotationData[]>(existingAnnotations);
  
  const imageEditorRef = React.useRef<ImageAnnotationEditorRef>(null);
  
  const mediaArray = Array.isArray(mediaData) ? mediaData : [mediaData];
  const currentMedia = mediaArray[currentIndex];
  const hasMultiple = mediaArray.length > 1;

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setCurrentIndex(initialIndex);
      setAnnotations(existingAnnotations);
    }
  }, [isOpen]); // Only depend on isOpen to avoid infinite loops

  // ESC key to close
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handlePrevious = useCallback(() => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : mediaArray.length - 1));
  }, [mediaArray.length]);

  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => (prev < mediaArray.length - 1 ? prev + 1 : 0));
  }, [mediaArray.length]);

  const handleSave = useCallback(() => {
    if (onSave) {
      // If it's an image, we might want to save the annotated file
      if (currentMedia.type === 'image' && imageEditorRef.current) {
        const dataUrl = imageEditorRef.current.getAnnotatedDataURL();
        console.log('Generated annotated image data URL (length):', dataUrl.length);
        // Ideally we would pass this back too, but for now we save the annotations
        // You could extend the onSave callback to accept the file data
      }
      
      onSave(annotations);
    }
    onClose();
  }, [annotations, onSave, onClose, currentMedia.type]);

  const handleAnnotationsChange = useCallback((newAnnotations: Annotation[]) => {
    setAnnotations((prev) => {
      const updated = [...prev];
      updated[currentIndex] = {
        page: currentIndex + 1,
        annotations: newAnnotations,
      };
      return updated;
    });
  }, [currentIndex]);

  if (!isOpen) return null;

  const modalContent = (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center"
      style={{ background: 'rgba(0, 0, 0, 0.95)' }}
      onClick={(e) => {
        // Close on backdrop click
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      {/* Close Button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 z-10 p-3 rounded-full transition-colors"
        style={{
          background: 'rgba(255, 255, 255, 0.1)',
          color: 'white',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
        }}
        title="Close (ESC)"
      >
        <i className="fas fa-times text-xl"></i>
      </button>

      {/* Navigation - Previous */}
      {hasMultiple && (
        <button
          onClick={handlePrevious}
          className="absolute left-4 top-1/2 -translate-y-1/2 z-10 p-3 rounded-full transition-colors"
          style={{
            background: 'rgba(255, 255, 255, 0.1)',
            color: 'white',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
          }}
          title="Previous"
        >
          <i className="fas fa-chevron-left text-xl"></i>
        </button>
      )}

      {/* Navigation - Next */}
      {hasMultiple && (
        <button
          onClick={handleNext}
          className="absolute right-4 top-1/2 -translate-y-1/2 z-10 p-3 rounded-full transition-colors"
          style={{
            background: 'rgba(255, 255, 255, 0.1)',
            color: 'white',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
          }}
          title="Next"
        >
          <i className="fas fa-chevron-right text-xl"></i>
        </button>
      )}

      {/* Counter */}
      {hasMultiple && (
        <div
          className="absolute top-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full text-sm"
          style={{
            background: 'rgba(255, 255, 255, 0.1)',
            color: 'white',
          }}
        >
          {currentIndex + 1} / {mediaArray.length}
        </div>
      )}

      {/* Save Button (Edit Mode) */}
      {mode === 'edit' && (
        <button
          onClick={handleSave}
          className="absolute bottom-4 right-4 z-10 px-6 py-3 rounded-lg transition-colors font-medium"
          style={{
            background: 'var(--theme-primary)',
            color: 'white',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = '0.9';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = '1';
          }}
        >
          <i className="fas fa-save mr-2"></i>
          Save Annotations
        </button>
      )}

      {/* Media Content */}
      <div className="w-full h-full flex items-center justify-center p-8">
        {currentMedia.type === 'image' ? (
          <ImageAnnotationEditor
            ref={imageEditorRef}
            mediaFormat={currentMedia}
            mode={mode}
            annotations={annotations[currentIndex]?.annotations || []}
            onAnnotationsChange={handleAnnotationsChange}
          />
        ) : currentMedia.type === 'document' ? (
          <DocumentAnnotationEditor
            mediaFormat={currentMedia}
            mode={mode}
            annotations={annotations[currentIndex]?.annotations || []}
            onAnnotationsChange={handleAnnotationsChange}
          />
        ) : (
          <div className="text-white text-center">
            <p className="text-lg mb-2">Unsupported media type: {currentMedia.type}</p>
            <p className="text-sm opacity-75">Only images and documents are supported for now</p>
          </div>
        )}
      </div>
    </div>
  );

  // Use portal to render at document body level
  return createPortal(modalContent, document.body);
}


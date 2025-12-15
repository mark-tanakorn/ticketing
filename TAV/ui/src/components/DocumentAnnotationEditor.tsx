/**
 * Document Annotation Editor Component
 * 
 * Uses @react-pdf-viewer/core for PDF rendering with Fabric.js overlay for annotations.
 * Properly handles Next.js SSR.
 */

'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import dynamic from 'next/dynamic';
import fabric from 'fabric';
import { getApiBaseUrl } from '@/lib/api-config';
import type { MediaFormat, Annotation } from './MediaFullScreenModal';

// Import PDF viewer styles
import '@react-pdf-viewer/core/lib/styles/index.css';

// Dynamically import PDF viewer components with SSR disabled
const Viewer = dynamic(
  () => import('@react-pdf-viewer/core').then((mod) => mod.Viewer),
  { ssr: false }
);

const Worker = dynamic(
  () => import('@react-pdf-viewer/core').then((mod) => mod.Worker),
  { ssr: false }
);

interface DocumentAnnotationEditorProps {
  mediaFormat: MediaFormat;
  mode: 'view' | 'edit';
  annotations: Annotation[];
  onAnnotationsChange: (annotations: Annotation[]) => void;
}

type DrawingTool = 'select' | 'pen' | 'highlighter' | 'text' | 'rectangle';

function DocumentAnnotationEditorComponent({
  mediaFormat,
  mode,
  annotations,
  onAnnotationsChange,
}: DocumentAnnotationEditorProps) {
  const [activeTool, setActiveTool] = useState<DrawingTool>('select');
  const [drawingColor, setDrawingColor] = useState('#FF0000');
  const [isClient, setIsClient] = useState(false);
  const [canvasReady, setCanvasReady] = useState(false);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fabricCanvasRef = useRef<fabric.Canvas | null>(null);
  const viewerContainerRef = useRef<HTMLDivElement>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  const [pdfContentContainer, setPdfContentContainer] = useState<HTMLElement | null>(null);

  // Ensure we're on client side
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Get file ID from MediaFormat
  const getFileId = () => {
    if (mediaFormat.metadata?.file_id) {
      return mediaFormat.metadata.file_id;
    }
    
    if (mediaFormat.data_type === 'file_path') {
      const path = mediaFormat.data;
      const uuidMatch = path.match(/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i);
      if (uuidMatch) {
        return uuidMatch[1];
      }
      if (path && path.match(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i)) {
        return path;
      }
    }
    
    return null;
  };

  const fileId = getFileId();
  const pdfUrl = fileId ? `${getApiBaseUrl()}/api/v1/files/${fileId}/view` : null;

  // Find the PDF viewer content container
  useEffect(() => {
    if (!isClient || !viewerContainerRef.current) return;

    const findContainer = () => {
      const container = viewerContainerRef.current?.querySelector('.rpv-core__inner-pages');
      if (container) {
        console.log('Found PDF content container');
        (container as HTMLElement).style.position = 'relative';
        setPdfContentContainer(container as HTMLElement);
        return true;
      }
      return false;
    };

    // Try immediately
    if (findContainer()) return;

    // Retry loop for when PDF loads
    const interval = setInterval(() => {
      if (findContainer()) {
        clearInterval(interval);
      }
    }, 500);

    // Stop searching after 10 seconds
    const timeout = setTimeout(() => {
      clearInterval(interval);
    }, 10000);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [isClient, pdfUrl]); // Re-run if PDF URL changes

  // Initialize Fabric.js canvas overlay
  useEffect(() => {
    if (!canvasRef.current || !pdfContentContainer || !isClient) {
      return;
    }

    // Initialize canvas
    const targetElement = pdfContentContainer;
    const containerRect = targetElement.getBoundingClientRect();
    const width = containerRect.width;
    const height = containerRect.height;

    console.log('Initializing canvas with dimensions:', width, 'x', height);

    // Ensure we have valid dimensions
    if (width === 0 || height === 0) {
      console.warn('Container has zero dimensions, waiting for resize...');
    }

    const canvas = new fabric.Canvas(canvasRef.current, {
      width: width || 100, // Fallback to avoid error
      height: height || 100,
      backgroundColor: 'transparent',
      selection: mode === 'edit' && activeTool === 'select',
      isDrawingMode: false,
    });

    const wrapperEl = canvas.wrapperEl as HTMLDivElement | null;
    if (wrapperEl) {
      // We no longer need to manually position the wrapper since it's inside our portal div
      // but we do need to ensure it takes up full space
      Object.assign(wrapperEl.style, {
        width: '100%',
        height: '100%',
      });
    }

    canvas.lowerCanvasEl.style.pointerEvents = 'none';
    canvas.upperCanvasEl.style.pointerEvents = 'all';
    canvas.upperCanvasEl.style.touchAction = 'auto';
    canvas.upperCanvasEl.style.zIndex = '10';

    fabricCanvasRef.current = canvas;
    setCanvasReady(true);

    // DEBUG: Test if canvas receives events
    canvas.on('mouse:down', (e) => console.log('🖱️ Canvas click detected at', e.pointer));
    canvas.on('path:created', () => console.log('✏️ Drawing created!'));

    // Load existing annotations
    if (annotations && annotations.length > 0) {
      console.log('Loading annotations:', annotations.length);
      annotations.forEach((annotation) => {
        if (annotation.data) {
          fabric.util.enlivenObjects([annotation.data]).then((objects: any[]) => {
            objects.forEach((obj: any) => {
              canvas.add(obj as fabric.Object);
            });
            canvas.renderAll();
          });
        }
      });
    }

    // Handle resize (window resize or PDF zoom/content change)
    const resizeObserver = new ResizeObserver((entries) => {
      // Wrap in requestAnimationFrame to avoid "ResizeObserver loop limit exceeded"
      window.requestAnimationFrame(() => {
        if (!canvas || !canvas.getElement()) return;

        for (const entry of entries) {
          // Use getBoundingClientRect to get the actual rendered dimensions (including zoom)
          const rect = entry.target.getBoundingClientRect();
          
          // Only update if dimensions changed significantly
          if (Math.abs(rect.width - (canvas.width || 0)) > 1 || 
              Math.abs(rect.height - (canvas.height || 0)) > 1) {
            
            console.log('Resizing canvas to match content:', rect.width, 'x', rect.height);
            canvas.setDimensions({
              width: rect.width,
              height: rect.height,
            });
            canvas.renderAll();
          }
        }
      });
    });

    // Observe the content element
    resizeObserver.observe(targetElement);

    return () => {
      resizeObserver.disconnect();
      if (fabricCanvasRef.current) {
        fabricCanvasRef.current.dispose();
        fabricCanvasRef.current = null;
        setCanvasReady(false);
      }
    };
  }, [isClient, mode, pdfContentContainer]); // Re-init if container changes (unlikely) or mode changes

  // Handle tool changes

  // Handle tool changes
  useEffect(() => {
    const canvas = fabricCanvasRef.current;
    if (!canvas || !canvasReady) {
      console.log('No canvas for tool change, canvasReady:', canvasReady);
      return;
    }

    console.log('Tool changed to:', activeTool);

    canvas.isDrawingMode = false;
    canvas.selection = false;

    if (mode === 'view') {
      canvas.selection = false;
      canvas.isDrawingMode = false;
    } else {
      switch (activeTool) {
        case 'select':
          canvas.selection = true;
          console.log('Selection mode enabled');
          break;

        case 'pen':
          canvas.isDrawingMode = true;
          canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
          canvas.freeDrawingBrush.color = drawingColor;
          canvas.freeDrawingBrush.width = 3;
          console.log('Pen mode enabled, color:', drawingColor);
          break;

        case 'highlighter':
          canvas.isDrawingMode = true;
          canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
          const hexColor = drawingColor;
          const r = parseInt(hexColor.slice(1, 3), 16);
          const g = parseInt(hexColor.slice(3, 5), 16);
          const b = parseInt(hexColor.slice(5, 7), 16);
          canvas.freeDrawingBrush.color = `rgba(${r}, ${g}, ${b}, 0.3)`;
          canvas.freeDrawingBrush.width = 20;
          console.log('Highlighter mode enabled');
          break;

        case 'text':
          canvas.selection = false;
          console.log('Text mode enabled');
          break;

        case 'rectangle':
          canvas.selection = false;
          console.log('Rectangle mode enabled');
          break;
      }
    }

    const upperCanvas = canvas.upperCanvasEl;
    if (upperCanvas) {
      if (mode === 'view') {
        upperCanvas.style.pointerEvents = 'none';
      } else {
        // Only enable pointer events when actively using a drawing tool
        // In select mode, allow events to pass through for PDF scrolling
        upperCanvas.style.pointerEvents = activeTool === 'select' ? 'none' : 'all';
        upperCanvas.style.cursor = activeTool === 'select' ? 'default' : 'crosshair';
      }
    }
  }, [activeTool, drawingColor, mode, canvasReady]);

  // Allow scrolling the PDF while canvas overlay is active
  useEffect(() => {
    const canvas = fabricCanvasRef.current;
    const viewerEl = viewerContainerRef.current;
    if (!canvas || !viewerEl || !canvasReady) {
      return;
    }

    const wrapperEl = canvas.wrapperEl as HTMLDivElement | null;
    if (!wrapperEl) {
      return;
    }

    // Make wrapper allow pointer events to pass through when not drawing
    const needsPointerEvents = mode === 'edit' && activeTool !== 'select';
    wrapperEl.style.pointerEvents = needsPointerEvents ? 'auto' : 'none';
    
    // No need for custom wheel handler - let events pass through naturally
  }, [canvasReady, mode, activeTool]);

  // Handle object creation (save annotations)
  useEffect(() => {
    const canvas = fabricCanvasRef.current;
    if (!canvas || mode === 'view' || !canvasReady) return;

    const handleObjectAdded = () => {
      const objects = canvas.getObjects();
      const newAnnotations: Annotation[] = objects.map((obj: fabric.Object, index: number) => ({
        id: `annotation-${index}`,
        type: obj.type === 'path' ? (activeTool === 'highlighter' ? 'highlight' : 'freehand') : 'rectangle',
        color: drawingColor,
        data: obj.toJSON(),
        bounds: {
          x: obj.left || 0,
          y: obj.top || 0,
          width: obj.width || 0,
          height: obj.height || 0,
        },
      }));
      
      onAnnotationsChange(newAnnotations);
    };

    canvas.on('path:created', handleObjectAdded);
    canvas.on('object:added', handleObjectAdded);
    canvas.on('object:modified', handleObjectAdded);
    canvas.on('object:removed', handleObjectAdded);

    return () => {
      canvas.off('path:created', handleObjectAdded);
      canvas.off('object:added', handleObjectAdded);
      canvas.off('object:modified', handleObjectAdded);
      canvas.off('object:removed', handleObjectAdded);
    };
  }, [mode, activeTool, drawingColor, onAnnotationsChange, canvasReady]);

  // Handle text and rectangle tools
  useEffect(() => {
    const canvas = fabricCanvasRef.current;
    if (!canvas || mode === 'view' || !canvasReady) return;
    
    if (activeTool === 'text') {
      const handleTextClick = (e: fabric.TEvent) => {
        const evt = e as any;
        if (!evt.pointer) return;

        const text = new fabric.IText('Click to edit', {
          left: evt.pointer.x,
          top: evt.pointer.y,
          fill: drawingColor,
          fontSize: 20,
          fontFamily: 'Arial',
        });

        canvas.add(text);
        canvas.setActiveObject(text);
        text.enterEditing();
        canvas.renderAll();
      };

      canvas.on('mouse:down', handleTextClick);
      return () => {
        canvas.off('mouse:down', handleTextClick);
      };
    }

    if (activeTool === 'rectangle') {
      let isDrawing = false;
      let startX = 0;
      let startY = 0;
      let rect: fabric.Rect | null = null;

      const handleMouseDown = (e: fabric.TEvent) => {
        const evt = e as any;
        if (!evt.pointer) return;

        isDrawing = true;
        startX = evt.pointer.x;
        startY = evt.pointer.y;

        rect = new fabric.Rect({
          left: startX,
          top: startY,
          width: 0,
          height: 0,
          fill: 'transparent',
          stroke: drawingColor,
          strokeWidth: 3,
        });

        canvas.add(rect);
      };

      const handleMouseMove = (e: fabric.TEvent) => {
        if (!isDrawing || !rect) return;
        const evt = e as any;
        if (!evt.pointer) return;

        const width = evt.pointer.x - startX;
        const height = evt.pointer.y - startY;

        rect.set({
          width: Math.abs(width),
          height: Math.abs(height),
          left: width < 0 ? evt.pointer.x : startX,
          top: height < 0 ? evt.pointer.y : startY,
        });

        canvas.renderAll();
      };

      const handleMouseUp = () => {
        isDrawing = false;
        rect = null;
      };

      canvas.on('mouse:down', handleMouseDown);
      canvas.on('mouse:move', handleMouseMove);
      canvas.on('mouse:up', handleMouseUp);

      return () => {
        canvas.off('mouse:down', handleMouseDown);
        canvas.off('mouse:move', handleMouseMove);
        canvas.off('mouse:up', handleMouseUp);
      };
    }
  }, [activeTool, drawingColor, mode, canvasReady]);

  // Clear all annotations
  const handleClear = useCallback(() => {
    const canvas = fabricCanvasRef.current;
    if (!canvas) return;

    const objects = canvas.getObjects();
    objects.forEach((obj) => canvas.remove(obj));
    canvas.renderAll();
    onAnnotationsChange([]);
  }, [onAnnotationsChange]);

  // Delete selected object
  const handleDelete = useCallback(() => {
    const canvas = fabricCanvasRef.current;
    if (!canvas) return;

    const activeObject = canvas.getActiveObject();
    if (activeObject) {
      canvas.remove(activeObject);
      canvas.renderAll();
    }
  }, []);

  if (!pdfUrl) {
    return (
      <div className="w-full h-full flex items-center justify-center text-white">
        <div className="text-center">
          <i className="fas fa-file-pdf text-4xl mb-3 opacity-50"></i>
          <p>Unable to load PDF</p>
          <p className="text-sm opacity-75">File ID not found</p>
        </div>
      </div>
    );
  }

  if (!isClient) {
    return (
      <div className="w-full h-full flex items-center justify-center text-white">
        <div className="text-center">
          <i className="fas fa-spinner fa-spin text-2xl mb-2"></i>
          <p>Loading PDF viewer...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full flex flex-col bg-gray-900">
      {/* Toolbar */}
      {mode === 'edit' && (
        <div
          className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex gap-2 p-2 rounded-lg shadow-lg"
          style={{
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
          }}
        >
          {/* Tool Buttons */}
          <button
            onClick={() => setActiveTool('select')}
            className={`p-2 px-3 rounded transition-colors ${
              activeTool === 'select' ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'
            }`}
            title="Select (Move/Resize)"
          >
            <i className="fas fa-mouse-pointer"></i>
          </button>

          <button
            onClick={() => setActiveTool('pen')}
            className={`p-2 px-3 rounded transition-colors ${
              activeTool === 'pen' ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'
            }`}
            title="Freehand Pen"
          >
            <i className="fas fa-pen"></i>
          </button>

          <button
            onClick={() => setActiveTool('highlighter')}
            className={`p-2 px-3 rounded transition-colors ${
              activeTool === 'highlighter' ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'
            }`}
            title="Highlighter"
          >
            <i className="fas fa-highlighter"></i>
          </button>

          <button
            onClick={() => setActiveTool('text')}
            className={`p-2 px-3 rounded transition-colors ${
              activeTool === 'text' ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'
            }`}
            title="Text"
          >
            <i className="fas fa-font"></i>
          </button>

          <button
            onClick={() => setActiveTool('rectangle')}
            className={`p-2 px-3 rounded transition-colors ${
              activeTool === 'rectangle' ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'
            }`}
            title="Rectangle"
          >
            <i className="far fa-square"></i>
          </button>

          <div className="w-px bg-gray-300"></div>

          {/* Color Picker */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Color:</label>
            <input
              type="color"
              value={drawingColor}
              onChange={(e) => setDrawingColor(e.target.value)}
              className="w-10 h-8 rounded cursor-pointer"
            />
          </div>

          <div className="w-px bg-gray-300"></div>

          {/* Actions */}
          <button
            onClick={handleDelete}
            className="p-2 px-3 rounded bg-orange-100 hover:bg-orange-200 text-orange-700 transition-colors"
            title="Delete Selected"
          >
            <i className="fas fa-eraser"></i>
          </button>

          <button
            onClick={handleClear}
            className="p-2 px-3 rounded bg-red-100 hover:bg-red-200 text-red-700 transition-colors"
            title="Clear All Annotations"
          >
            <i className="fas fa-trash"></i>
          </button>
        </div>
      )}

      {/* PDF Viewer with Fabric.js Overlay */}
      <div 
        ref={viewerContainerRef}
        className="flex-1 relative"
        style={{ background: '#374151', overflow: 'auto' }}
      >
        {/* @react-pdf-viewer/core PDF Viewer */}
        <div 
          className="w-full h-full"
        >
          <Worker workerUrl={`https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js`}>
            <Viewer fileUrl={pdfUrl} />
          </Worker>
        </div>

      {/* Fabric.js Canvas Overlay - Rendered via Portal into the PDF Viewer's content container */}
      {/* We wrap the canvas in a div so React owns the div. Fabric modifies the DOM inside this div.
          This prevents "Failed to execute 'removeChild' on 'Node'" errors when React tries to unmount
          because React only needs to remove the wrapper div, not the complex Fabric DOM structure. */}
      {mode === 'edit' && pdfContentContainer && createPortal(
        <div 
          className="annotation-layer-wrapper" 
          style={{
            position: 'absolute', 
            top: 0, 
            left: 0, 
            width: '100%', 
            height: '100%', 
            zIndex: 10, 
            pointerEvents: 'none'
          }}
        >
          <canvas
            ref={canvasRef}
            className="absolute top-0 left-0"
          />
        </div>,
        pdfContentContainer
      )}
      </div>
    </div>
  );
}

// Export with dynamic import
export const DocumentAnnotationEditor = DocumentAnnotationEditorComponent;

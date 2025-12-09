/**
 * Image Annotation Editor Component
 * 
 * Fabric.js-based canvas for annotating images.
 * Supports freehand drawing, highlighting, text boxes, and shapes.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import fabric from 'fabric';
import { getApiBaseUrl } from '@/lib/api-config';
import type { MediaFormat, Annotation } from './MediaFullScreenModal';

interface ImageAnnotationEditorProps {
  mediaFormat: MediaFormat;
  mode: 'view' | 'edit';
  annotations: Annotation[];
  onAnnotationsChange: (annotations: Annotation[]) => void;
}

type DrawingTool = 'select' | 'pen' | 'highlighter' | 'text' | 'rectangle';

export interface ImageAnnotationEditorRef {
  getAnnotatedDataURL: () => string;
}

export const ImageAnnotationEditor = React.forwardRef<ImageAnnotationEditorRef, ImageAnnotationEditorProps>(({
  mediaFormat,
  mode,
  annotations,
  onAnnotationsChange,
}, ref) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fabricCanvasRef = useRef<fabric.Canvas | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [activeTool, setActiveTool] = useState<DrawingTool>('select');
  const [drawingColor, setDrawingColor] = useState('#FF0000');

  // Expose method to get annotated image
  React.useImperativeHandle(ref, () => ({
    getAnnotatedDataURL: () => {
      if (fabricCanvasRef.current) {
        // 1. Get the current viewport transform (zoom/pan)
        const originalViewport = fabricCanvasRef.current.viewportTransform;
        const originalWidth = fabricCanvasRef.current.width;
        const originalHeight = fabricCanvasRef.current.height;

        // 2. Reset viewport to show full image
        // We need to find the bounding box of the background image + all objects
        const bgImage = fabricCanvasRef.current.backgroundImage as fabric.FabricImage;
        if (bgImage) {
          // Temporarily resize canvas to match image dimensions if needed
          // For simple export, usually toDataURL({ format: 'png', multiplier: ... }) works
          // But we want to ensure we capture the *original* image resolution if possible
          
          return fabricCanvasRef.current.toDataURL({
            format: 'png',
            quality: 1,
            enableRetinaScaling: true,
            multiplier: 1 // Adjust if you want higher res
          });
        }

        return fabricCanvasRef.current.toDataURL({ 
          format: 'png',
          multiplier: 1
        });
      }
      return '';
    }
  }));

  // Get file ID from MediaFormat
  const getFileId = useCallback(() => {
    if (mediaFormat.metadata?.file_id) {
      return mediaFormat.metadata.file_id;
    }
    
    if (mediaFormat.data_type === 'file_path') {
      const path = mediaFormat.data;
      const uuidMatch = path.match(/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i);
      if (uuidMatch) {
        return uuidMatch[1];
      }
      // If data is just the file_id itself
      if (path && path.match(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i)) {
        return path;
      }
    }
    
    return null;
  }, [mediaFormat]);

  // Initialize Fabric.js canvas
  useEffect(() => {
    if (!canvasRef.current || !containerRef.current) return;

    const canvas = new fabric.Canvas(canvasRef.current, {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      backgroundColor: 'transparent', // Transparent instead of white
      selection: mode === 'edit' && activeTool === 'select',
      isDrawingMode: false,
    });

    fabricCanvasRef.current = canvas;

    // Load background image
    const fileId = getFileId();
    if (fileId) {
      const imageUrl = `${getApiBaseUrl()}/api/v1/files/${fileId}/view`;
      
      fabric.FabricImage.fromURL(imageUrl, { crossOrigin: 'anonymous' }).then((img: fabric.FabricImage) => {
        if (!canvas) return;
        
        // Scale image to fit canvas
        const scale = Math.min(
          canvas.width! / (img.width || 1),
          canvas.height! / (img.height || 1)
        );
        
        img.scale(scale);
        img.set({
          left: (canvas.width! - (img.width || 0) * scale) / 2,
          top: (canvas.height! - (img.height || 0) * scale) / 2,
          selectable: false,
          evented: false,
        });
        
        canvas.backgroundImage = img;
        canvas.renderAll();
      }).catch(err => {
        console.error('Failed to load image:', err);
        const text = new fabric.Text('Failed to load image: ' + err.message, {
          left: canvas.width! / 2,
          top: canvas.height! / 2,
          originX: 'center',
          originY: 'center',
          fill: '#ff0000',
          fontSize: 16,
          textAlign: 'center',
        });
        canvas.add(text);
        canvas.renderAll();
      });
    }

    // Load existing annotations
    if (annotations && annotations.length > 0) {
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

    // Cleanup
    return () => {
      canvas.dispose();
      fabricCanvasRef.current = null;
    };
  }, [mediaFormat, mode, getFileId]);

  // Handle tool changes
  useEffect(() => {
    const canvas = fabricCanvasRef.current;
    if (!canvas) return;

    // Reset drawing mode
    canvas.isDrawingMode = false;
    canvas.selection = false;

    if (mode === 'view') {
      // View mode - no interaction
      canvas.selection = false;
      return;
    }

    // Edit mode
    switch (activeTool) {
      case 'select':
        canvas.selection = true;
        break;

      case 'pen':
        canvas.isDrawingMode = true;
        canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
        canvas.freeDrawingBrush.color = drawingColor;
        canvas.freeDrawingBrush.width = 3;
        break;

      case 'highlighter':
        canvas.isDrawingMode = true;
        canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
        // Convert color to rgba with 30% opacity
        const hexColor = drawingColor;
        const r = parseInt(hexColor.slice(1, 3), 16);
        const g = parseInt(hexColor.slice(3, 5), 16);
        const b = parseInt(hexColor.slice(5, 7), 16);
        canvas.freeDrawingBrush.color = `rgba(${r}, ${g}, ${b}, 0.3)`;
        canvas.freeDrawingBrush.width = 20;
        break;

      case 'text':
        // Text mode handled by click event
        canvas.selection = false;
        break;

      case 'rectangle':
        // Rectangle mode handled by mouse events
        canvas.selection = false;
        break;
    }
  }, [activeTool, drawingColor, mode]);

  // Handle object creation (save annotations)
  useEffect(() => {
    const canvas = fabricCanvasRef.current;
    if (!canvas || mode === 'view') return;

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
  }, [mode, activeTool, drawingColor, onAnnotationsChange]);

  // Handle text and rectangle tools
  useEffect(() => {
    const canvas = fabricCanvasRef.current;
    if (!canvas || mode === 'view') return;
    
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
  }, [activeTool, drawingColor, mode]);

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

  return (
    <div ref={containerRef} className="relative w-full h-full flex flex-col">
      {/* Toolbar (Edit Mode Only) */}
      {mode === 'edit' && (
        <div
          className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex gap-2 p-2 rounded-lg shadow-lg"
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
            title="Delete Selected (Delete Key)"
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

      {/* Canvas */}
      <canvas ref={canvasRef} className="max-w-full max-h-full" />
    </div>
  );
});


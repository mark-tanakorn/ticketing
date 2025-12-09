/**
 * Custom hook for managing canvas pan and zoom functionality
 */

import { useEffect, useRef, useCallback } from 'react';

interface CanvasEditor {
  baseCanvasSize: number;
  canvas: HTMLDivElement | null;
  viewport: HTMLDivElement | null;
  connectionLayer: null;
  _viewportResizeObserver: ResizeObserver | null;
  miniMapCanvas: null;
  isPanning: boolean;
  panStart: { x: number; y: number };
  scrollStart: { left: number; top: number };
  scale: number;
  onScaleChange?: (scale: number) => void;
}

interface GridSettings {
  gridSize: number;
  gridOpacity: number;
  enableGrid: boolean;
}

export function useCanvasPanZoom(
  viewportRef: React.RefObject<HTMLDivElement | null>,
  gridSettings?: GridSettings,
  onScaleChange?: (scale: number) => void
) {
  const editorRef = useRef<CanvasEditor>({
    baseCanvasSize: 5000,
    canvas: null,
    viewport: null,
    connectionLayer: null,
    _viewportResizeObserver: null,
    miniMapCanvas: null,
    isPanning: false,
    panStart: { x: 0, y: 0 },
    scrollStart: { left: 0, top: 0 },
    scale: 1,
    onScaleChange,
  });

  useEffect(() => {
    if (!viewportRef.current) return;

    const editor = editorRef.current;
    
    // Clean up any existing canvas first (important for navigation)
    const existingCanvas = viewportRef.current.querySelector('.node-canvas');
    if (existingCanvas) {
      existingCanvas.remove();
    }
    
    createCanvasWithGrid(editor, viewportRef.current, gridSettings);
    initializeCanvasEventListeners(editor);

    const handleMouseMove = (e: MouseEvent) => handleDocumentMouseMove(editor, e);
    const handleMouseUp = (e: MouseEvent) => handleDocumentMouseUp(editor, e);
    const handleResize = () => ensureCanvasCoverage(editor);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    window.addEventListener("resize", handleResize);

    return () => {
      // Clean up canvas element
      if (editor.canvas && editor.canvas.parentElement) {
        editor.canvas.remove();
      }
      
      if (editor._viewportResizeObserver) {
        editor._viewportResizeObserver.disconnect();
      }
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      window.removeEventListener("resize", handleResize);
    };
  }, [viewportRef]); // Only create canvas once!

  // Separate effect to update grid styling without recreating canvas
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor.canvas || !gridSettings) return;

    updateGridStyles(editor.canvas, gridSettings);
  }, [gridSettings]); // Update styles when settings change

  // Update onScaleChange callback when it changes
  useEffect(() => {
    editorRef.current.onScaleChange = onScaleChange;
  }, [onScaleChange]);

  // Zoom control methods
  const zoomIn = useCallback(() => {
    const editor = editorRef.current;
    const newScale = Math.min(2, editor.scale * 1.1);
    if (newScale !== editor.scale) {
      editor.scale = newScale;
      updateCanvasTransform(editor);
      if (editor.onScaleChange) {
        editor.onScaleChange(newScale);
      }
    }
  }, []);

  const zoomOut = useCallback(() => {
    const editor = editorRef.current;
    const newScale = Math.max(0.1, editor.scale * 0.9);
    if (newScale !== editor.scale) {
      editor.scale = newScale;
      updateCanvasTransform(editor);
      if (editor.onScaleChange) {
        editor.onScaleChange(newScale);
      }
    }
  }, []);

  const zoomReset = useCallback(() => {
    const editor = editorRef.current;
    if (editor.scale !== 1) {
      editor.scale = 1;
      updateCanvasTransform(editor);
      if (editor.onScaleChange) {
        editor.onScaleChange(1);
      }
    }
  }, []);

  const setZoom = useCallback((scale: number) => {
    const editor = editorRef.current;
    const newScale = Math.max(0.1, Math.min(2, scale));
    if (newScale !== editor.scale) {
      editor.scale = newScale;
      updateCanvasTransform(editor);
      if (editor.onScaleChange) {
        editor.onScaleChange(newScale);
      }
    }
  }, []);

  return {
    canvasRef: editorRef.current.canvas,
    scale: editorRef.current.scale,
    zoomIn,
    zoomOut,
    zoomReset,
    setZoom,
  };
}

function updateGridStyles(canvas: HTMLDivElement, gridSettings: GridSettings) {
  // Get grid color from CSS variable
  let gridColor = window.getComputedStyle(document.documentElement)
    .getPropertyValue("--canvas-grid-color").trim() || "#6c757d";
  
  // Calculate final opacity (0 if disabled)
  const finalOpacity = gridSettings.enableGrid ? gridSettings.gridOpacity : 0;
  
  // Convert color to rgba with opacity
  if (gridColor.startsWith("#")) {
    const r = parseInt(gridColor.slice(1, 3), 16);
    const g = parseInt(gridColor.slice(3, 5), 16);
    const b = parseInt(gridColor.slice(5, 7), 16);
    gridColor = `rgba(${r}, ${g}, ${b}, ${finalOpacity})`;
  } else if (!gridColor.startsWith("rgba")) {
    gridColor = gridColor.replace("rgb(", "rgba(").replace(")", `, ${finalOpacity})`);
  }
  
  // Apply new grid pattern
  const dotSize = 2;
  const gridPattern = `radial-gradient(circle at ${dotSize}px ${dotSize}px, ${gridColor} ${dotSize}px, transparent 0)`;
  canvas.style.backgroundImage = gridPattern;
  canvas.style.backgroundSize = `${gridSettings.gridSize}px ${gridSettings.gridSize}px`;
}

function createCanvasWithGrid(
  editor: CanvasEditor, 
  viewport: HTMLDivElement,
  gridSettings?: GridSettings
) {
  const canvas = document.createElement("div");
  canvas.className = "node-canvas";
  canvas.id = "nodeCanvas";
  canvas.style.minHeight = editor.baseCanvasSize + "px";
  canvas.style.minWidth = editor.baseCanvasSize + "px";
  canvas.style.position = "absolute";
  canvas.style.top = "0";
  canvas.style.left = "0";

  viewport.appendChild(canvas);
  editor.canvas = canvas;
  editor.viewport = viewport;
  editor.connectionLayer = null;
  editor.viewport.style.position = "relative";
  editor.viewport.style.overflow = "auto";

  // Use passed-in settings or fall back to CSS variables
  const gridSize = gridSettings?.gridSize 
    ? `${gridSettings.gridSize}px`
    : (window.getComputedStyle(document.documentElement).getPropertyValue("--canvas-grid-size").trim() || "20px");
  
  const gridOpacity = gridSettings?.gridOpacity ?? 
    (parseFloat(window.getComputedStyle(document.documentElement).getPropertyValue("--canvas-grid-opacity").trim()) || 0.3);
  
  const enableGrid = gridSettings?.enableGrid ?? true;

  // If grid is disabled, set opacity to 0
  const finalOpacity = enableGrid ? gridOpacity : 0;

  let gridColor = window.getComputedStyle(document.documentElement).getPropertyValue("--canvas-grid-color").trim() || "#6c757d";

  if (gridColor.startsWith("#")) {
    const r = parseInt(gridColor.slice(1, 3), 16);
    const g = parseInt(gridColor.slice(3, 5), 16);
    const b = parseInt(gridColor.slice(5, 7), 16);
    gridColor = `rgba(${r}, ${g}, ${b}, ${finalOpacity})`;
  } else if (!gridColor.startsWith("rgba")) {
    gridColor = gridColor.replace("rgb(", "rgba(").replace(")", `, ${finalOpacity})`);
  }

  const dotSize = 2;
  const gridPattern = `radial-gradient(circle at ${dotSize}px ${dotSize}px, ${gridColor} ${dotSize}px, transparent 0)`;
  canvas.style.backgroundImage = gridPattern;
  canvas.style.backgroundSize = `${gridSize} ${gridSize}`;
  canvas.style.transformOrigin = "0 0";
  canvas.style.transform = `scale(${editor.scale})`;

  ensureCanvasCoverage(editor);
  const onResize = () => ensureCanvasCoverage(editor);
  window.addEventListener("resize", onResize);
  
  if (window.ResizeObserver) {
    const ro = new ResizeObserver(onResize);
    ro.observe(editor.viewport);
    editor._viewportResizeObserver = ro;
  }
}

function initializeCanvasEventListeners(editor: CanvasEditor) {
  if (!editor.canvas) return;

  editor.canvas.addEventListener("mousedown", (e: MouseEvent) => handleCanvasMouseDown(editor, e));
  
  if (editor.viewport) {
    editor.viewport.addEventListener("mousedown", (e: MouseEvent) => handleCanvasMouseDown(editor, e));
    // Only attach wheel listener to viewport (not canvas) to allow natural scrolling
    // Use passive: false to allow preventDefault for Ctrl+scroll zoom
    editor.viewport.addEventListener("wheel", (e: WheelEvent) => handleCanvasWheel(editor, e), { passive: false });
  }
}

function ensureCanvasCoverage(editor: CanvasEditor) {
  if (!editor.canvas || !editor.viewport) return;

  const viewportRect = editor.viewport.getBoundingClientRect();
  const requiredMinWidth = Math.max(
    editor.baseCanvasSize,
    Math.ceil(viewportRect.width / Math.max(editor.scale || 1, 0.001))
  );
  const requiredMinHeight = Math.max(
    editor.baseCanvasSize,
    Math.ceil(viewportRect.height / Math.max(editor.scale || 1, 0.001))
  );

  const currentMinWidth = parseInt(editor.canvas.style.minWidth || "0", 10) || 0;
  const currentMinHeight = parseInt(editor.canvas.style.minHeight || "0", 10) || 0;

  if (requiredMinWidth > currentMinWidth) {
    editor.canvas.style.minWidth = requiredMinWidth + "px";
  }
  if (requiredMinHeight > currentMinHeight) {
    editor.canvas.style.minHeight = requiredMinHeight + "px";
  }
}

function handleCanvasMouseDown(editor: CanvasEditor, e: MouseEvent) {
  if (e.button !== 0) return;
  
  // Only start panning if clicking directly on the canvas, not on nodes
  const target = e.target as HTMLElement;
  if (target.closest('.workflow-node')) return;

  // Only pan if Ctrl/Cmd is held down
  if (!e.ctrlKey && !e.metaKey) return;

  editor.isPanning = true;
  editor.panStart = { x: e.clientX, y: e.clientY };
  editor.scrollStart = {
    left: editor.viewport!.scrollLeft,
    top: editor.viewport!.scrollTop
  };

  e.preventDefault();
  document.body.style.userSelect = "none";
  editor.viewport!.style.cursor = "grabbing";
}

function handleCanvasWheel(editor: CanvasEditor, e: WheelEvent) {
  // Only intercept wheel events when Ctrl/Cmd is pressed for zooming
  // Otherwise, let the browser handle natural scrolling
  if (e.ctrlKey || e.metaKey) {
    // Prevent default zoom behavior and implement custom zoom
    e.preventDefault();
    e.stopPropagation();
    
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.1, Math.min(2, editor.scale * zoomFactor));

    if (newScale !== editor.scale) {
      editor.scale = newScale;
      updateCanvasTransform(editor);
      if (editor.onScaleChange) {
        editor.onScaleChange(newScale);
      }
    }
  }
  // If Ctrl/Cmd is NOT pressed, we don't do anything and let browser handle scroll
}

function handleDocumentMouseMove(editor: CanvasEditor, e: MouseEvent) {
  if (!editor.isPanning) return;

  e.preventDefault();
  const dx = e.clientX - editor.panStart.x;
  const dy = e.clientY - editor.panStart.y;

  editor.viewport!.scrollLeft = editor.scrollStart.left - dx;
  editor.viewport!.scrollTop = editor.scrollStart.top - dy;
}

function handleDocumentMouseUp(editor: CanvasEditor, e: MouseEvent) {
  if (e.button !== 0) return;

  editor.isPanning = false;
  document.body.style.userSelect = "";
  editor.viewport!.style.cursor = "";
}

function updateCanvasTransform(editor: CanvasEditor) {
  if (!editor.canvas) return;

  editor.canvas.style.transform = `scale(${editor.scale})`;
  editor.canvas.style.transformOrigin = "0 0";
  ensureCanvasCoverage(editor);
}


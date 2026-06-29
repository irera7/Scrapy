'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { datasetApi, dataApi, projectsApi } from '@/lib/api'
import { useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useTranslations } from 'next-intl'
import {
  Square,
  Type,
  Tag,
  Trash2,
  Save,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Move,
  Loader2,
  Plus,
  Settings,
  Layers,
  Eye,
  EyeOff,
  Undo,
  Redo,
  Download,
  Target,
  Image as ImageIcon,
  FileText,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const annotationsTutorial: TutorialSection[] = [
  {
    title: 'Annotation Studio Overview',
    content: 'The Annotation Studio lets you label your data for ML training. Support for bounding boxes (images), NER spans (text), and classifications.',
    tips: [
      'Use keyboard shortcuts for faster annotation',
      'Save frequently with Ctrl+S or the Save button',
      'Use arrow keys to navigate between items',
    ],
  },
  {
    title: 'Getting Started',
    content: 'Select a project and start annotating items one by one.',
    steps: [
      { title: 'Select Project', description: 'Choose a project from the dropdown' },
      { title: 'Select Label', description: 'Click a label from the right panel before drawing' },
      { title: 'Draw Annotation', description: 'Click and drag on image, or select text' },
      { title: 'Save & Next', description: 'Click Save then navigate to next item' },
    ],
  },
  {
    title: 'Image Annotation Tools',
    content: 'Tools for annotating images with bounding boxes and regions.',
    steps: [
      { title: 'Select Tool (V)', description: 'Click to select and move annotations' },
      { title: 'Bounding Box (B)', description: 'Draw rectangular regions around objects' },
      { title: 'Zoom In/Out', description: 'Zoom for precise annotation' },
      { title: 'Toggle Labels', description: 'Show/hide label names on boxes' },
    ],
    tips: [
      'Select a label first before drawing boxes',
      'Draw boxes from corner to corner with click-drag',
      'Use zoom for small or detailed objects',
    ],
  },
  {
    title: 'Text Annotation (NER)',
    content: 'Annotate named entities in text by selecting spans.',
    steps: [
      { title: 'Select Label', description: 'Choose an entity type (PERSON, ORG, etc.)' },
      { title: 'Highlight Text', description: 'Click and drag to select text' },
      { title: 'Release', description: 'Entity is automatically created' },
    ],
    tips: [
      'Be consistent with span boundaries (include/exclude spaces)',
      'You can delete annotations from the right panel',
    ],
  },
  {
    title: 'Keyboard Shortcuts',
    content: 'Speed up annotation with these shortcuts.',
    steps: [
      { title: '←  / →', description: 'Navigate to previous/next item' },
      { title: 'V', description: 'Switch to Select tool' },
      { title: 'B', description: 'Switch to Bounding Box tool' },
      { title: 'Ctrl+S', description: 'Save annotations' },
    ],
  },
  {
    title: 'Best Practices',
    content: 'Tips for high-quality annotations.',
    tips: [
      'Be consistent with labeling guidelines across all items',
      'Include tight bounding boxes - not too loose, not too tight',
      'For NER, decide upfront whether to include punctuation',
      'Review annotations periodically for quality',
      'Use quality scores to prioritize items needing attention',
    ],
    warning: 'Annotations are auto-saved when navigating, but always click Save before closing.',
  },
]

interface BBox {
  id: string
  label: string
  x: number
  y: number
  width: number
  height: number
  color: string
}

interface NERSpan {
  id: string
  label: string
  start: number
  end: number
  text: string
  color: string
}

export default function AnnotationsPage() {
  const queryClient = useQueryClient()
  const searchParams = useSearchParams()
  const preselectedProject = searchParams.get('project')
  
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  
  const [projectId, setProjectId] = useState(preselectedProject || '')
  const [currentItemIndex, setCurrentItemIndex] = useState(0)
  const [tool, setTool] = useState<'select' | 'bbox' | 'polygon'>('select')
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDrawing, setIsDrawing] = useState(false)
  const [startPos, setStartPos] = useState({ x: 0, y: 0 })
  const [currentRect, setCurrentRect] = useState<{ x: number; y: number; width: number; height: number } | null>(null)
  const [bboxes, setBboxes] = useState<BBox[]>([])
  const [nerSpans, setNerSpans] = useState<NERSpan[]>([])
  const [selectedLabel, setSelectedLabel] = useState('')
  const [showLabels, setShowLabels] = useState(true)
  const [image, setImage] = useState<HTMLImageElement | null>(null)

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const { data: annotationTypes } = useQuery({
    queryKey: ['annotation-types', projectId],
    queryFn: () => datasetApi.listAnnotationTypes(projectId),
    enabled: !!projectId,
  })

  const { data: dataItems, isLoading } = useQuery({
    queryKey: ['data-items-for-annotation', projectId],
    queryFn: () => dataApi.list(projectId, { limit: 100 }),
    enabled: !!projectId,
  })

  const items = dataItems?.items || dataItems || []
  const currentItem = items[currentItemIndex]

  // Load annotations when item changes
  useEffect(() => {
    if (currentItem?.annotations) {
      const ann = currentItem.annotations
      if (ann.bboxes) {
        setBboxes(ann.bboxes.map((b: any, i: number) => ({
          ...b,
          id: `bbox-${i}`,
          color: annotationTypes?.find((t: any) => t.id === b.type_id)?.color || '#3B82F6',
        })))
      } else {
        setBboxes([])
      }
      if (ann.ner) {
        setNerSpans(ann.ner.map((n: any, i: number) => ({
          ...n,
          id: `ner-${i}`,
          color: annotationTypes?.find((t: any) => t.id === n.type_id)?.color || '#3B82F6',
        })))
      } else {
        setNerSpans([])
      }
    } else {
      setBboxes([])
      setNerSpans([])
    }
  }, [currentItem, annotationTypes])

  // Load image when item changes
  useEffect(() => {
    if (currentItem?.data_type === 'image') {
      // Try different URL sources
      const imageUrl = currentItem.download_url || currentItem.file_path || currentItem.source_url
      
      if (imageUrl) {
        const img = new Image()
        img.crossOrigin = 'anonymous'
        img.onload = () => setImage(img)
        img.onerror = () => {
          console.warn('Failed to load image:', imageUrl)
          setImage(null)
        }
        img.src = imageUrl
      } else {
        setImage(null)
      }
    } else {
      setImage(null)
    }
  }, [currentItem])

  // Draw canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !image) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size
    canvas.width = image.width
    canvas.height = image.height

    // Clear and draw image
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(image, 0, 0)

    // Draw existing bboxes
    bboxes.forEach((bbox) => {
      ctx.strokeStyle = bbox.color
      ctx.lineWidth = 2
      ctx.strokeRect(bbox.x, bbox.y, bbox.width, bbox.height)
      
      if (showLabels) {
        ctx.fillStyle = bbox.color
        ctx.fillRect(bbox.x, bbox.y - 20, ctx.measureText(bbox.label).width + 10, 20)
        ctx.fillStyle = 'white'
        ctx.font = '12px sans-serif'
        ctx.fillText(bbox.label, bbox.x + 5, bbox.y - 6)
      }
    })

    // Draw current rectangle being drawn
    if (currentRect) {
      ctx.strokeStyle = '#10B981'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 5])
      ctx.strokeRect(currentRect.x, currentRect.y, currentRect.width, currentRect.height)
      ctx.setLineDash([])
    }
  }, [image, bboxes, currentRect, showLabels])

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (tool !== 'bbox' || !selectedLabel) return
    
    const canvas = canvasRef.current
    if (!canvas) return
    
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY
    
    setIsDrawing(true)
    setStartPos({ x, y })
    setCurrentRect({ x, y, width: 0, height: 0 })
  }, [tool, selectedLabel])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return
    
    const canvas = canvasRef.current
    if (!canvas) return
    
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY
    
    setCurrentRect({
      x: Math.min(startPos.x, x),
      y: Math.min(startPos.y, y),
      width: Math.abs(x - startPos.x),
      height: Math.abs(y - startPos.y),
    })
  }, [isDrawing, startPos])

  const handleMouseUp = useCallback(() => {
    if (!isDrawing || !currentRect || !selectedLabel) return
    
    // Only add if has meaningful size
    if (currentRect.width > 10 && currentRect.height > 10) {
      const labelInfo = annotationTypes?.find((t: any) => t.name === selectedLabel)
      setBboxes([...bboxes, {
        id: `bbox-${Date.now()}`,
        label: selectedLabel,
        x: currentRect.x,
        y: currentRect.y,
        width: currentRect.width,
        height: currentRect.height,
        color: labelInfo?.color || '#3B82F6',
      }])
    }
    
    setIsDrawing(false)
    setCurrentRect(null)
  }, [isDrawing, currentRect, selectedLabel, bboxes, annotationTypes])

  const deleteBbox = (id: string) => {
    setBboxes(bboxes.filter(b => b.id !== id))
  }

  const saveAnnotationsMutation = useMutation({
    mutationFn: async () => {
      if (!currentItem) return
      
      const annotations = {
        bboxes: bboxes.map(b => ({
          type_id: annotationTypes?.find((t: any) => t.name === b.label)?.id,
          label: b.label,
          x: b.x,
          y: b.y,
          width: b.width,
          height: b.height,
        })),
        ner: nerSpans.map(n => ({
          type_id: annotationTypes?.find((t: any) => t.name === n.label)?.id,
          label: n.label,
          start: n.start,
          end: n.end,
          text: n.text,
        })),
        classifications: [],
        polygons: [],
        keypoints: [],
        relations: [],
      }
      
      return datasetApi.annotateItem(currentItem.id, { annotations, merge: false })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-items-for-annotation'] })
      toast.success('Annotations saved')
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail
      let errorMsg = 'Failed to save annotations'
      if (typeof detail === 'string') {
        errorMsg = detail
      } else if (Array.isArray(detail)) {
        errorMsg = detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ')
      } else if (detail?.msg) {
        errorMsg = detail.msg
      }
      toast.error(errorMsg)
    },
  })

  const handleTextSelection = useCallback(() => {
    if (!selectedLabel || currentItem?.data_type !== 'text') return
    
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) return
    
    const text = selection.toString()
    const range = selection.getRangeAt(0)
    
    // Get the text content element
    const textElement = document.getElementById('text-content')
    if (!textElement) return
    
    // Calculate offsets
    const startOffset = range.startOffset
    const endOffset = range.endOffset
    
    const labelInfo = annotationTypes?.find((t: any) => t.name === selectedLabel)
    
    setNerSpans([...nerSpans, {
      id: `ner-${Date.now()}`,
      label: selectedLabel,
      start: startOffset,
      end: endOffset,
      text: text,
      color: labelInfo?.color || '#3B82F6',
    }])
    
    selection.removeAllRanges()
  }, [selectedLabel, currentItem, nerSpans, annotationTypes])

  const goToNext = () => {
    if (currentItemIndex < items.length - 1) {
      saveAnnotationsMutation.mutate()
      setCurrentItemIndex(currentItemIndex + 1)
    }
  }

  const goToPrev = () => {
    if (currentItemIndex > 0) {
      saveAnnotationsMutation.mutate()
      setCurrentItemIndex(currentItemIndex - 1)
    }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') goToNext()
      if (e.key === 'ArrowLeft') goToPrev()
      if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        saveAnnotationsMutation.mutate()
      }
      if (e.key === 'b') setTool('bbox')
      if (e.key === 'v') setTool('select')
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentItemIndex, items.length])

  return (
    <div className="h-screen flex flex-col">
      {/* Tutorial */}
      <TutorialPanel
        title="Annotation Studio Guide"
        description="Learn how to label and annotate your data"
        sections={annotationsTutorial}
        storageKey="annotations"
      />

      {/* Header */}
      <div className="p-4 border-b border-surface-800 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Target className="w-6 h-6" />
            Annotation Studio
          </h1>
          
          <select
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value)
              setCurrentItemIndex(0)
            }}
            className="px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 text-sm"
          >
            <option value="">Select project</option>
            {projects?.map((p: any) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-sm text-surface-400">
            {currentItemIndex + 1} / {items.length}
          </span>
          
          <button
            onClick={goToPrev}
            disabled={currentItemIndex === 0}
            className="p-2 rounded-lg hover:bg-surface-800 disabled:opacity-50"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          
          <button
            onClick={goToNext}
            disabled={currentItemIndex >= items.length - 1}
            className="p-2 rounded-lg hover:bg-surface-800 disabled:opacity-50"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => saveAnnotationsMutation.mutate()}
            disabled={saveAnnotationsMutation.isPending}
            className="px-4 py-2 rounded-lg bg-brand-500 text-white hover:bg-brand-600 flex items-center gap-2"
          >
            {saveAnnotationsMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Toolbar */}
        <div className="w-16 border-r border-surface-800 p-2 flex flex-col gap-2">
          <button
            onClick={() => setTool('select')}
            className={`p-3 rounded-lg transition-colors ${tool === 'select' ? 'bg-brand-500 text-white' : 'hover:bg-surface-800'}`}
            title="Select (V)"
          >
            <Move className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => setTool('bbox')}
            className={`p-3 rounded-lg transition-colors ${tool === 'bbox' ? 'bg-brand-500 text-white' : 'hover:bg-surface-800'}`}
            title="Bounding Box (B)"
          >
            <Square className="w-5 h-5" />
          </button>
          
          <div className="flex-1" />
          
          <button
            onClick={() => setZoom(z => Math.min(z + 0.25, 3))}
            className="p-3 rounded-lg hover:bg-surface-800"
            title="Zoom In"
          >
            <ZoomIn className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => setZoom(z => Math.max(z - 0.25, 0.25))}
            className="p-3 rounded-lg hover:bg-surface-800"
            title="Zoom Out"
          >
            <ZoomOut className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => setShowLabels(!showLabels)}
            className={`p-3 rounded-lg transition-colors ${showLabels ? 'text-brand-400' : 'text-surface-400'}`}
            title="Toggle Labels"
          >
            {showLabels ? <Eye className="w-5 h-5" /> : <EyeOff className="w-5 h-5" />}
          </button>
        </div>

        {/* Main Canvas Area */}
        <div className="flex-1 overflow-auto bg-surface-950 relative" ref={containerRef}>
          {!projectId ? (
            <div className="flex items-center justify-center h-full text-surface-400">
              Select a project to start annotating
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
            </div>
          ) : !currentItem ? (
            <div className="flex items-center justify-center h-full text-surface-400">
              No items to annotate
            </div>
          ) : currentItem.data_type === 'image' ? (
            <div 
              className="min-h-full flex items-center justify-center p-8"
              style={{ transform: `scale(${zoom})`, transformOrigin: 'center' }}
            >
              {image ? (
                <canvas
                  ref={canvasRef}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                  className="max-w-full shadow-2xl cursor-crosshair"
                />
              ) : currentItem.source_url ? (
                <div className="text-center">
                  <img 
                    src={currentItem.source_url} 
                    alt="Item" 
                    className="max-w-full max-h-[70vh] rounded-lg shadow-2xl"
                    crossOrigin="anonymous"
                  />
                  <p className="mt-4 text-sm text-surface-400">
                    Image preview (canvas not available)
                  </p>
                </div>
              ) : (
                <div className="text-center p-8 bg-surface-800 rounded-lg">
                  <ImageIcon className="w-16 h-16 mx-auto text-surface-500 mb-4" />
                  <p className="text-surface-400">No image URL available</p>
                  <p className="text-sm text-surface-500 mt-2">
                    Source: {currentItem.source_url || 'N/A'}
                  </p>
                </div>
              )}
            </div>
          ) : currentItem.data_type === 'text' ? (
            <div className="p-8 max-w-4xl mx-auto">
              {/* Existing Labels Banner */}
              {currentItem.labels?.length > 0 && (
                <div className="mb-4 p-3 rounded-lg bg-brand-500/10 border border-brand-500/30">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Tag className="w-4 h-4 text-brand-400" />
                    <span className="text-sm text-brand-400 mr-2">Labels:</span>
                    {currentItem.labels.map((label: string) => (
                      <span 
                        key={label}
                        className="px-2 py-1 rounded text-sm bg-brand-500/20 text-brand-300"
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              <div 
                id="text-content"
                className="p-6 rounded-xl bg-surface-900 text-lg leading-relaxed select-text whitespace-pre-wrap"
                onMouseUp={handleTextSelection}
              >
                {currentItem.content || (
                  <span className="text-surface-500 italic">No text content available</span>
                )}
              </div>
              
              {/* Metadata preview */}
              {currentItem.item_metadata && Object.keys(currentItem.item_metadata).length > 0 && (
                <div className="mt-4 p-4 rounded-lg bg-surface-800/50">
                  <h4 className="text-sm font-medium text-surface-400 mb-2">Metadata</h4>
                  <div className="text-sm text-surface-300 space-y-1">
                    {Object.entries(currentItem.item_metadata).slice(0, 5).map(([key, value]) => (
                      <div key={key} className="flex">
                        <span className="text-surface-500 w-32 flex-shrink-0">{key}:</span>
                        <span className="truncate">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                    {Object.keys(currentItem.item_metadata).length > 5 && (
                      <div className="text-surface-500 text-xs mt-1">
                        +{Object.keys(currentItem.item_metadata).length - 5} more fields
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {nerSpans.length > 0 && (
                <div className="mt-4 space-y-2">
                  <h4 className="text-sm font-medium text-surface-400">Named Entities</h4>
                  {nerSpans.map((span) => (
                    <div 
                      key={span.id}
                      className="flex items-center justify-between p-2 rounded-lg bg-surface-800"
                    >
                      <div className="flex items-center gap-2">
                        <span 
                          className="px-2 py-1 rounded text-sm"
                          style={{ backgroundColor: span.color + '30', color: span.color }}
                        >
                          {span.label}
                        </span>
                        <span className="text-sm">"{span.text}"</span>
                      </div>
                      <button
                        onClick={() => setNerSpans(nerSpans.filter(n => n.id !== span.id))}
                        className="p-1 hover:text-red-400"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-surface-400">
              Unsupported data type for annotation
            </div>
          )}
        </div>

        {/* Right Panel - Labels & Annotations */}
        <div className="w-80 border-l border-surface-800 flex flex-col">
          {/* Labels for Annotation */}
          <div className="p-4 border-b border-surface-800">
            <h3 className="text-sm font-medium text-surface-400 mb-3">
              Annotation Labels
              <span className="ml-2 text-xs text-surface-500">(select to draw)</span>
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {/* Show annotation types if defined */}
              {annotationTypes?.map((type: any) => (
                <button
                  key={type.id}
                  onClick={() => setSelectedLabel(type.name)}
                  className={`w-full px-3 py-2 rounded-lg text-left flex items-center gap-2 transition-colors ${
                    selectedLabel === type.name 
                      ? 'bg-brand-500/20 border border-brand-500' 
                      : 'bg-surface-800 hover:bg-surface-700'
                  }`}
                >
                  <div 
                    className="w-3 h-3 rounded-sm"
                    style={{ backgroundColor: type.color }}
                  />
                  <span className="text-sm">{type.name}</span>
                  {type.shortcut_key && (
                    <span className="ml-auto text-xs text-surface-500">{type.shortcut_key}</span>
                  )}
                </button>
              ))}
              
              {/* If no annotation types, allow using existing item labels */}
              {(!annotationTypes || annotationTypes.length === 0) && currentItem?.labels?.length > 0 && (
                <>
                  <p className="text-xs text-surface-500 mb-2">Using existing labels:</p>
                  {currentItem.labels.map((label: string) => (
                    <button
                      key={label}
                      onClick={() => setSelectedLabel(label)}
                      className={`w-full px-3 py-2 rounded-lg text-left flex items-center gap-2 transition-colors ${
                        selectedLabel === label 
                          ? 'bg-brand-500/20 border border-brand-500' 
                          : 'bg-surface-800 hover:bg-surface-700'
                      }`}
                    >
                      <div className="w-3 h-3 rounded-sm bg-brand-500" />
                      <span className="text-sm">{label}</span>
                    </button>
                  ))}
                </>
              )}
              
              {(!annotationTypes || annotationTypes.length === 0) && (!currentItem?.labels || currentItem.labels.length === 0) && (
                <p className="text-sm text-surface-500 text-center py-4">
                  No labels defined. Create annotation types in project settings first.
                </p>
              )}
            </div>
            
            {/* Quick label input */}
            <div className="mt-3 flex gap-2">
              <input
                type="text"
                placeholder="Custom label..."
                className="flex-1 px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 text-sm"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const input = e.target as HTMLInputElement
                    if (input.value.trim()) {
                      setSelectedLabel(input.value.trim())
                      input.value = ''
                    }
                  }
                }}
              />
              {selectedLabel && (
                <div className="flex items-center px-2 text-xs text-brand-400 bg-brand-500/20 rounded">
                  {selectedLabel}
                </div>
              )}
            </div>
          </div>

          {/* Annotations List */}
          <div className="flex-1 overflow-auto p-4">
            <h3 className="text-sm font-medium text-surface-400 mb-3">
              Annotations ({bboxes.length + nerSpans.length})
            </h3>
            
            <div className="space-y-2">
              {bboxes.map((bbox) => (
                <div 
                  key={bbox.id}
                  className="p-3 rounded-lg bg-surface-800 flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Square className="w-4 h-4" style={{ color: bbox.color }} />
                    <span className="text-sm">{bbox.label}</span>
                  </div>
                  <button
                    onClick={() => deleteBbox(bbox.id)}
                    className="p-1 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              
              {bboxes.length === 0 && nerSpans.length === 0 && (
                <p className="text-sm text-surface-500 text-center py-8">
                  No annotations yet
                </p>
              )}
            </div>
          </div>

          {/* Item Info */}
          <div className="p-4 border-t border-surface-800 bg-surface-900/50">
            <h3 className="text-sm font-medium text-surface-400 mb-3">Current Item</h3>
            
            <div className="space-y-3">
              {/* Data Type */}
              <div className="flex items-center gap-2">
                {currentItem?.data_type === 'image' ? (
                  <ImageIcon className="w-4 h-4 text-surface-400" />
                ) : (
                  <FileText className="w-4 h-4 text-surface-400" />
                )}
                <span className="text-sm">{currentItem?.data_type}</span>
              </div>
              
              {/* Quality Score */}
              {currentItem?.quality_score !== undefined && currentItem?.quality_score !== null && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-surface-400">Quality:</span>
                  <span className={`font-medium ${
                    currentItem.quality_score >= 0.7 ? 'text-green-400' :
                    currentItem.quality_score >= 0.4 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {(currentItem.quality_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}
              
              {/* Dataset Split */}
              {currentItem?.dataset_split && currentItem.dataset_split !== 'unassigned' && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-surface-400">Split:</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    currentItem.dataset_split === 'train' ? 'bg-blue-500/20 text-blue-400' :
                    currentItem.dataset_split === 'validation' ? 'bg-purple-500/20 text-purple-400' :
                    'bg-orange-500/20 text-orange-400'
                  }`}>
                    {currentItem.dataset_split}
                  </span>
                </div>
              )}
              
              {/* Existing Labels */}
              {currentItem?.labels?.length > 0 && (
                <div>
                  <span className="text-xs text-surface-500 block mb-1">Existing Labels:</span>
                  <div className="flex flex-wrap gap-1">
                    {currentItem.labels.map((label: string) => (
                      <span 
                        key={label}
                        className="px-2 py-1 rounded text-xs bg-brand-500/20 text-brand-400 border border-brand-500/30"
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Is Labeled indicator */}
              <div className="flex items-center justify-between text-sm">
                <span className="text-surface-400">Labeled:</span>
                <span className={currentItem?.is_labeled ? 'text-green-400' : 'text-surface-500'}>
                  {currentItem?.is_labeled ? '✓ Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

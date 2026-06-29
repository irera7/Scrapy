'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dataApi, projectsApi, processingApi, datasetApi } from '@/lib/api'
import { formatDate, formatBytes } from '@/lib/utils'
import { motion } from 'framer-motion'
import { useSearchParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import {
  Search,
  Filter,
  Tag,
  Trash2,
  Loader2,
  Database,
  CheckSquare,
  Square,
  Image as ImageIcon,
  FileText,
  Music,
  Video,
  Upload,
  Eye,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Sparkles,
  Zap,
  Settings,
  Download,
  Split,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const dataTutorial: TutorialSection[] = [
  {
    title: 'Data Browser Overview',
    content: 'The Data Browser is your central hub for viewing, filtering, and managing all collected data items. Browse through text, images, audio, and video content from your scraping jobs.',
    tips: [
      'Use filters to quickly find specific data types or labeled/unlabeled items',
      'Click on any item to preview its full content and metadata',
      'Select multiple items to apply bulk operations like labeling',
    ],
  },
  {
    title: 'Filtering Data',
    content: 'Filter your data by project, data type (text/image/audio/video), and labeling status. The filters help you focus on specific subsets of your data for efficient management.',
    steps: [
      { title: 'Select Project', description: 'First choose a project to view its data' },
      { title: 'Filter by Type', description: 'Optionally filter by text, image, audio, or video' },
      { title: 'Filter by Status', description: 'Show all, labeled only, or unlabeled items' },
    ],
  },
  {
    title: 'Processing Data',
    content: 'Process your data to extract features, detect language, clean text, and compute quality scores. Processing prepares raw data for ML training.',
    tips: [
      '"Process All" runs NLP analysis, text cleaning, and language detection',
      '"Extract Labels" finds labels from metadata fields like categories or tags',
      '"Compute Quality" calculates a quality score for each item',
    ],
    warning: 'Processing large datasets may take several minutes. Check the Workers page for progress.',
  },
  {
    title: 'Bulk Labeling',
    content: 'Select multiple items and apply labels in bulk. Labels are essential for supervised ML training. You can add comma-separated labels to categorize your data.',
    steps: [
      { title: 'Select Items', description: 'Click checkboxes to select items or "Select All"' },
      { title: 'Enter Labels', description: 'Type comma-separated labels (e.g., "positive, review")' },
      { title: 'Apply', description: 'Click "Apply Labels" to add labels to all selected items' },
    ],
  },
  {
    title: 'Data Preview',
    content: 'Click the eye icon or any item to open a detailed preview. For media files, you can play audio/video directly. The preview shows all metadata, labels, quality scores, and source information.',
    tips: [
      'Press ESC to close the preview modal',
      'Download files directly from the preview',
      'View the original source URL for scraped items',
    ],
  },
]

export default function DataPage() {
  const t = useTranslations()
  const searchParams = useSearchParams()
  const preselectedProject = searchParams.get('project')
  const queryClient = useQueryClient()

  const [projectId, setProjectId] = useState(preselectedProject || '')
  const [dataTypeFilter, setDataTypeFilter] = useState('')
  const [labeledFilter, setLabeledFilter] = useState<string>('')
  const [splitFilter, setSplitFilter] = useState<string>('')
  const [selectedItems, setSelectedItems] = useState<string[]>([])
  const [labelInput, setLabelInput] = useState('')
  const [previewItem, setPreviewItem] = useState<any>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 50

  // Close modal on ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && previewItem) {
        setPreviewItem(null)
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [previewItem])

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const { data: dataResponse, isLoading } = useQuery({
    queryKey: ['data', projectId, dataTypeFilter, labeledFilter, currentPage],
    queryFn: () => dataApi.list(projectId, {
      data_type: dataTypeFilter || undefined,
      is_labeled: labeledFilter === 'labeled' ? true : labeledFilter === 'unlabeled' ? false : undefined,
      skip: (currentPage - 1) * itemsPerPage,
      limit: itemsPerPage,
    }),
    enabled: !!projectId,
  })

  // Extract items from paginated response (handle both old and new format)
  const dataItems = dataResponse?.items || dataResponse || []

  const { data: categories } = useQuery({
    queryKey: ['categories', projectId],
    queryFn: () => dataApi.getCategories(projectId),
    enabled: !!projectId,
  })

  const deleteMutation = useMutation({
    mutationFn: dataApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data'] })
      toast.success('Item deleted')
    },
  })

  const bulkLabelMutation = useMutation({
    mutationFn: dataApi.bulkLabel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data'] })
      setSelectedItems([])
      setLabelInput('')
      toast.success('Labels applied')
    },
  })

  const computeQualityMutation = useMutation({
    mutationFn: (recompute: boolean) => dataApi.computeQualityScores(projectId, recompute),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['data'] })
      if (data.processed > 0) {
        toast.success(data.message || `Computed quality scores for ${data.processed} items`)
      } else {
        toast('All items already have quality scores', { icon: 'ℹ️' })
      }
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || error?.message || 'Failed to compute quality scores'
      toast.error(message)
    },
  })

  const extractLabelsMutation = useMutation({
    mutationFn: () => dataApi.extractLabels(projectId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['data'] })
      if (data.labeled > 0) {
        toast.success(data.message || `Extracted labels for ${data.labeled} items`)
      } else {
        toast(`No labels found in metadata. Processed ${data.processed} items but none had labels/tags/categories fields.`, { icon: 'ℹ️' })
      }
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || error?.message || 'Failed to extract labels'
      toast.error(message)
    },
  })

  const processAllMutation = useMutation({
    mutationFn: (reprocess: boolean) => processingApi.processAll(projectId, 'auto', reprocess),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['data'] })
      if (data.processed > 0) {
        toast.success(data.message || `Processed ${data.processed} items`)
      } else {
        toast('All items are already processed', { icon: 'ℹ️' })
      }
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || error?.message || 'Failed to process items'
      toast.error(message)
    },
  })

  const processSelectedMutation = useMutation({
    mutationFn: (itemIds: string[]) => processingApi.batchProcess({ item_ids: itemIds }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['data'] })
      const successCount = data.filter((r: any) => r.success).length
      const failCount = data.filter((r: any) => !r.success).length
      if (successCount > 0) {
        toast.success(`Processed ${successCount} items${failCount > 0 ? `, ${failCount} failed` : ''}`)
      } else if (failCount > 0) {
        toast.error(`Failed to process ${failCount} items`)
      }
      setSelectedItems([])
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || error?.message || 'Failed to process items'
      toast.error(message)
    },
  })

  const toggleSelect = (id: string) => {
    setSelectedItems(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  const selectAll = () => {
    const items = Array.isArray(dataItems) ? dataItems : []
    if (selectedItems.length === items.length) {
      setSelectedItems([])
    } else {
      setSelectedItems(items.map((i: any) => i.id) || [])
    }
  }

  const handleBulkLabel = () => {
    if (!labelInput.trim() || selectedItems.length === 0) return

    bulkLabelMutation.mutate({
      item_ids: selectedItems,
      labels: labelInput.split(',').map(l => l.trim()),
      action: 'add',
    })
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'text': return <FileText className="w-5 h-5" />
      case 'image': return <ImageIcon className="w-5 h-5" />
      case 'audio': return <Music className="w-5 h-5" />
      case 'video': return <Video className="w-5 h-5" />
      default: return <Database className="w-5 h-5" />
    }
  }

  // Use actual totals from API response if available, otherwise fall back to array length
  const stats = {
    total: dataResponse?.total ?? dataItems?.length ?? 0,
    labeled: dataResponse?.labeled_count ?? dataItems?.filter((i: any) => i.is_labeled).length ?? 0,
    processed: dataResponse?.processed_count ?? dataItems?.filter((i: any) => i.is_processed).length ?? 0,
  }

  // Pagination calculations
  const totalPages = Math.ceil(stats.total / itemsPerPage)
  const canGoPrev = currentPage > 1
  const canGoNext = currentPage < totalPages

  // Reset to page 1 when filters change
  const handleFilterChange = (setter: (value: any) => void, value: any) => {
    setter(value)
    setCurrentPage(1)
    setSelectedItems([])
  }

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Data Browser Guide"
        description="Learn how to browse, filter, and manage your collected data"
        sections={dataTutorial}
        storageKey="data-browser"
      />

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">{t('nav.data')}</h1>
        <p className="text-surface-400">{t('data.description') || 'Browse and label collected data'}</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <select
          value={projectId}
          onChange={(e) => handleFilterChange(setProjectId, e.target.value)}
          className="px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
        >
          <option value="">Select a project</option>
          {projects?.map((project: any) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>

        <select
          value={dataTypeFilter}
          onChange={(e) => handleFilterChange(setDataTypeFilter, e.target.value)}
          className="px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
        >
          <option value="">All types</option>
          <option value="text">Text</option>
          <option value="image">Image</option>
          <option value="audio">Audio</option>
          <option value="video">Video</option>
          <option value="structured">Structured</option>
        </select>

        <select
          value={labeledFilter}
          onChange={(e) => handleFilterChange(setLabeledFilter, e.target.value)}
          className="px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
        >
          <option value="">All items</option>
          <option value="labeled">Labeled</option>
          <option value="unlabeled">Unlabeled</option>
        </select>
      </div>

      {/* Stats & Processing Actions */}
      {projectId && (Array.isArray(dataItems) ? dataItems.length > 0 : false) && (
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="flex gap-4">
            <div className="px-4 py-2 rounded-xl bg-surface-800/50 border border-surface-700">
              <span className="text-surface-400 text-sm">Total: </span>
              <span className="font-medium">{stats.total}</span>
            </div>
            <div className="px-4 py-2 rounded-xl bg-green-500/10 border border-green-500/20">
              <span className="text-green-400 text-sm">Labeled: </span>
              <span className="font-medium text-green-400">{stats.labeled}</span>
            </div>
            <div className="px-4 py-2 rounded-xl bg-blue-500/10 border border-blue-500/20">
              <span className="text-blue-400 text-sm">Processed: </span>
              <span className="font-medium text-blue-400">{stats.processed}</span>
            </div>
          </div>
          
          <div className="flex-1" />
          
          {/* Processing Actions */}
          <div className="flex gap-2">
            <button
              onClick={() => processAllMutation.mutate(false)}
              disabled={processAllMutation.isPending}
              className="px-3 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-sm text-white font-medium transition-all flex items-center gap-2 disabled:opacity-50 shadow-lg shadow-purple-500/20"
              title="Process all unprocessed items (NLP analysis, text cleaning, language detection)"
            >
              {processAllMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              Process All
            </button>
            <button
              onClick={() => extractLabelsMutation.mutate()}
              disabled={extractLabelsMutation.isPending}
              className="px-3 py-2 rounded-lg bg-surface-800 hover:bg-surface-700 text-sm text-surface-300 hover:text-white transition-colors flex items-center gap-2 disabled:opacity-50"
              title="Extract labels from metadata (categories, tags, etc.)"
            >
              {extractLabelsMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Tag className="w-4 h-4" />
              )}
              Extract Labels
            </button>
            <button
              onClick={() => computeQualityMutation.mutate(false)}
              disabled={computeQualityMutation.isPending}
              className="px-3 py-2 rounded-lg bg-surface-800 hover:bg-surface-700 text-sm text-surface-300 hover:text-white transition-colors flex items-center gap-2 disabled:opacity-50"
              title="Compute quality scores for items without scores"
            >
              {computeQualityMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Filter className="w-4 h-4" />
              )}
              Compute Quality
            </button>
          </div>
        </div>
      )}

      {/* Bulk Actions */}
      {selectedItems.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4 mb-4 p-4 rounded-xl bg-brand-500/10 border border-brand-500/20"
        >
          <span className="text-sm font-medium">
            {selectedItems.length} item{selectedItems.length > 1 ? 's' : ''} selected
          </span>
          
          {/* Process Selected Button */}
          <button
            onClick={() => processSelectedMutation.mutate(selectedItems)}
            disabled={processSelectedMutation.isPending}
            className="px-3 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-sm text-white font-medium transition-all flex items-center gap-2 disabled:opacity-50"
            title="Process selected items (NLP analysis, text cleaning, etc.)"
          >
            {processSelectedMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            Process Selected
          </button>
          
          <div className="flex-1 flex items-center gap-2">
            <input
              type="text"
              value={labelInput}
              onChange={(e) => setLabelInput(e.target.value)}
              placeholder="Add labels (comma separated)"
              className="flex-1 px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors text-sm"
            />
            <button
              onClick={handleBulkLabel}
              disabled={bulkLabelMutation.isPending}
              className="px-4 py-2 rounded-lg bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition-colors flex items-center gap-2"
            >
              <Tag className="w-4 h-4" />
              Apply Labels
            </button>
          </div>
          <button
            onClick={() => setSelectedItems([])}
            className="text-surface-400 hover:text-white transition-colors"
          >
            Clear selection
          </button>
        </motion.div>
      )}

      {/* Data List */}
      {!projectId ? (
        <div className="text-center py-20">
          <Database className="w-16 h-16 text-surface-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Select a Project</h3>
          <p className="text-surface-400">Choose a project to view its data</p>
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
        </div>
      ) : (Array.isArray(dataItems) && dataItems.length > 0) ? (
        <div className="rounded-2xl glass overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-surface-700">
                <th className="p-4 w-10">
                  <button onClick={selectAll} className="text-surface-400 hover:text-white">
                    {selectedItems.length === (Array.isArray(dataItems) ? dataItems.length : 0) ? (
                      <CheckSquare className="w-5 h-5" />
                    ) : (
                      <Square className="w-5 h-5" />
                    )}
                  </button>
                </th>
                <th className="text-left p-4 text-surface-400 font-medium">Type</th>
                <th className="text-left p-4 text-surface-400 font-medium">Content</th>
                <th className="text-left p-4 text-surface-400 font-medium">Labels</th>
                <th className="text-left p-4 text-surface-400 font-medium">Quality</th>
                <th className="text-left p-4 text-surface-400 font-medium">Date</th>
                <th className="text-right p-4 text-surface-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {dataItems.map((item: any, index: number) => (
                <motion.tr
                  key={item.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.02 }}
                  className="border-b border-surface-800 hover:bg-surface-800/50 transition-colors"
                >
                  <td className="p-4">
                    <button
                      onClick={() => toggleSelect(item.id)}
                      className="text-surface-400 hover:text-white"
                    >
                      {selectedItems.includes(item.id) ? (
                        <CheckSquare className="w-5 h-5 text-brand-400" />
                      ) : (
                        <Square className="w-5 h-5" />
                      )}
                    </button>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2 text-surface-400">
                      {getTypeIcon(item.data_type)}
                      <span className="capitalize text-sm">{item.data_type}</span>
                    </div>
                  </td>
                  <td className="p-4 max-w-md">
                    {item.data_type === 'image' && item.download_url ? (
                      <button
                        onClick={() => setPreviewItem(item)}
                        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
                      >
                        <img
                          src={item.download_url}
                          alt=""
                          className="w-16 h-16 object-cover rounded-lg"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect fill="%23334155" width="100" height="100"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%2394a3b8" font-family="sans-serif"%3ENo Image%3C/text%3E%3C/svg%3E'
                          }}
                        />
                        <Eye className="w-4 h-4 text-surface-400" />
                      </button>
                    ) : item.data_type === 'audio' && item.download_url ? (
                      <button
                        onClick={() => setPreviewItem(item)}
                        className="flex items-center gap-2 text-purple-400 hover:text-purple-300 transition-colors"
                      >
                        <Music className="w-5 h-5" />
                        <span className="text-sm">Audio file</span>
                        <Eye className="w-4 h-4" />
                      </button>
                    ) : item.data_type === 'video' && item.download_url ? (
                      <button
                        onClick={() => setPreviewItem(item)}
                        className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        <Video className="w-5 h-5" />
                        <span className="text-sm">Video file</span>
                        <Eye className="w-4 h-4" />
                      </button>
                    ) : (
                      <p className="truncate text-sm">
                        {item.content?.slice(0, 100) || item.source_url || 'No content'}
                      </p>
                    )}
                  </td>
                  <td className="p-4">
                    <div className="flex flex-wrap gap-1">
                      {item.labels?.map((label: string) => (
                        <span
                          key={label}
                          className="px-2 py-0.5 rounded-full text-xs bg-brand-500/20 text-brand-400"
                        >
                          {label}
                        </span>
                      ))}
                      {(!item.labels || item.labels.length === 0) && (
                        <span className="text-xs text-surface-500">No labels</span>
                      )}
                    </div>
                  </td>
                  <td className="p-4">
                    {item.quality_score !== null && item.quality_score !== undefined ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-surface-700 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              item.quality_score >= 0.8 ? 'bg-green-500' :
                              item.quality_score >= 0.5 ? 'bg-yellow-500' :
                              'bg-red-500'
                            }`}
                            style={{ width: `${item.quality_score * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-surface-400">
                          {(item.quality_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-surface-500">-</span>
                    )}
                  </td>
                  <td className="p-4 text-sm text-surface-400">
                    {formatDate(item.created_at)}
                  </td>
                  <td className="p-4">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setPreviewItem(item)}
                        className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('Delete this item?')) {
                            deleteMutation.mutate(item.id)
                          }
                        }}
                        className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-4 border-t border-surface-700">
              <div className="text-sm text-surface-400">
                Showing {((currentPage - 1) * itemsPerPage) + 1} - {Math.min(currentPage * itemsPerPage, stats.total)} of {stats.total} items
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={!canGoPrev}
                  className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="First page"
                >
                  <ChevronsLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={!canGoPrev}
                  className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Previous page"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                
                <div className="flex items-center gap-1 px-2">
                  {/* Page numbers */}
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum: number
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (currentPage <= 3) {
                      pageNum = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = currentPage - 2 + i
                    }
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                          currentPage === pageNum
                            ? 'bg-brand-500 text-white'
                            : 'hover:bg-surface-700 text-surface-400 hover:text-white'
                        }`}
                      >
                        {pageNum}
                      </button>
                    )
                  })}
                </div>

                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={!canGoNext}
                  className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Next page"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={!canGoNext}
                  className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Last page"
                >
                  <ChevronsRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-20">
          <Database className="w-16 h-16 text-surface-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">No data yet</h3>
          <p className="text-surface-400">Run a scraping job to collect data</p>
        </div>
      )}

      {/* Preview Modal */}
      {previewItem && (
        <div 
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setPreviewItem(null)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface-900 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-surface-800 flex items-center justify-between sticky top-0 bg-surface-900 z-10">
              <h2 className="text-lg font-semibold">Item Details</h2>
              <button
                onClick={() => setPreviewItem(null)}
                className="p-2 rounded-lg hover:bg-surface-800 transition-colors"
                title="Close (ESC)"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              {/* Media Preview */}
              {previewItem.data_type === 'image' && previewItem.download_url && (
                <div className="bg-surface-950 rounded-xl p-4 flex items-center justify-center">
                  <img
                    src={previewItem.download_url}
                    alt=""
                    className="max-w-full max-h-96 rounded-lg object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none'
                      const parent = (e.target as HTMLImageElement).parentElement
                      if (parent) {
                        parent.innerHTML = '<div class="text-red-400 p-4">Failed to load image</div>'
                      }
                    }}
                  />
                </div>
              )}

              {previewItem.data_type === 'audio' && previewItem.download_url && (
                <div className="bg-surface-950 rounded-xl p-4">
                  <audio
                    controls
                    className="w-full"
                    src={previewItem.download_url}
                    onError={(e) => {
                      const parent = e.currentTarget.parentElement
                      if (parent) {
                        parent.innerHTML = '<div class="text-red-400 p-4">Failed to load audio. Format may not be supported by your browser.</div>'
                      }
                    }}
                  >
                    Your browser does not support the audio element.
                  </audio>
                  {previewItem.metadata?.duration && (
                    <div className="mt-2 text-sm text-surface-400">
                      Duration: {Math.floor(previewItem.metadata.duration / 60)}:{(previewItem.metadata.duration % 60).toFixed(0).padStart(2, '0')}
                    </div>
                  )}
                  {previewItem.mime_type && (
                    <div className="mt-1 text-xs text-surface-500">
                      Format: {previewItem.mime_type}
                    </div>
                  )}
                </div>
              )}

              {previewItem.data_type === 'video' && previewItem.download_url && (
                <div className="bg-surface-950 rounded-xl p-4">
                  <video
                    controls
                    className="w-full rounded-lg max-h-96"
                    src={previewItem.download_url}
                    onError={(e) => {
                      const parent = e.currentTarget.parentElement
                      if (parent) {
                        parent.innerHTML = '<div class="text-red-400 p-4">Failed to load video. Format may not be supported by your browser.</div>'
                      }
                    }}
                  >
                    Your browser does not support the video element.
                  </video>
                  {previewItem.metadata?.duration && (
                    <div className="mt-2 text-sm text-surface-400">
                      Duration: {Math.floor(previewItem.metadata.duration / 60)}:{(previewItem.metadata.duration % 60).toFixed(0).padStart(2, '0')}
                    </div>
                  )}
                  {previewItem.metadata?.width && previewItem.metadata?.height && (
                    <div className="mt-1 text-xs text-surface-500">
                      Resolution: {previewItem.metadata.width}x{previewItem.metadata.height}
                    </div>
                  )}
                  {previewItem.mime_type && (
                    <div className="mt-1 text-xs text-surface-500">
                      Format: {previewItem.mime_type}
                    </div>
                  )}
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-surface-400 mb-1">Type</h3>
                  <div className="flex items-center gap-2">
                    {getTypeIcon(previewItem.data_type)}
                    <p className="capitalize">{previewItem.data_type}</p>
                  </div>
                </div>
                
                {previewItem.file_size && (
                  <div>
                    <h3 className="text-sm font-medium text-surface-400 mb-1">File Size</h3>
                    <p>{formatBytes(previewItem.file_size)}</p>
                  </div>
                )}
              </div>
              
              {previewItem.content && (
                <div>
                  <h3 className="text-sm font-medium text-surface-400 mb-1">Content</h3>
                  <p className="whitespace-pre-wrap text-sm bg-surface-800 p-4 rounded-lg max-h-60 overflow-y-auto">
                    {previewItem.content}
                  </p>
                </div>
              )}
              
              {previewItem.source_url && (
                <div>
                  <h3 className="text-sm font-medium text-surface-400 mb-1">Source URL</h3>
                  <a 
                    href={previewItem.source_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-brand-400 hover:text-brand-300 text-sm break-all"
                  >
                    {previewItem.source_url}
                  </a>
                </div>
              )}

              {previewItem.download_url && (
                <div>
                  <h3 className="text-sm font-medium text-surface-400 mb-1">Download</h3>
                  <a 
                    href={previewItem.download_url} 
                    target="_blank"
                    download
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500 text-white hover:bg-brand-600 transition-colors text-sm"
                  >
                    <Download className="w-4 h-4" />
                    Download File
                  </a>
                </div>
              )}
              
              {previewItem.labels?.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-surface-400 mb-1">Labels</h3>
                  <div className="flex flex-wrap gap-2">
                    {previewItem.labels.map((label: string) => (
                      <span
                        key={label}
                        className="px-2 py-1 rounded-lg text-sm bg-brand-500/20 text-brand-400"
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {previewItem.metadata && Object.keys(previewItem.metadata).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-surface-400 mb-2">Metadata</h3>
                  <pre className="text-xs bg-surface-800 p-4 rounded-lg overflow-x-auto max-h-60 overflow-y-auto">
                    {JSON.stringify(previewItem.metadata, null, 2)}
                  </pre>
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4 text-sm pt-4 border-t border-surface-700">
                <div>
                  <span className="text-surface-400">Quality Score:</span>
                  <span className="ml-2">
                    {previewItem.quality_score !== null 
                      ? `${(previewItem.quality_score * 100).toFixed(0)}%` 
                      : '-'}
                  </span>
                </div>
                <div>
                  <span className="text-surface-400">MIME Type:</span>
                  <span className="ml-2 text-xs">
                    {previewItem.mime_type || '-'}
                  </span>
                </div>
                <div>
                  <span className="text-surface-400">Created:</span>
                  <span className="ml-2">{formatDate(previewItem.created_at)}</span>
                </div>
                <div>
                  <span className="text-surface-400">Processed:</span>
                  <span className="ml-2">{previewItem.is_processed ? 'Yes' : 'No'}</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}

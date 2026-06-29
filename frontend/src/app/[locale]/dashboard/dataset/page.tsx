'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { datasetApi, projectsApi, dataApi } from '@/lib/api'
import { formatBytes } from '@/lib/utils'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useTranslations } from 'next-intl'
import {
  BarChart3,
  PieChart,
  TrendingUp,
  Split,
  GitBranch,
  Tag,
  Wand2,
  Search,
  AlertTriangle,
  CheckCircle,
  Loader2,
  RefreshCw,
  Download,
  Layers,
  Target,
  Sparkles,
  FileText,
  Image as ImageIcon,
  Music,
  Video,
  Settings,
  Play,
  Plus,
  Brain,
  Copy,
  Lightbulb,
  X,
  Eye,
  FileCode,
  BookOpen,
  Trash2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const datasetTutorial: TutorialSection[] = [
  {
    title: 'Dataset Manager Overview',
    content: 'The Dataset Manager helps you prepare your collected data for ML training. It provides statistics, splitting tools, versioning, and advanced ML preparation features.',
    tips: [
      'Start by selecting a project from the dropdown',
      'Review statistics before splitting your data',
      'Create versions to track dataset changes over time',
    ],
  },
  {
    title: 'Understanding Statistics',
    content: 'The statistics panel shows key metrics about your dataset including total items, labeled items, storage usage, and class balance.',
    steps: [
      { title: 'Total Items', description: 'Count of all data items in the project' },
      { title: 'Labeled Items', description: 'Items that have been annotated with labels' },
      { title: 'Storage', description: 'Total disk space used by the dataset' },
      { title: 'Class Balance', description: 'Ratio between most and least common labels' },
    ],
    warning: 'A high class imbalance ratio (>10x) may negatively impact model training.',
  },
  {
    title: 'Dataset Splitting',
    content: 'Split your data into training, validation, and test sets. This is essential for proper ML evaluation.',
    steps: [
      { title: 'Train Set (80%)', description: 'Data used to train the model' },
      { title: 'Validation Set (10%)', description: 'Data used to tune hyperparameters' },
      { title: 'Test Set (10%)', description: 'Held-out data for final evaluation' },
    ],
    tips: [
      'Use "Stratify by labels" to maintain class distribution across splits',
      'Enable "Shuffle data" for random distribution',
      'Click "Reset" to clear all split assignments',
    ],
  },
  {
    title: 'Dataset Versioning',
    content: 'Create versions to snapshot your dataset at specific points. This helps track changes and reproduce experiments.',
    steps: [
      { title: 'Create Version', description: 'Snapshot current dataset state with a version name (e.g., v1.0.0)' },
      { title: 'Add Description', description: 'Document what changed in this version' },
      { title: 'Track History', description: 'View all versions with item counts and split info' },
    ],
  },
  {
    title: 'ML Preparation Tools',
    content: 'Advanced tools to prepare your dataset for machine learning.',
    steps: [
      { title: 'Generate Embeddings', description: 'Create vector representations for similarity search and clustering' },
      { title: 'Data Augmentation', description: 'Expand your dataset with synthetic variations' },
      { title: 'Annotation Studio', description: 'Label data with bounding boxes, NER tags, or classifications' },
    ],
    tips: [
      'Generate embeddings before finding duplicates',
      'Use augmentation to balance underrepresented classes',
      'Export annotations in COCO format for computer vision',
    ],
  },
  {
    title: 'Active Learning & Duplicates',
    content: 'Use smart features to improve dataset quality efficiently.',
    steps: [
      { title: 'Active Learning', description: 'Get suggestions for which items to label next based on model uncertainty' },
      { title: 'Find Duplicates', description: 'Detect and remove similar or duplicate items using embeddings' },
      { title: 'Dataset Card', description: 'Create HuggingFace-style documentation for your dataset' },
    ],
    warning: 'Always generate embeddings first before using similarity-based features.',
  },
]

export default function DatasetPage() {
  const queryClient = useQueryClient()
  const [projectId, setProjectId] = useState('')
  const [splitConfig, setSplitConfig] = useState({
    train_ratio: 0.8,
    val_ratio: 0.1,
    test_ratio: 0.1,
    stratify_by: 'labels',
    shuffle: true,
  })
  const [versionName, setVersionName] = useState('')
  const [versionDescription, setVersionDescription] = useState('')
  const [showSplitModal, setShowSplitModal] = useState(false)
  const [showVersionModal, setShowVersionModal] = useState(false)
  const [showActiveLearningModal, setShowActiveLearningModal] = useState(false)
  const [showDuplicatesModal, setShowDuplicatesModal] = useState(false)
  const [showDatasetCardModal, setShowDatasetCardModal] = useState(false)
  const [activeLearningConfig, setActiveLearningConfig] = useState({
    strategy: 'uncertainty',
    batch_size: 10,
    exclude_labeled: true,
  })
  const [duplicateThreshold, setDuplicateThreshold] = useState(0.95)
  const [datasetCard, setDatasetCard] = useState({
    title: '',
    description: '',
    license: 'mit',
    languages: [] as string[],
    task_categories: [] as string[],
    tags: [] as string[],
  })
  const [newTag, setNewTag] = useState('')
  const [newLanguage, setNewLanguage] = useState('')

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['dataset-stats', projectId],
    queryFn: () => datasetApi.getStatistics(projectId),
    enabled: !!projectId,
  })

  const { data: splitStats, refetch: refetchSplitStats } = useQuery({
    queryKey: ['split-stats', projectId],
    queryFn: () => datasetApi.getSplitStats(projectId),
    enabled: !!projectId,
  })

  const { data: versions } = useQuery({
    queryKey: ['versions', projectId],
    queryFn: () => datasetApi.listVersions(projectId),
    enabled: !!projectId,
  })

  const autoSplitMutation = useMutation({
    mutationFn: (data: any) => datasetApi.autoSplit(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['dataset-stats'] })
      queryClient.invalidateQueries({ queryKey: ['split-stats'] })
      queryClient.invalidateQueries({ queryKey: ['versions'] })
      toast.success(`Dataset split: ${data.train} train, ${data.val} val, ${data.test} test`)
      setShowSplitModal(false)
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Split failed')
    },
  })

  const resetSplitMutation = useMutation({
    mutationFn: () => datasetApi.resetSplits(projectId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['split-stats'] })
      toast.success(`Reset ${data.reset} items to unassigned`)
    },
  })

  const createVersionMutation = useMutation({
    mutationFn: (data: any) => datasetApi.createVersion(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['versions'] })
      toast.success('Version created')
      setShowVersionModal(false)
      setVersionName('')
      setVersionDescription('')
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to create version')
    },
  })

  const generateEmbeddingsMutation = useMutation({
    mutationFn: (recompute: boolean) => datasetApi.generateEmbeddings(projectId, recompute),
    onSuccess: (data) => {
      toast.success(`Generated embeddings for ${data.processed} items`)
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to generate embeddings')
    },
  })

  // Active Learning
  const { data: activeLearningData, refetch: refetchActiveLearning, isFetching: activeLearningLoading } = useQuery({
    queryKey: ['active-learning', projectId, activeLearningConfig],
    queryFn: () => datasetApi.getActiveLearning(projectId, activeLearningConfig),
    enabled: !!projectId && showActiveLearningModal,
  })

  // Find Duplicates
  const [selectedDuplicates, setSelectedDuplicates] = useState<Set<string>>(new Set())
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())
  const [expandedPairIndex, setExpandedPairIndex] = useState<number | null>(null)
  const [itemDetailsCache, setItemDetailsCache] = useState<Record<string, any>>({})
  const [loadingItemDetails, setLoadingItemDetails] = useState<Set<string>>(new Set())

  const findDuplicatesMutation = useMutation({
    mutationFn: () => datasetApi.findDuplicatesByEmbedding(projectId, duplicateThreshold),
    onSuccess: (data) => {
      toast.success(`Found ${data.count} potential duplicates`)
      setSelectedDuplicates(new Set())
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to find duplicates')
    },
  })

  const deleteDataItemMutation = useMutation({
    mutationFn: (id: string) => dataApi.delete(id),
    onSuccess: (_, id) => {
      setDeletingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(id)
        return newSet
      })
      setSelectedDuplicates(prev => {
        const newSet = new Set(prev)
        newSet.delete(id)
        return newSet
      })
      queryClient.invalidateQueries({ queryKey: ['dataset-stats'] })
      toast.success('Item deleted')
    },
    onError: (error: any, id) => {
      setDeletingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(id)
        return newSet
      })
      toast.error(error?.response?.data?.detail || 'Failed to delete item')
    },
  })

  const handleDeleteDuplicate = (id: string) => {
    setDeletingIds(prev => new Set(prev).add(id))
    deleteDataItemMutation.mutate(id)
  }

  const handleDeleteSelectedDuplicates = async () => {
    if (selectedDuplicates.size === 0) return
    if (!confirm(`Are you sure you want to delete ${selectedDuplicates.size} items?`)) return
    
    const idsToDelete = Array.from(selectedDuplicates)
    setDeletingIds(new Set(idsToDelete))
    
    for (const id of idsToDelete) {
      try {
        await dataApi.delete(id)
        setSelectedDuplicates(prev => {
          const newSet = new Set(prev)
          newSet.delete(id)
          return newSet
        })
      } catch (error) {
        console.error(`Failed to delete ${id}`, error)
      }
    }
    
    setDeletingIds(new Set())
    queryClient.invalidateQueries({ queryKey: ['dataset-stats'] })
    toast.success(`Deleted ${idsToDelete.length} duplicate items`)
    findDuplicatesMutation.mutate() // Refresh duplicates list
  }

  const toggleDuplicateSelection = (id: string) => {
    setSelectedDuplicates(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const selectAllItem2s = () => {
    if (!findDuplicatesMutation.data?.duplicates) return
    const item2Ids = findDuplicatesMutation.data.duplicates.map((p: any) => p.item2_id)
    setSelectedDuplicates(new Set(item2Ids))
  }

  const fetchItemDetails = async (itemId: string) => {
    if (itemDetailsCache[itemId]) return itemDetailsCache[itemId]
    
    setLoadingItemDetails(prev => new Set(prev).add(itemId))
    try {
      const data = await dataApi.get(itemId)
      setItemDetailsCache(prev => ({ ...prev, [itemId]: data }))
      return data
    } catch (error) {
      console.error(`Failed to fetch item ${itemId}`, error)
      return null
    } finally {
      setLoadingItemDetails(prev => {
        const newSet = new Set(prev)
        newSet.delete(itemId)
        return newSet
      })
    }
  }

  const toggleExpandPair = async (index: number, item1Id: string, item2Id: string) => {
    if (expandedPairIndex === index) {
      setExpandedPairIndex(null)
    } else {
      setExpandedPairIndex(index)
      // Fetch details for both items
      await Promise.all([
        fetchItemDetails(item1Id),
        fetchItemDetails(item2Id)
      ])
    }
  }

  const renderItemPreview = (item: any) => {
    if (!item) return <p className="text-surface-500 italic">Failed to load</p>
    
    const content = item.content || item.text_content || ''
    const dataType = item.data_type || 'text'
    
    if (dataType === 'image' && item.file_url) {
      return (
        <div className="space-y-2">
          <img 
            src={item.file_url} 
            alt="Preview" 
            className="max-h-48 rounded-lg object-contain bg-surface-800"
          />
          {item.metadata?.alt_text && (
            <p className="text-xs text-surface-400">{item.metadata.alt_text}</p>
          )}
        </div>
      )
    }
    
    if (dataType === 'text' || content) {
      return (
        <div className="space-y-2">
          <p className="text-sm text-surface-300 whitespace-pre-wrap line-clamp-6">
            {content.slice(0, 500)}{content.length > 500 ? '...' : ''}
          </p>
          <div className="text-xs text-surface-500">
            {content.length} characters
          </div>
        </div>
      )
    }
    
    if (item.source_url) {
      return (
        <div className="space-y-1">
          <p className="text-sm text-surface-400">Source:</p>
          <a 
            href={item.source_url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-xs text-brand-400 hover:underline truncate block"
          >
            {item.source_url}
          </a>
        </div>
      )
    }
    
    return <p className="text-surface-500 italic">No preview available</p>
  }

  // Dataset Card
  const { data: existingCard, refetch: refetchCard } = useQuery({
    queryKey: ['dataset-card', projectId],
    queryFn: () => datasetApi.getDatasetCard(projectId),
    enabled: !!projectId && showDatasetCardModal,
    retry: false,
  })

  const createCardMutation = useMutation({
    mutationFn: (data: any) => datasetApi.createDatasetCard(data),
    onSuccess: () => {
      toast.success('Dataset card created')
      setShowDatasetCardModal(false)
      refetchCard()
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to create card')
    },
  })

  const updateCardMutation = useMutation({
    mutationFn: (data: any) => datasetApi.updateDatasetCard(projectId, data),
    onSuccess: () => {
      toast.success('Dataset card updated')
      refetchCard()
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to update card')
    },
  })

  // Effect to load existing card data
  useEffect(() => {
    if (existingCard && showDatasetCardModal) {
      setDatasetCard({
        title: existingCard.title || '',
        description: existingCard.description || '',
        license: existingCard.license || 'mit',
        languages: existingCard.languages || [],
        task_categories: existingCard.task_categories || [],
        tags: existingCard.tags || [],
      })
    }
  }, [existingCard, showDatasetCardModal])

  const getDataTypeIcon = (type: string) => {
    switch (type) {
      case 'text': return <FileText className="w-4 h-4" />
      case 'image': return <ImageIcon className="w-4 h-4" />
      case 'audio': return <Music className="w-4 h-4" />
      case 'video': return <Video className="w-4 h-4" />
      default: return <Layers className="w-4 h-4" />
    }
  }

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Dataset Manager Guide"
        description="Learn how to prepare your data for ML training"
        sections={datasetTutorial}
        storageKey="dataset"
      />

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Dataset Manager</h1>
        <p className="text-surface-400">Manage splits, versions, statistics, and ML training preparation</p>
      </div>

      {/* Project Selector */}
      <div className="mb-6">
        <select
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          className="px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors min-w-[300px]"
        >
          <option value="">Select a project</option>
          {projects?.map((project: any) => (
            <option key={project.id} value={project.id}>
              {project.name} ({project.data_count} items)
            </option>
          ))}
        </select>
      </div>

      {!projectId ? (
        <div className="text-center py-20">
          <BarChart3 className="w-16 h-16 text-surface-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Select a Project</h3>
          <p className="text-surface-400">Choose a project to view dataset statistics and manage ML preparation</p>
        </div>
      ) : statsLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
        </div>
      ) : stats ? (
        <div className="space-y-8">
          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-6 rounded-2xl glass"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-surface-400">Total Items</span>
                <Layers className="w-5 h-5 text-brand-400" />
              </div>
              <p className="text-3xl font-bold">{stats.total_items.toLocaleString()}</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="p-6 rounded-2xl glass"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-surface-400">Labeled</span>
                <Tag className="w-5 h-5 text-green-400" />
              </div>
              <p className="text-3xl font-bold text-green-400">{stats.labeled_items.toLocaleString()}</p>
              <p className="text-sm text-surface-500">{((stats.labeled_items / stats.total_items) * 100).toFixed(1)}%</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="p-6 rounded-2xl glass"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-surface-400">Storage</span>
                <Download className="w-5 h-5 text-blue-400" />
              </div>
              <p className="text-3xl font-bold text-blue-400">{formatBytes(stats.total_storage_bytes)}</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className={`p-6 rounded-2xl glass ${stats.is_balanced ? 'border-green-500/20' : 'border-yellow-500/20'} border`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-surface-400">Class Balance</span>
                {stats.is_balanced ? (
                  <CheckCircle className="w-5 h-5 text-green-400" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-yellow-400" />
                )}
              </div>
              <p className={`text-3xl font-bold ${stats.is_balanced ? 'text-green-400' : 'text-yellow-400'}`}>
                {stats.class_imbalance_ratio ? `${stats.class_imbalance_ratio.toFixed(1)}x` : 'N/A'}
              </p>
              <p className="text-sm text-surface-500">{stats.is_balanced ? 'Balanced' : 'Imbalanced'}</p>
            </motion.div>
          </div>

          {/* Split Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="p-6 rounded-2xl glass"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Split className="w-5 h-5" />
                  Dataset Splits
                </h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowSplitModal(true)}
                    className="px-3 py-1.5 rounded-lg bg-brand-500 text-white text-sm hover:bg-brand-600 transition-colors flex items-center gap-1"
                  >
                    <Wand2 className="w-4 h-4" />
                    Auto Split
                  </button>
                  <button
                    onClick={() => resetSplitMutation.mutate()}
                    disabled={resetSplitMutation.isPending}
                    className="px-3 py-1.5 rounded-lg bg-surface-700 text-surface-300 text-sm hover:bg-surface-600 transition-colors"
                  >
                    Reset
                  </button>
                </div>
              </div>

              {splitStats && (
                <div className="space-y-4">
                  <div className="flex gap-2 h-8 rounded-lg overflow-hidden">
                    <div 
                      className="bg-green-500 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(splitStats.train_count / splitStats.total) * 100}%` }}
                    >
                      {splitStats.train_count > 0 && 'Train'}
                    </div>
                    <div 
                      className="bg-blue-500 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(splitStats.val_count / splitStats.total) * 100}%` }}
                    >
                      {splitStats.val_count > 0 && 'Val'}
                    </div>
                    <div 
                      className="bg-purple-500 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(splitStats.test_count / splitStats.total) * 100}%` }}
                    >
                      {splitStats.test_count > 0 && 'Test'}
                    </div>
                    <div 
                      className="bg-surface-600 flex items-center justify-center text-xs font-medium text-surface-300"
                      style={{ width: `${(splitStats.unassigned_count / splitStats.total) * 100}%` }}
                    >
                      {splitStats.unassigned_count > 0 && 'Unassigned'}
                    </div>
                  </div>

                  <div className="grid grid-cols-4 gap-2 text-sm">
                    <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                      <p className="text-green-400 font-medium">{splitStats.train_count.toLocaleString()}</p>
                      <p className="text-surface-400 text-xs">Train</p>
                    </div>
                    <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                      <p className="text-blue-400 font-medium">{splitStats.val_count.toLocaleString()}</p>
                      <p className="text-surface-400 text-xs">Validation</p>
                    </div>
                    <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                      <p className="text-purple-400 font-medium">{splitStats.test_count.toLocaleString()}</p>
                      <p className="text-surface-400 text-xs">Test</p>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-700/50 border border-surface-600">
                      <p className="text-surface-300 font-medium">{splitStats.unassigned_count.toLocaleString()}</p>
                      <p className="text-surface-400 text-xs">Unassigned</p>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Label Distribution */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="p-6 rounded-2xl glass"
            >
              <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                <Tag className="w-5 h-5" />
                Label Distribution
              </h3>
              
              {stats.label_distribution.length > 0 ? (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {stats.label_distribution.slice(0, 10).map((item: any) => (
                    <div key={item.label} className="flex items-center gap-3">
                      <span className="text-sm text-surface-300 w-32 truncate">{item.label}</span>
                      <div className="flex-1 h-6 bg-surface-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-brand-500 to-purple-500 rounded-full"
                          style={{ width: `${item.percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-surface-400 w-16 text-right">{item.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-surface-500 text-center py-8">No labels found</p>
              )}
            </motion.div>
          </div>

          {/* Data Types & Quality */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Data Type Distribution */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="p-6 rounded-2xl glass"
            >
              <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                <PieChart className="w-5 h-5" />
                Data Types
              </h3>
              
              <div className="space-y-3">
                {stats.data_type_distribution.map((item: any) => (
                  <div key={item.data_type} className="flex items-center justify-between p-3 rounded-lg bg-surface-800/50">
                    <div className="flex items-center gap-3">
                      {getDataTypeIcon(item.data_type)}
                      <span className="capitalize">{item.data_type}</span>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{item.count.toLocaleString()}</p>
                      <p className="text-xs text-surface-500">{item.percentage.toFixed(1)}%</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Quality Distribution */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="p-6 rounded-2xl glass"
            >
              <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5" />
                Quality Distribution
              </h3>
              
              {stats.avg_quality_score !== null ? (
                <>
                  <div className="mb-4 p-4 rounded-lg bg-surface-800/50">
                    <p className="text-surface-400 text-sm">Average Quality Score</p>
                    <p className="text-2xl font-bold text-brand-400">{(stats.avg_quality_score * 100).toFixed(1)}%</p>
                  </div>
                  
                  <div className="space-y-2">
                    {stats.quality_distribution.map((item: any) => (
                      <div key={item.range} className="flex items-center gap-3">
                        <span className="text-sm text-surface-400 w-16">{item.range}</span>
                        <div className="flex-1 h-4 bg-surface-700 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              item.range.startsWith('0.8') ? 'bg-green-500' :
                              item.range.startsWith('0.6') ? 'bg-blue-500' :
                              item.range.startsWith('0.4') ? 'bg-yellow-500' :
                              'bg-red-500'
                            }`}
                            style={{ width: `${item.percentage}%` }}
                          />
                        </div>
                        <span className="text-sm text-surface-500 w-12 text-right">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-surface-500 text-center py-8">No quality scores computed</p>
              )}
            </motion.div>
          </div>

          {/* Versions & Actions */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Versions */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              className="p-6 rounded-2xl glass"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <GitBranch className="w-5 h-5" />
                  Dataset Versions
                </h3>
                <button
                  onClick={() => setShowVersionModal(true)}
                  className="px-3 py-1.5 rounded-lg bg-surface-700 text-surface-300 text-sm hover:bg-surface-600 transition-colors flex items-center gap-1"
                >
                  <Plus className="w-4 h-4" />
                  New Version
                </button>
              </div>
              
              {versions && versions.length > 0 ? (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {versions.map((version: any) => (
                    <div key={version.id} className="flex items-center justify-between p-3 rounded-lg bg-surface-800/50">
                      <div>
                        <p className="font-medium flex items-center gap-2">
                          {version.version}
                          {version.is_published && (
                            <span className="px-1.5 py-0.5 rounded text-xs bg-green-500/20 text-green-400">Published</span>
                          )}
                        </p>
                        <p className="text-xs text-surface-500">{version.item_count} items</p>
                      </div>
                      <div className="text-right text-xs text-surface-500">
                        <p>{version.train_count} train</p>
                        <p>{version.val_count} val / {version.test_count} test</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-surface-500 text-center py-8">No versions created yet</p>
              )}
            </motion.div>

            {/* ML Actions */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 }}
              className="p-6 rounded-2xl glass"
            >
              <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                <Sparkles className="w-5 h-5" />
                ML Preparation
              </h3>
              
              <div className="space-y-3">
                <button
                  onClick={() => generateEmbeddingsMutation.mutate(false)}
                  disabled={generateEmbeddingsMutation.isPending}
                  className="w-full p-4 rounded-xl bg-gradient-to-r from-purple-600/20 to-indigo-600/20 border border-purple-500/30 hover:border-purple-500/50 transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3">
                    <Search className="w-5 h-5 text-purple-400" />
                    <div className="text-left">
                      <p className="font-medium">Generate Embeddings</p>
                      <p className="text-xs text-surface-500">For similarity search & clustering</p>
                    </div>
                  </div>
                  {generateEmbeddingsMutation.isPending ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Play className="w-5 h-5 text-surface-400 group-hover:text-purple-400 transition-colors" />
                  )}
                </button>
                
                <a
                  href={`/dashboard/dataset/augmentation?project=${projectId}`}
                  className="w-full p-4 rounded-xl bg-gradient-to-r from-green-600/20 to-emerald-600/20 border border-green-500/30 hover:border-green-500/50 transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3">
                    <Wand2 className="w-5 h-5 text-green-400" />
                    <div className="text-left">
                      <p className="font-medium">Data Augmentation</p>
                      <p className="text-xs text-surface-500">Expand dataset with variations</p>
                    </div>
                  </div>
                  <Settings className="w-5 h-5 text-surface-400 group-hover:text-green-400 transition-colors" />
                </a>
                
                <a
                  href={`/dashboard/dataset/annotations?project=${projectId}`}
                  className="w-full p-4 rounded-xl bg-gradient-to-r from-blue-600/20 to-cyan-600/20 border border-blue-500/30 hover:border-blue-500/50 transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3">
                    <Target className="w-5 h-5 text-blue-400" />
                    <div className="text-left">
                      <p className="font-medium">Annotation Studio</p>
                      <p className="text-xs text-surface-500">BBox, segmentation, NER annotations</p>
                    </div>
                  </div>
                  <Settings className="w-5 h-5 text-surface-400 group-hover:text-blue-400 transition-colors" />
                </a>
              </div>
            </motion.div>
          </div>

          {/* Advanced ML Tools */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Active Learning */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1 }}
              className="p-6 rounded-2xl glass"
            >
              <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                <Brain className="w-5 h-5 text-orange-400" />
                Active Learning
              </h3>
              <p className="text-sm text-surface-400 mb-4">
                Get smart suggestions for which items to label next
              </p>
              <button
                onClick={() => setShowActiveLearningModal(true)}
                className="w-full px-4 py-3 rounded-xl bg-orange-500/10 text-orange-400 border border-orange-500/30 hover:border-orange-500/50 transition-colors flex items-center justify-center gap-2"
              >
                <Lightbulb className="w-5 h-5" />
                Get Suggestions
              </button>
            </motion.div>

            {/* Find Duplicates */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.1 }}
              className="p-6 rounded-2xl glass"
            >
              <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                <Copy className="w-5 h-5 text-red-400" />
                Find Duplicates
              </h3>
              <p className="text-sm text-surface-400 mb-4">
                Detect similar or duplicate items using embeddings
              </p>
              <button
                onClick={() => setShowDuplicatesModal(true)}
                className="w-full px-4 py-3 rounded-xl bg-red-500/10 text-red-400 border border-red-500/30 hover:border-red-500/50 transition-colors flex items-center justify-center gap-2"
              >
                <Search className="w-5 h-5" />
                Find Duplicates
              </button>
            </motion.div>

            {/* Dataset Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.2 }}
              className="p-6 rounded-2xl glass"
            >
              <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                <BookOpen className="w-5 h-5 text-cyan-400" />
                Dataset Card
              </h3>
              <p className="text-sm text-surface-400 mb-4">
                Create documentation for your dataset (HuggingFace style)
              </p>
              <button
                onClick={() => setShowDatasetCardModal(true)}
                className="w-full px-4 py-3 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 hover:border-cyan-500/50 transition-colors flex items-center justify-center gap-2"
              >
                <FileCode className="w-5 h-5" />
                {existingCard ? 'Edit Card' : 'Create Card'}
              </button>
            </motion.div>
          </div>

          {/* Recommendations */}
          {stats.recommendations && stats.recommendations.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1 }}
              className="p-6 rounded-2xl glass border border-yellow-500/20"
            >
              <h3 className="text-lg font-semibold flex items-center gap-2 mb-4 text-yellow-400">
                <AlertTriangle className="w-5 h-5" />
                Recommendations
              </h3>
              
              <ul className="space-y-2">
                {stats.recommendations.map((rec: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-surface-300">
                    <span className="text-yellow-400">•</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </motion.div>
          )}
        </div>
      ) : null}

      {/* Auto Split Modal */}
      {showSplitModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface-900 rounded-2xl max-w-md w-full p-6"
          >
            <h2 className="text-xl font-semibold mb-4">Auto Split Dataset</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-surface-400 mb-1">Train Ratio</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={splitConfig.train_ratio}
                  onChange={(e) => setSplitConfig({ ...splitConfig, train_ratio: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                />
              </div>
              
              <div>
                <label className="block text-sm text-surface-400 mb-1">Validation Ratio</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={splitConfig.val_ratio}
                  onChange={(e) => setSplitConfig({ ...splitConfig, val_ratio: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                />
              </div>
              
              <div>
                <label className="block text-sm text-surface-400 mb-1">Test Ratio</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={splitConfig.test_ratio}
                  onChange={(e) => setSplitConfig({ ...splitConfig, test_ratio: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                />
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="stratify"
                  checked={splitConfig.stratify_by === 'labels'}
                  onChange={(e) => setSplitConfig({ ...splitConfig, stratify_by: e.target.checked ? 'labels' : '' })}
                  className="rounded"
                />
                <label htmlFor="stratify" className="text-sm text-surface-400">Stratify by labels</label>
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="shuffle"
                  checked={splitConfig.shuffle}
                  onChange={(e) => setSplitConfig({ ...splitConfig, shuffle: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="shuffle" className="text-sm text-surface-400">Shuffle data</label>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowSplitModal(false)}
                className="px-4 py-2 rounded-lg text-surface-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => autoSplitMutation.mutate({
                  project_id: projectId,
                  config: splitConfig,
                  create_version: true,
                })}
                disabled={autoSplitMutation.isPending}
                className="px-4 py-2 rounded-lg bg-brand-500 text-white hover:bg-brand-600 transition-colors flex items-center gap-2"
              >
                {autoSplitMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Split Dataset
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Create Version Modal */}
      {showVersionModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface-900 rounded-2xl max-w-md w-full p-6"
          >
            <h2 className="text-xl font-semibold mb-4">Create Dataset Version</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-surface-400 mb-1">Version Name</label>
                <input
                  type="text"
                  placeholder="v1.0.0"
                  value={versionName}
                  onChange={(e) => setVersionName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                />
              </div>
              
              <div>
                <label className="block text-sm text-surface-400 mb-1">Description</label>
                <textarea
                  placeholder="Describe this version..."
                  value={versionDescription}
                  onChange={(e) => setVersionDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 h-24 resize-none"
                />
              </div>
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowVersionModal(false)}
                className="px-4 py-2 rounded-lg text-surface-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => createVersionMutation.mutate({
                  project_id: projectId,
                  version: versionName,
                  description: versionDescription,
                })}
                disabled={createVersionMutation.isPending || !versionName}
                className="px-4 py-2 rounded-lg bg-brand-500 text-white hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {createVersionMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Create Version
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Active Learning Modal */}
      {showActiveLearningModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface-900 rounded-2xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Brain className="w-6 h-6 text-orange-400" />
                Active Learning Suggestions
              </h2>
              <button
                onClick={() => setShowActiveLearningModal(false)}
                className="p-2 rounded-lg hover:bg-surface-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Config */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div>
                <label className="block text-sm text-surface-400 mb-1">Strategy</label>
                <select
                  value={activeLearningConfig.strategy}
                  onChange={(e) => setActiveLearningConfig({ ...activeLearningConfig, strategy: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                >
                  <option value="uncertainty">Uncertainty</option>
                  <option value="diversity">Diversity</option>
                  <option value="random">Random</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-surface-400 mb-1">Batch Size</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={activeLearningConfig.batch_size}
                  onChange={(e) => setActiveLearningConfig({ ...activeLearningConfig, batch_size: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={() => refetchActiveLearning()}
                  disabled={activeLearningLoading}
                  className="w-full px-4 py-2 rounded-lg bg-orange-500 text-white hover:bg-orange-600 transition-colors flex items-center justify-center gap-2"
                >
                  {activeLearningLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                  Refresh
                </button>
              </div>
            </div>

            {/* Suggestions */}
            <div className="space-y-3">
              {activeLearningData?.suggestions?.length > 0 ? (
                <>
                  <div className="flex items-center justify-between text-sm text-surface-400 mb-2">
                    <span>{activeLearningData.suggestions.length} suggestions ({activeLearningData.strategy_used})</span>
                    <span>{activeLearningData.total_unlabeled} unlabeled items</span>
                  </div>
                  {activeLearningData.suggestions.map((item: any) => (
                    <div key={item.item_id} className="p-4 rounded-xl bg-surface-800/50 border border-surface-700">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              item.data_type === 'text' ? 'bg-blue-500/20 text-blue-400' :
                              item.data_type === 'image' ? 'bg-green-500/20 text-green-400' :
                              'bg-surface-700 text-surface-400'
                            }`}>
                              {item.data_type}
                            </span>
                            <span className="text-xs text-surface-500">{item.reason}</span>
                          </div>
                          <p className="text-sm text-surface-300 line-clamp-2">
                            {item.preview || 'No preview available'}
                          </p>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="text-lg font-bold text-orange-400">
                            {(item.uncertainty_score * 100).toFixed(0)}%
                          </div>
                          <div className="text-xs text-surface-500">uncertainty</div>
                        </div>
                      </div>
                      <div className="mt-3 flex gap-2">
                        <a
                          href={`/dashboard/dataset/annotations?project=${projectId}`}
                          className="px-3 py-1.5 rounded-lg bg-orange-500/20 text-orange-400 text-sm hover:bg-orange-500/30 transition-colors"
                        >
                          Label Now
                        </a>
                        <button
                          onClick={() => navigator.clipboard.writeText(item.item_id)}
                          className="px-3 py-1.5 rounded-lg bg-surface-700 text-surface-300 text-sm hover:bg-surface-600 transition-colors"
                        >
                          Copy ID
                        </button>
                      </div>
                    </div>
                  ))}
                </>
              ) : activeLearningLoading ? (
                <div className="text-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-surface-400 mx-auto mb-4" />
                  <p className="text-surface-400">Loading suggestions...</p>
                </div>
              ) : (
                <div className="text-center py-12">
                  <Brain className="w-12 h-12 text-surface-500 mx-auto mb-4" />
                  <p className="text-surface-400">Click Refresh to get suggestions</p>
                  <p className="text-sm text-surface-500 mt-1">Make sure you have unlabeled items</p>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}

      {/* Find Duplicates Modal */}
      {showDuplicatesModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface-900 rounded-2xl max-w-3xl w-full p-6 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Copy className="w-6 h-6 text-red-400" />
                Find & Remove Duplicates
              </h2>
              <button
                onClick={() => {
                  setShowDuplicatesModal(false)
                  setSelectedDuplicates(new Set())
                }}
                className="p-2 rounded-lg hover:bg-surface-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Config */}
            <div className="flex gap-4 mb-6">
              <div className="flex-1">
                <label className="block text-sm text-surface-400 mb-1">
                  Similarity Threshold ({(duplicateThreshold * 100).toFixed(0)}%)
                </label>
                <input
                  type="range"
                  min="0.7"
                  max="1"
                  step="0.01"
                  value={duplicateThreshold}
                  onChange={(e) => setDuplicateThreshold(parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-surface-500 mt-1">
                  <span>70% (more matches)</span>
                  <span>100% (exact)</span>
                </div>
              </div>
              <div className="flex items-end">
                <button
                  onClick={() => findDuplicatesMutation.mutate()}
                  disabled={findDuplicatesMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-brand-500 text-white hover:bg-brand-600 transition-colors flex items-center gap-2"
                >
                  {findDuplicatesMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  Find
                </button>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20 mb-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-yellow-400 mt-0.5" />
                <div className="text-sm">
                  <p className="text-yellow-400 font-medium">Generate embeddings first!</p>
                  <p className="text-surface-400">Make sure you've generated embeddings for your data before finding duplicates.</p>
                </div>
              </div>
            </div>

            {/* Action Bar for Duplicates */}
            {findDuplicatesMutation.data?.duplicates?.length > 0 && (
              <div className="flex items-center justify-between p-4 rounded-xl bg-surface-800 mb-4">
                <div className="flex items-center gap-4">
                  <span className="text-sm text-surface-400">
                    {selectedDuplicates.size} selected
                  </span>
                  <button
                    onClick={selectAllItem2s}
                    className="text-sm text-brand-400 hover:text-brand-300 transition-colors"
                  >
                    Select all Item 2s
                  </button>
                  <button
                    onClick={() => setSelectedDuplicates(new Set())}
                    className="text-sm text-surface-400 hover:text-white transition-colors"
                  >
                    Clear selection
                  </button>
                </div>
                <button
                  onClick={handleDeleteSelectedDuplicates}
                  disabled={selectedDuplicates.size === 0 || deletingIds.size > 0}
                  className="px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                  {deletingIds.size > 0 ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      Delete Selected ({selectedDuplicates.size})
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Results */}
            <div className="space-y-3">
              {findDuplicatesMutation.data?.duplicates?.length > 0 ? (
                <>
                  <div className="text-sm text-surface-400 mb-2">
                    Found {findDuplicatesMutation.data.count} potential duplicate pairs
                  </div>
                  {findDuplicatesMutation.data.duplicates.slice(0, 50).map((pair: any, idx: number) => {
                    const isItem1Deleting = deletingIds.has(pair.item1_id)
                    const isItem2Deleting = deletingIds.has(pair.item2_id)
                    const isItem1Selected = selectedDuplicates.has(pair.item1_id)
                    const isItem2Selected = selectedDuplicates.has(pair.item2_id)
                    const isExpanded = expandedPairIndex === idx
                    const item1Details = itemDetailsCache[pair.item1_id]
                    const item2Details = itemDetailsCache[pair.item2_id]
                    const isLoadingItem1 = loadingItemDetails.has(pair.item1_id)
                    const isLoadingItem2 = loadingItemDetails.has(pair.item2_id)
                    
                    return (
                      <div key={idx} className={`rounded-xl bg-surface-800/50 border transition-all ${
                        isExpanded ? 'border-brand-500/50' : 'border-surface-700'
                      }`}>
                        {/* Header Row */}
                        <div className="p-4">
                          <div className="flex items-center gap-4">
                            {/* Item 1 */}
                            <div className={`flex-1 p-3 rounded-lg border transition-all ${
                              isItem1Selected 
                                ? 'bg-red-500/10 border-red-500/50' 
                                : 'bg-surface-700/50 border-surface-600'
                            }`}>
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                  <input
                                    type="checkbox"
                                    checked={isItem1Selected}
                                    onChange={() => toggleDuplicateSelection(pair.item1_id)}
                                    disabled={isItem1Deleting}
                                    className="w-4 h-4 rounded"
                                  />
                                  <div>
                                    <p className="text-surface-300 text-sm font-medium">Item 1</p>
                                    <code className="text-xs text-surface-500">{pair.item1_id.slice(0, 12)}...</code>
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleDeleteDuplicate(pair.item1_id)}
                                  disabled={isItem1Deleting}
                                  className="p-2 rounded-lg text-surface-400 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50"
                                  title="Delete this item"
                                >
                                  {isItem1Deleting ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Trash2 className="w-4 h-4" />
                                  )}
                                </button>
                              </div>
                            </div>

                            {/* Similarity Badge */}
                            <div className="flex flex-col items-center flex-shrink-0">
                              <div className="text-lg font-bold text-red-400">
                                {(pair.similarity * 100).toFixed(0)}%
                              </div>
                              <div className="text-xs text-surface-500">similar</div>
                            </div>

                            {/* Item 2 */}
                            <div className={`flex-1 p-3 rounded-lg border transition-all ${
                              isItem2Selected 
                                ? 'bg-red-500/10 border-red-500/50' 
                                : 'bg-surface-700/50 border-surface-600'
                            }`}>
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                  <input
                                    type="checkbox"
                                    checked={isItem2Selected}
                                    onChange={() => toggleDuplicateSelection(pair.item2_id)}
                                    disabled={isItem2Deleting}
                                    className="w-4 h-4 rounded"
                                  />
                                  <div>
                                    <p className="text-surface-300 text-sm font-medium">Item 2</p>
                                    <code className="text-xs text-surface-500">{pair.item2_id.slice(0, 12)}...</code>
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleDeleteDuplicate(pair.item2_id)}
                                  disabled={isItem2Deleting}
                                  className="p-2 rounded-lg text-surface-400 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50"
                                  title="Delete this item"
                                >
                                  {isItem2Deleting ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Trash2 className="w-4 h-4" />
                                  )}
                                </button>
                              </div>
                            </div>
                          </div>

                          {/* Expand Button */}
                          <button
                            onClick={() => toggleExpandPair(idx, pair.item1_id, pair.item2_id)}
                            className="mt-3 w-full py-2 rounded-lg bg-surface-700/50 hover:bg-surface-700 transition-colors flex items-center justify-center gap-2 text-sm text-surface-400 hover:text-white"
                          >
                            <Eye className="w-4 h-4" />
                            {isExpanded ? 'Hide Preview' : 'Compare Items'}
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </div>

                        {/* Expanded Preview Section */}
                        {isExpanded && (
                          <div className="border-t border-surface-700 p-4">
                            <div className="grid grid-cols-2 gap-4">
                              {/* Item 1 Preview */}
                              <div className="p-4 rounded-xl bg-surface-900/50 border border-surface-700">
                                <div className="flex items-center justify-between mb-3">
                                  <h4 className="font-medium text-surface-300 flex items-center gap-2">
                                    Item 1
                                    {item1Details?.data_type && (
                                      <span className="px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-400">
                                        {item1Details.data_type}
                                      </span>
                                    )}
                                  </h4>
                                  {item1Details?.source_url && (
                                    <a
                                      href={item1Details.source_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="p-1.5 rounded-lg text-surface-400 hover:text-brand-400 hover:bg-brand-500/10 transition-colors"
                                      title="Open source URL"
                                    >
                                      <ExternalLink className="w-4 h-4" />
                                    </a>
                                  )}
                                </div>
                                {isLoadingItem1 ? (
                                  <div className="flex items-center justify-center py-8">
                                    <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
                                  </div>
                                ) : (
                                  <div>
                                    {renderItemPreview(item1Details)}
                                    {item1Details?.labels?.length > 0 && (
                                      <div className="mt-3 flex flex-wrap gap-1">
                                        {item1Details.labels.map((label: string, i: number) => (
                                          <span key={i} className="px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400">
                                            {label}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                    {item1Details?.created_at && (
                                      <p className="mt-2 text-xs text-surface-500">
                                        Created: {new Date(item1Details.created_at).toLocaleDateString()}
                                      </p>
                                    )}
                                  </div>
                                )}
                              </div>

                              {/* Item 2 Preview */}
                              <div className="p-4 rounded-xl bg-surface-900/50 border border-surface-700">
                                <div className="flex items-center justify-between mb-3">
                                  <h4 className="font-medium text-surface-300 flex items-center gap-2">
                                    Item 2
                                    {item2Details?.data_type && (
                                      <span className="px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-400">
                                        {item2Details.data_type}
                                      </span>
                                    )}
                                  </h4>
                                  {item2Details?.source_url && (
                                    <a
                                      href={item2Details.source_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="p-1.5 rounded-lg text-surface-400 hover:text-brand-400 hover:bg-brand-500/10 transition-colors"
                                      title="Open source URL"
                                    >
                                      <ExternalLink className="w-4 h-4" />
                                    </a>
                                  )}
                                </div>
                                {isLoadingItem2 ? (
                                  <div className="flex items-center justify-center py-8">
                                    <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
                                  </div>
                                ) : (
                                  <div>
                                    {renderItemPreview(item2Details)}
                                    {item2Details?.labels?.length > 0 && (
                                      <div className="mt-3 flex flex-wrap gap-1">
                                        {item2Details.labels.map((label: string, i: number) => (
                                          <span key={i} className="px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400">
                                            {label}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                    {item2Details?.created_at && (
                                      <p className="mt-2 text-xs text-surface-500">
                                        Created: {new Date(item2Details.created_at).toLocaleDateString()}
                                      </p>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Quick Actions when Expanded */}
                            <div className="mt-4 flex justify-center gap-3">
                              <button
                                onClick={() => {
                                  // Keep Item 1, select Item 2 for deletion
                                  if (selectedDuplicates.has(pair.item1_id)) {
                                    toggleDuplicateSelection(pair.item1_id) // Deselect Item 1
                                  }
                                  if (!selectedDuplicates.has(pair.item2_id)) {
                                    toggleDuplicateSelection(pair.item2_id) // Select Item 2
                                  }
                                }}
                                disabled={isItem2Selected}
                                className={`px-4 py-2 rounded-lg text-sm transition-colors flex items-center gap-2 ${
                                  isItem2Selected 
                                    ? 'bg-red-500/20 text-red-400 border border-red-500/30' 
                                    : 'bg-surface-700 hover:bg-surface-600'
                                }`}
                              >
                                {isItem2Selected && <CheckCircle className="w-4 h-4" />}
                                Keep Item 1, Delete Item 2
                              </button>
                              <button
                                onClick={() => {
                                  // Keep Item 2, select Item 1 for deletion
                                  if (selectedDuplicates.has(pair.item2_id)) {
                                    toggleDuplicateSelection(pair.item2_id) // Deselect Item 2
                                  }
                                  if (!selectedDuplicates.has(pair.item1_id)) {
                                    toggleDuplicateSelection(pair.item1_id) // Select Item 1
                                  }
                                }}
                                disabled={isItem1Selected}
                                className={`px-4 py-2 rounded-lg text-sm transition-colors flex items-center gap-2 ${
                                  isItem1Selected 
                                    ? 'bg-red-500/20 text-red-400 border border-red-500/30' 
                                    : 'bg-surface-700 hover:bg-surface-600'
                                }`}
                              >
                                {isItem1Selected && <CheckCircle className="w-4 h-4" />}
                                Keep Item 2, Delete Item 1
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                  {findDuplicatesMutation.data.count > 50 && (
                    <p className="text-sm text-surface-500 text-center">
                      Showing 50 of {findDuplicatesMutation.data.count} pairs
                    </p>
                  )}
                </>
              ) : findDuplicatesMutation.isPending ? (
                <div className="text-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-surface-400 mx-auto mb-4" />
                  <p className="text-surface-400">Searching for duplicates...</p>
                </div>
              ) : findDuplicatesMutation.isSuccess && findDuplicatesMutation.data?.count === 0 ? (
                <div className="text-center py-12">
                  <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                  <p className="text-surface-300">No duplicates found!</p>
                  <p className="text-sm text-surface-500 mt-1">Your dataset looks clean</p>
                </div>
              ) : (
                <div className="text-center py-12">
                  <Copy className="w-12 h-12 text-surface-500 mx-auto mb-4" />
                  <p className="text-surface-400">Click Find to search for duplicates</p>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}

      {/* Dataset Card Modal */}
      {showDatasetCardModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface-900 rounded-2xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <BookOpen className="w-6 h-6 text-cyan-400" />
                Dataset Card
              </h2>
              <button
                onClick={() => setShowDatasetCardModal(false)}
                className="p-2 rounded-lg hover:bg-surface-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-surface-400 mb-1">Title *</label>
                <input
                  type="text"
                  placeholder="My Awesome Dataset"
                  value={datasetCard.title}
                  onChange={(e) => setDatasetCard({ ...datasetCard, title: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                />
              </div>
              
              <div>
                <label className="block text-sm text-surface-400 mb-1">Description</label>
                <textarea
                  placeholder="Describe your dataset, its purpose, and how it was collected..."
                  value={datasetCard.description}
                  onChange={(e) => setDatasetCard({ ...datasetCard, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 h-32 resize-none"
                />
              </div>

              <div>
                <label className="block text-sm text-surface-400 mb-1">License</label>
                <select
                  value={datasetCard.license}
                  onChange={(e) => setDatasetCard({ ...datasetCard, license: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                >
                  <option value="mit">MIT</option>
                  <option value="apache-2.0">Apache 2.0</option>
                  <option value="cc-by-4.0">CC BY 4.0</option>
                  <option value="cc-by-sa-4.0">CC BY-SA 4.0</option>
                  <option value="cc0-1.0">CC0 (Public Domain)</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-surface-400 mb-1">Languages</label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    placeholder="en, fa, de..."
                    value={newLanguage}
                    onChange={(e) => setNewLanguage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newLanguage.trim()) {
                        setDatasetCard({ ...datasetCard, languages: [...datasetCard.languages, newLanguage.trim()] })
                        setNewLanguage('')
                      }
                    }}
                    className="flex-1 px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                  />
                  <button
                    onClick={() => {
                      if (newLanguage.trim()) {
                        setDatasetCard({ ...datasetCard, languages: [...datasetCard.languages, newLanguage.trim()] })
                        setNewLanguage('')
                      }
                    }}
                    className="px-4 py-2 rounded-lg bg-surface-700 hover:bg-surface-600"
                  >
                    Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {datasetCard.languages.map((lang, i) => (
                    <span key={i} className="px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 text-sm flex items-center gap-1">
                      {lang}
                      <button
                        onClick={() => setDatasetCard({ ...datasetCard, languages: datasetCard.languages.filter((_, idx) => idx !== i) })}
                        className="hover:text-white"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm text-surface-400 mb-1">Task Categories</label>
                <div className="flex flex-wrap gap-2">
                  {['text-classification', 'token-classification', 'question-answering', 'summarization', 'translation', 'image-classification', 'object-detection', 'text-generation'].map((task) => (
                    <button
                      key={task}
                      onClick={() => {
                        if (datasetCard.task_categories.includes(task)) {
                          setDatasetCard({ ...datasetCard, task_categories: datasetCard.task_categories.filter(t => t !== task) })
                        } else {
                          setDatasetCard({ ...datasetCard, task_categories: [...datasetCard.task_categories, task] })
                        }
                      }}
                      className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                        datasetCard.task_categories.includes(task)
                          ? 'bg-cyan-500 text-white'
                          : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                      }`}
                    >
                      {task}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm text-surface-400 mb-1">Tags</label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    placeholder="Add tags..."
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newTag.trim()) {
                        setDatasetCard({ ...datasetCard, tags: [...datasetCard.tags, newTag.trim()] })
                        setNewTag('')
                      }
                    }}
                    className="flex-1 px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                  />
                  <button
                    onClick={() => {
                      if (newTag.trim()) {
                        setDatasetCard({ ...datasetCard, tags: [...datasetCard.tags, newTag.trim()] })
                        setNewTag('')
                      }
                    }}
                    className="px-4 py-2 rounded-lg bg-surface-700 hover:bg-surface-600"
                  >
                    Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {datasetCard.tags.map((tag, i) => (
                    <span key={i} className="px-2 py-1 rounded bg-surface-700 text-surface-300 text-sm flex items-center gap-1">
                      {tag}
                      <button
                        onClick={() => setDatasetCard({ ...datasetCard, tags: datasetCard.tags.filter((_, idx) => idx !== i) })}
                        className="hover:text-white"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowDatasetCardModal(false)}
                className="px-4 py-2 rounded-lg text-surface-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const cardData = {
                    project_id: projectId,
                    ...datasetCard,
                  }
                  if (existingCard) {
                    updateCardMutation.mutate(cardData)
                  } else {
                    createCardMutation.mutate(cardData)
                  }
                }}
                disabled={createCardMutation.isPending || updateCardMutation.isPending || !datasetCard.title}
                className="px-4 py-2 rounded-lg bg-cyan-500 text-white hover:bg-cyan-600 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {(createCardMutation.isPending || updateCardMutation.isPending) && <Loader2 className="w-4 h-4 animate-spin" />}
                {existingCard ? 'Update Card' : 'Create Card'}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}

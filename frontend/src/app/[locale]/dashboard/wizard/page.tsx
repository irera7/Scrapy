'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { useRouter } from '@/i18n/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import {
  projectsApi,
  jobsApi,
  dataApi,
  datasetApi,
  processingApi,
  exportsApi,
} from '@/lib/api'
import {
  Wand2,
  ChevronRight,
  ChevronLeft,
  Check,
  Loader2,
  FolderKanban,
  Plus,
  Database,
  Sparkles,
  Split,
  Tag,
  FileText,
  Download,
  CheckCircle,
  AlertTriangle,
  Play,
  RefreshCw,
  ArrowRight,
  Settings,
  Target,
  Brain,
  BookOpen,
  Zap,
  Globe,
  Upload,
  BarChart3,
  TrendingUp,
  Layers,
  Image as ImageIcon,
  Music,
  Video,
  X,
  Info,
  Star,
  Rocket,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const wizardTutorial: TutorialSection[] = [
  {
    title: 'ML Dataset Wizard',
    content: 'This wizard guides you through the complete process of preparing a machine learning dataset. Follow each step to transform raw data into a training-ready dataset.',
    tips: [
      'Complete each step in order for best results',
      'Green checkmarks show completed steps',
      'You can navigate between steps at any time',
    ],
  },
  {
    title: 'Step 1: Project',
    content: 'Select an existing project or create a new one. Projects organize your data by topic or ML task. Choose the primary data type (text, image, audio, video).',
    steps: [
      { title: 'Create New', description: 'Enter name, description, and data type' },
      { title: 'Or Select Existing', description: 'Choose from your existing projects' },
    ],
  },
  {
    title: 'Step 2: Collect Data',
    content: 'Gather raw data through web scraping, file upload, or the visual scraper. You need data before proceeding to the next steps.',
    tips: [
      'Web scraping collects data from online sources',
      'Upload CSV, JSON, or media files directly',
      'Visual scraper lets you click elements to extract data',
    ],
  },
  {
    title: 'Step 3: Process',
    content: 'Process your data to extract features, compute quality scores, and prepare for ML training. This includes text cleaning, language detection, and metadata extraction.',
    steps: [
      { title: 'Auto Processing', description: 'Run feature extraction and text cleaning' },
      { title: 'Compute Quality', description: 'Calculate quality scores for filtering' },
    ],
  },
  {
    title: 'Step 4: Label',
    content: 'Assign labels to your data for supervised learning. Use manual labeling, the annotation studio for complex annotations, or active learning suggestions.',
    tips: [
      'Labels are categories your model will learn to predict',
      'Annotation studio supports bounding boxes, NER, etc.',
      'Active learning prioritizes uncertain samples',
    ],
  },
  {
    title: 'Step 5: Split',
    content: 'Divide your dataset into Train, Validation, and Test sets. Standard ratios are 80/10/10 for large datasets or 70/15/15 for smaller ones.',
    warning: 'Always keep test data completely separate - never train on test data!',
    steps: [
      { title: 'Set Ratios', description: 'Configure train/val/test percentages (must sum to 100%)' },
      { title: 'Stratify', description: 'Enable to maintain label distribution across splits' },
      { title: 'Auto Split', description: 'Click to automatically assign items to splits' },
    ],
  },
  {
    title: 'Step 6: Augment',
    content: 'Optionally increase your training data through augmentation. Apply transformations like synonym replacement, image flips, or audio modifications.',
    warning: 'Only augment training data! Test and validation sets must remain original.',
  },
  {
    title: 'Step 7: Document',
    content: 'Create a Dataset Card (HuggingFace format) documenting your dataset\'s purpose, contents, and licensing. Good documentation helps others use your dataset.',
    tips: [
      'Include a clear description of data sources',
      'Specify the license for data usage',
      'Tag relevant ML tasks and languages',
    ],
  },
  {
    title: 'Step 8: Export',
    content: 'Export your ML-ready dataset in your preferred format. Choose from JSONL, CSV, HuggingFace format, or COCO for object detection.',
    steps: [
      { title: 'Choose Format', description: 'Select output format based on your ML framework' },
      { title: 'Select Splits', description: 'Include train, val, and/or test sets' },
      { title: 'Export', description: 'Generate and download your dataset' },
    ],
  },
]

// Helper function to extract error message from API errors
const getErrorMessage = (error: any, fallback: string): string => {
  const detail = error?.response?.data?.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // Pydantic validation errors
    return detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ')
  }
  if (typeof detail === 'object' && detail.msg) {
    return detail.msg
  }
  return fallback
}

// Wizard Steps
const STEPS = [
  {
    id: 'project',
    title: 'Project',
    description: 'Select or create a project',
    icon: FolderKanban,
  },
  {
    id: 'collect',
    title: 'Collect',
    description: 'Collect data',
    icon: Database,
  },
  {
    id: 'process',
    title: 'Process',
    description: 'Processing & quality check',
    icon: Sparkles,
  },
  {
    id: 'label',
    title: 'Label',
    description: 'Assign labels & annotations',
    icon: Tag,
  },
  {
    id: 'split',
    title: 'Split',
    description: 'Split into Train/Val/Test',
    icon: Split,
  },
  {
    id: 'augment',
    title: 'Augment',
    description: 'Data augmentation techniques',
    icon: TrendingUp,
  },
  {
    id: 'document',
    title: 'Document',
    description: 'Create Dataset Card',
    icon: BookOpen,
  },
  {
    id: 'export',
    title: 'Export',
    description: 'Export the dataset',
    icon: Download,
  },
]

// Storage key for wizard state persistence
const WIZARD_STORAGE_KEY = 'wizard-state'

export default function WizardPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  
  // Wizard State
  const [currentStep, setCurrentStep] = useState(0)
  const [selectedProjectId, setSelectedProjectId] = useState<string>('')
  const [isCreatingProject, setIsCreatingProject] = useState(false)
  const [newProjectData, setNewProjectData] = useState({
    name: '',
    description: '',
    data_type: 'text',
  })
  const [stateRestored, setStateRestored] = useState(false)
  
  // Collection State
  const [collectionMethod, setCollectionMethod] = useState<'scrape' | 'upload' | 'skip'>('skip')
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  
  // Split Config
  const [splitConfig, setSplitConfig] = useState({
    train_ratio: 0.8,
    val_ratio: 0.1,
    test_ratio: 0.1,
    stratify_by: 'labels',
    shuffle: true,
  })
  
  // Dataset Card State
  const [datasetCard, setDatasetCard] = useState({
    title: '',
    description: '',
    license: 'mit',
    languages: ['en'],
    task_categories: [] as string[],
    tags: [] as string[],
  })
  
  // Export Config
  const [exportConfig, setExportConfig] = useState({
    name: '',
    format: 'jsonl',
    splits: ['train', 'val', 'test'],
    include_annotations: true,
  })
  
  // Completion tracking for each step
  const [stepCompletion, setStepCompletion] = useState<Record<string, boolean>>({
    project: false,
    collect: false,
    process: false,
    label: false,
    split: false,
    augment: false,
    document: false,
    export: false,
  })

  // Queries
  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const { data: selectedProject, refetch: refetchProject } = useQuery({
    queryKey: ['project', selectedProjectId],
    queryFn: () => projectsApi.get(selectedProjectId),
    enabled: !!selectedProjectId,
  })

  const { data: projectStats, refetch: refetchStats } = useQuery({
    queryKey: ['project-stats', selectedProjectId],
    queryFn: () => datasetApi.getStatistics(selectedProjectId),
    enabled: !!selectedProjectId,
  })

  const { data: splitStats, refetch: refetchSplitStats } = useQuery({
    queryKey: ['split-stats', selectedProjectId],
    queryFn: () => datasetApi.getSplitStats(selectedProjectId),
    enabled: !!selectedProjectId,
  })

  const { data: projectJobs } = useQuery({
    queryKey: ['project-jobs', selectedProjectId],
    queryFn: () => jobsApi.list({ project_id: selectedProjectId, limit: 10 }),
    enabled: !!selectedProjectId,
    refetchInterval: 5000,
  })

  // Mutations
  const createProjectMutation = useMutation({
    mutationFn: (data: typeof newProjectData) => projectsApi.create(data),
    onSuccess: (data) => {
      toast.success('Project created successfully!')
      setSelectedProjectId(data.id)
      setIsCreatingProject(false)
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      markStepComplete('project')
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Failed to create project'))
    },
  })

  const processAllMutation = useMutation({
    mutationFn: () => processingApi.processAll(selectedProjectId, 'auto', false),
    onSuccess: (data) => {
      toast.success(`${data.processed || 0} items processed`)
      refetchStats()
      markStepComplete('process')
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Processing failed'))
    },
  })

  const computeQualityMutation = useMutation({
    mutationFn: () => processingApi.computeQualityScores(selectedProjectId, false),
    onSuccess: (data) => {
      toast.success('Quality scores computed')
      refetchStats()
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Quality computation failed'))
    },
  })

  const autoSplitMutation = useMutation({
    mutationFn: () => datasetApi.autoSplit({
      project_id: selectedProjectId,
      config: splitConfig,
      create_version: true,
    }),
    onSuccess: (data) => {
      toast.success(`Dataset split: ${data.train} train, ${data.val} val, ${data.test} test`)
      refetchSplitStats()
      refetchStats()
      markStepComplete('split')
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Split failed'))
    },
  })

  const createDatasetCardMutation = useMutation({
    mutationFn: () => datasetApi.createDatasetCard({
      project_id: selectedProjectId,
      ...datasetCard,
    }),
    onSuccess: () => {
      toast.success('Dataset card created')
      markStepComplete('document')
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Failed to create card'))
    },
  })

  const createExportMutation = useMutation({
    mutationFn: () => exportsApi.create({
      project_id: selectedProjectId,
      name: exportConfig.name || `${selectedProject?.name}-export`,
      format: exportConfig.format,
      filters: {
        splits: exportConfig.splits,
        include_annotations: exportConfig.include_annotations,
      },
    }),
    onSuccess: () => {
      toast.success('Export is being prepared')
      markStepComplete('export')
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, 'Failed to create export'))
    },
  })

  // Restore state from localStorage on mount
  useEffect(() => {
    if (stateRestored) return
    
    try {
      const savedState = localStorage.getItem(WIZARD_STORAGE_KEY)
      if (savedState) {
        const parsed = JSON.parse(savedState)
        // Only restore if saved within last 24 hours
        if (parsed.savedAt && Date.now() - parsed.savedAt < 24 * 60 * 60 * 1000) {
          if (parsed.currentStep !== undefined) setCurrentStep(parsed.currentStep)
          if (parsed.selectedProjectId) setSelectedProjectId(parsed.selectedProjectId)
          if (parsed.stepCompletion) setStepCompletion(parsed.stepCompletion)
          if (parsed.splitConfig) setSplitConfig(parsed.splitConfig)
          if (parsed.datasetCard) setDatasetCard(parsed.datasetCard)
          if (parsed.exportConfig) setExportConfig(parsed.exportConfig)
        }
      }
    } catch (e) {
      console.error('Failed to restore wizard state:', e)
    }
    
    // URL params override saved state
    const projectParam = searchParams.get('project')
    if (projectParam) {
      setSelectedProjectId(projectParam)
    }
    const stepParam = searchParams.get('step')
    if (stepParam) {
      const stepIndex = STEPS.findIndex(s => s.id === stepParam)
      if (stepIndex !== -1) {
        setCurrentStep(stepIndex)
      }
    }
    
    setStateRestored(true)
  }, [searchParams, stateRestored])

  // Save state to localStorage when it changes
  useEffect(() => {
    if (!stateRestored) return
    
    try {
      const stateToSave = {
        currentStep,
        selectedProjectId,
        stepCompletion,
        splitConfig,
        datasetCard,
        exportConfig,
        savedAt: Date.now(),
      }
      localStorage.setItem(WIZARD_STORAGE_KEY, JSON.stringify(stateToSave))
    } catch (e) {
      console.error('Failed to save wizard state:', e)
    }
  }, [stateRestored, currentStep, selectedProjectId, stepCompletion, splitConfig, datasetCard, exportConfig])

  // Update step completion based on project data
  useEffect(() => {
    if (selectedProjectId) {
      setStepCompletion(prev => ({ ...prev, project: true }))
      
      // Update datasetCard title from project
      if (selectedProject && !datasetCard.title) {
        setDatasetCard(prev => ({
          ...prev,
          title: selectedProject.name,
          description: selectedProject.description || '',
        }))
      }
      
      // Update export config name
      if (selectedProject && !exportConfig.name) {
        setExportConfig(prev => ({
          ...prev,
          name: `${selectedProject.name}-dataset`,
        }))
      }
    }
    
    // Check if data exists
    if (projectStats && projectStats.total_items > 0) {
      setStepCompletion(prev => ({ ...prev, collect: true }))
    }
    
    // Check if processed
    if (projectStats && projectStats.avg_quality_score !== null) {
      setStepCompletion(prev => ({ ...prev, process: true }))
    }
    
    // Check if labeled
    if (projectStats && projectStats.labeled_items > 0) {
      setStepCompletion(prev => ({ ...prev, label: true }))
    }
    
    // Check if split
    if (splitStats && (splitStats.train_count > 0 || splitStats.val_count > 0 || splitStats.test_count > 0)) {
      setStepCompletion(prev => ({ ...prev, split: true }))
    }
  }, [selectedProjectId, selectedProject, projectStats, splitStats])

  const markStepComplete = (stepId: string) => {
    setStepCompletion(prev => ({ ...prev, [stepId]: true }))
  }

  const goToNextStep = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const goToPrevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const canProceed = () => {
    const currentStepId = STEPS[currentStep].id
    switch (currentStepId) {
      case 'project':
        return !!selectedProjectId
      case 'collect':
        return projectStats && projectStats.total_items > 0
      default:
        return true
    }
  }

  const getDataTypeIcon = (type: string) => {
    switch (type) {
      case 'text': return <FileText className="w-5 h-5" />
      case 'image': return <ImageIcon className="w-5 h-5" />
      case 'audio': return <Music className="w-5 h-5" />
      case 'video': return <Video className="w-5 h-5" />
      default: return <Layers className="w-5 h-5" />
    }
  }

  const renderStepContent = () => {
    const step = STEPS[currentStep]
    
    switch (step.id) {
      case 'project':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">Select or Create a Project</h2>
              <p className="text-surface-400">
                First, choose the project you want to build an ML dataset from
              </p>
            </div>

            {/* Create New Project Section */}
            <div className="rounded-2xl border border-dashed border-surface-700 p-6 hover:border-brand-500/50 transition-colors">
              {isCreatingProject ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-4"
                >
                  <div>
                    <label className="block text-sm text-surface-400 mb-2">Project Name *</label>
                    <input
                      type="text"
                      placeholder="e.g., Sentiment Analysis Dataset"
                      value={newProjectData.name}
                      onChange={(e) => setNewProjectData({ ...newProjectData, name: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm text-surface-400 mb-2">Description</label>
                    <textarea
                      placeholder="Project description..."
                      value={newProjectData.description}
                      onChange={(e) => setNewProjectData({ ...newProjectData, description: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors h-24 resize-none"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm text-surface-400 mb-2">Primary Data Type</label>
                    <div className="grid grid-cols-4 gap-3">
                      {[
                        { value: 'text', label: 'Text', icon: FileText },
                        { value: 'image', label: 'Image', icon: ImageIcon },
                        { value: 'audio', label: 'Audio', icon: Music },
                        { value: 'video', label: 'Video', icon: Video },
                      ].map((type) => (
                        <button
                          key={type.value}
                          onClick={() => setNewProjectData({ ...newProjectData, data_type: type.value })}
                          className={cn(
                            'p-4 rounded-xl border transition-all flex flex-col items-center gap-2',
                            newProjectData.data_type === type.value
                              ? 'border-brand-500 bg-brand-500/10 text-brand-400'
                              : 'border-surface-700 hover:border-surface-600'
                          )}
                        >
                          <type.icon className="w-6 h-6" />
                          <span className="text-sm">{type.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex gap-3 pt-4">
                    <button
                      onClick={() => setIsCreatingProject(false)}
                      className="flex-1 px-4 py-3 rounded-xl bg-surface-800 text-surface-400 hover:bg-surface-700 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => createProjectMutation.mutate(newProjectData)}
                      disabled={!newProjectData.name || createProjectMutation.isPending}
                      className="flex-1 px-4 py-3 rounded-xl bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                    >
                      {createProjectMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                      Create Project
                    </button>
                  </div>
                </motion.div>
              ) : (
                <button
                  onClick={() => setIsCreatingProject(true)}
                  className="w-full flex items-center justify-center gap-3 py-4 text-surface-400 hover:text-brand-400 transition-colors"
                >
                  <Plus className="w-6 h-6" />
                  <span className="text-lg">Create New Project</span>
                </button>
              )}
            </div>

            {/* Existing Projects */}
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <FolderKanban className="w-5 h-5" />
                Existing Projects
              </h3>
              
              {projectsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
                </div>
              ) : projects && projects.length > 0 ? (
                <div className="grid gap-3 max-h-[400px] overflow-y-auto">
                  {projects.map((project: any) => (
                    <button
                      key={project.id}
                      onClick={() => {
                        setSelectedProjectId(project.id)
                        markStepComplete('project')
                      }}
                      className={cn(
                        'p-4 rounded-xl border transition-all text-left w-full',
                        selectedProjectId === project.id
                          ? 'border-brand-500 bg-brand-500/10'
                          : 'border-surface-700 hover:border-surface-600 bg-surface-800/50'
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            'w-12 h-12 rounded-xl flex items-center justify-center',
                            selectedProjectId === project.id ? 'bg-brand-500/20' : 'bg-surface-700'
                          )}>
                            {getDataTypeIcon(project.data_type)}
                          </div>
                          <div>
                            <h4 className="font-semibold">{project.name}</h4>
                            <p className="text-sm text-surface-400">
                              {project.data_type} • {(project.data_count || 0).toLocaleString()} items
                            </p>
                          </div>
                        </div>
                        {selectedProjectId === project.id && (
                          <CheckCircle className="w-6 h-6 text-brand-500" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-surface-400">
                  <FolderKanban className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No projects yet</p>
                  <p className="text-sm">Create a new project above</p>
                </div>
              )}
            </div>
          </div>
        )

      case 'collect':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">Collect Data</h2>
              <p className="text-surface-400">
                Collect raw data via scraping or file upload
              </p>
            </div>

            {/* Current Data Stats */}
            {projectStats && projectStats.total_items > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-6 rounded-2xl bg-green-500/10 border border-green-500/30"
              >
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-xl bg-green-500/20 flex items-center justify-center">
                    <CheckCircle className="w-7 h-7 text-green-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-green-400">
                      {projectStats.total_items.toLocaleString()} items available
                    </h3>
                    <p className="text-sm text-surface-400">
                      {projectStats.labeled_items.toLocaleString()} labeled
                    </p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Collection Options */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Scrape */}
              <Link
                href={`/dashboard/jobs/new?project=${selectedProjectId}`}
                target="_blank"
                className="p-6 rounded-2xl border border-surface-700 hover:border-brand-500/50 bg-surface-800/50 transition-all group"
              >
                <div className="w-14 h-14 rounded-xl bg-brand-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <Globe className="w-7 h-7 text-brand-400" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Web Scraping</h3>
                <p className="text-sm text-surface-400">
                  Collect data from the web using scraping jobs
                </p>
                <div className="mt-4 flex items-center gap-2 text-brand-400 text-sm">
                  <span>Create New Job</span>
                  <ArrowRight className="w-4 h-4" />
                  <span className="text-xs text-surface-500">(opens in new tab)</span>
                </div>
              </Link>

              {/* Upload */}
              <Link
                href={`/dashboard/data?project=${selectedProjectId}`}
                target="_blank"
                className="p-6 rounded-2xl border border-surface-700 hover:border-purple-500/50 bg-surface-800/50 transition-all group"
              >
                <div className="w-14 h-14 rounded-xl bg-purple-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <Upload className="w-7 h-7 text-purple-400" />
                </div>
                <h3 className="text-lg font-semibold mb-2">File Upload</h3>
                <p className="text-sm text-surface-400">
                  Upload CSV, JSON or media files
                </p>
                <div className="mt-4 flex items-center gap-2 text-purple-400 text-sm">
                  <span>Go to Data Page</span>
                  <ArrowRight className="w-4 h-4" />
                  <span className="text-xs text-surface-500">(opens in new tab)</span>
                </div>
              </Link>

              {/* Visual Scraper */}
              <Link
                href="/dashboard/visual-scraper"
                target="_blank"
                className="p-6 rounded-2xl border border-surface-700 hover:border-cyan-500/50 bg-surface-800/50 transition-all group"
              >
                <div className="w-14 h-14 rounded-xl bg-cyan-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <Target className="w-7 h-7 text-cyan-400" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Visual Scraper</h3>
                <p className="text-sm text-surface-400">
                  Select elements by clicking to extract data
                </p>
                <div className="mt-4 flex items-center gap-2 text-cyan-400 text-sm">
                  <span>Open</span>
                  <ArrowRight className="w-4 h-4" />
                  <span className="text-xs text-surface-500">(opens in new tab)</span>
                </div>
              </Link>
            </div>

            {/* Running Jobs */}
            {projectJobs && projectJobs.length > 0 && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Play className="w-5 h-5" />
                  Recent Jobs
                </h3>
                <div className="space-y-2">
                  {projectJobs.slice(0, 5).map((job: any) => (
                    <Link
                      key={job.id}
                      href={`/dashboard/jobs/${job.id}`}
                      target="_blank"
                      className="flex items-center justify-between p-4 rounded-xl bg-surface-800/50 hover:bg-surface-800 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          'w-10 h-10 rounded-lg flex items-center justify-center',
                          job.status === 'completed' ? 'bg-green-500/10' :
                          job.status === 'running' ? 'bg-yellow-500/10' :
                          job.status === 'failed' ? 'bg-red-500/10' :
                          'bg-surface-700'
                        )}>
                          {job.status === 'completed' && <CheckCircle className="w-5 h-5 text-green-400" />}
                          {job.status === 'running' && <Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />}
                          {job.status === 'failed' && <AlertTriangle className="w-5 h-5 text-red-400" />}
                          {!['completed', 'running', 'failed'].includes(job.status) && <Play className="w-5 h-5 text-surface-400" />}
                        </div>
                        <div>
                          <h4 className="font-medium">{job.name}</h4>
                          <p className="text-sm text-surface-400">
                            {(job.items_collected || 0).toLocaleString()} items collected
                          </p>
                        </div>
                      </div>
                      <span className={cn(
                        'px-3 py-1 rounded-lg text-sm',
                        job.status === 'completed' ? 'bg-green-500/10 text-green-400' :
                        job.status === 'running' ? 'bg-yellow-500/10 text-yellow-400' :
                        job.status === 'failed' ? 'bg-red-500/10 text-red-400' :
                        'bg-surface-700 text-surface-400'
                      )}>
                        {job.status}
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Info */}
            <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-400 mt-0.5" />
              <div className="text-sm">
                <p className="text-blue-400 font-medium">Important Note</p>
                <p className="text-surface-400">
                  You need at least some data to proceed to the next step.
                  If you already have data, you can continue.
                </p>
              </div>
            </div>
          </div>
        )

      case 'process':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">Processing & Quality Check</h2>
              <p className="text-surface-400">
                Automatic data processing and quality score calculation
              </p>
            </div>

            {/* Stats Cards */}
            {projectStats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-surface-800/50 text-center">
                  <Layers className="w-6 h-6 mx-auto mb-2 text-brand-400" />
                  <p className="text-2xl font-bold">{projectStats.total_items.toLocaleString()}</p>
                  <p className="text-sm text-surface-400">Total Items</p>
                </div>
                <div className="p-4 rounded-xl bg-surface-800/50 text-center">
                  <Tag className="w-6 h-6 mx-auto mb-2 text-green-400" />
                  <p className="text-2xl font-bold">{projectStats.labeled_items.toLocaleString()}</p>
                  <p className="text-sm text-surface-400">Labeled</p>
                </div>
                <div className="p-4 rounded-xl bg-surface-800/50 text-center">
                  <BarChart3 className="w-6 h-6 mx-auto mb-2 text-blue-400" />
                  <p className="text-2xl font-bold">
                    {projectStats.avg_quality_score !== null 
                      ? `${(projectStats.avg_quality_score * 100).toFixed(0)}%`
                      : 'N/A'}
                  </p>
                  <p className="text-sm text-surface-400">Avg Quality</p>
                </div>
                <div className="p-4 rounded-xl bg-surface-800/50 text-center">
                  {projectStats.is_balanced ? (
                    <CheckCircle className="w-6 h-6 mx-auto mb-2 text-green-400" />
                  ) : (
                    <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-yellow-400" />
                  )}
                  <p className="text-2xl font-bold">
                    {projectStats.class_imbalance_ratio?.toFixed(1) || 'N/A'}x
                  </p>
                  <p className="text-sm text-surface-400">Class Balance</p>
                </div>
              </div>
            )}

            {/* Processing Actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                onClick={() => processAllMutation.mutate()}
                disabled={processAllMutation.isPending}
                className="p-6 rounded-2xl border border-purple-500/30 bg-purple-500/5 hover:bg-purple-500/10 transition-all text-left"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-purple-400" />
                      Auto Processing
                    </h3>
                    <p className="text-sm text-surface-400">
                      Feature extraction, language detection, text cleaning
                    </p>
                  </div>
                  {processAllMutation.isPending ? (
                    <Loader2 className="w-6 h-6 animate-spin text-purple-400" />
                  ) : (
                    <Play className="w-6 h-6 text-purple-400" />
                  )}
                </div>
              </button>

              <button
                onClick={() => computeQualityMutation.mutate()}
                disabled={computeQualityMutation.isPending}
                className="p-6 rounded-2xl border border-green-500/30 bg-green-500/5 hover:bg-green-500/10 transition-all text-left"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-green-400" />
                      Compute Quality
                    </h3>
                    <p className="text-sm text-surface-400">
                      Score each item's quality for filtering
                    </p>
                  </div>
                  {computeQualityMutation.isPending ? (
                    <Loader2 className="w-6 h-6 animate-spin text-green-400" />
                  ) : (
                    <Play className="w-6 h-6 text-green-400" />
                  )}
                </div>
              </button>
            </div>

            {/* Quality Distribution */}
            {projectStats?.quality_distribution && projectStats.quality_distribution.length > 0 && (
              <div className="p-6 rounded-2xl bg-surface-800/50">
                <h3 className="text-lg font-semibold mb-4">Quality Distribution</h3>
                <div className="space-y-2">
                  {projectStats.quality_distribution.map((item: any) => (
                    <div key={item.range} className="flex items-center gap-3">
                      <span className="text-sm text-surface-400 w-16">{item.range}</span>
                      <div className="flex-1 h-4 bg-surface-700 rounded-full overflow-hidden">
                        <div 
                          className={cn(
                            'h-full rounded-full',
                            item.range.startsWith('0.8') ? 'bg-green-500' :
                            item.range.startsWith('0.6') ? 'bg-blue-500' :
                            item.range.startsWith('0.4') ? 'bg-yellow-500' :
                            'bg-red-500'
                          )}
                          style={{ width: `${item.percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-surface-500 w-12 text-right">{item.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Advanced Options Link */}
            <Link
              href={`/dashboard/quality?project=${selectedProjectId}`}
              target="_blank"
              className="block p-4 rounded-xl bg-surface-800/50 hover:bg-surface-800 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Settings className="w-5 h-5 text-surface-400" />
                  <span>Advanced Quality Settings & Data Leakage Detection</span>
                </div>
                <ArrowRight className="w-5 h-5 text-surface-400" />
              </div>
            </Link>
          </div>
        )

      case 'label':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">Labeling & Annotation</h2>
              <p className="text-surface-400">
                Assign labels to data for model training
              </p>
            </div>

            {/* Labeling Stats */}
            {projectStats && (
              <div className="p-6 rounded-2xl bg-surface-800/50">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-lg font-semibold">Labeling Status</h3>
                    <p className="text-sm text-surface-400">
                      {projectStats.labeled_items} of {projectStats.total_items} items are labeled
                    </p>
                  </div>
                  <div className="text-2xl font-bold text-brand-400">
                    {((projectStats.labeled_items / projectStats.total_items) * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="h-3 bg-surface-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-brand-500 to-green-500 rounded-full transition-all"
                    style={{ width: `${(projectStats.labeled_items / projectStats.total_items) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Label Distribution */}
            {projectStats?.label_distribution && projectStats.label_distribution.length > 0 && (
              <div className="p-6 rounded-2xl bg-surface-800/50">
                <h3 className="text-lg font-semibold mb-4">Label Distribution</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {projectStats.label_distribution.slice(0, 10).map((item: any) => (
                    <div key={item.label} className="flex items-center gap-3">
                      <span className="text-sm text-surface-300 w-32 truncate">{item.label}</span>
                      <div className="flex-1 h-4 bg-surface-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-brand-500 to-purple-500 rounded-full"
                          style={{ width: `${item.percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-surface-500 w-16 text-right">{item.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Labeling Options */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Link
                href={`/dashboard/data?project=${selectedProjectId}`}
                target="_blank"
                className="p-6 rounded-2xl border border-surface-700 hover:border-brand-500/50 bg-surface-800/50 transition-all"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center">
                    <Tag className="w-6 h-6 text-brand-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Manual Labeling</h3>
                    <p className="text-sm text-surface-400">Assign labels to items <span className="text-xs text-surface-500">(opens in new tab)</span></p>
                  </div>
                </div>
              </Link>

              <Link
                href={`/dashboard/dataset/annotations?project=${selectedProjectId}`}
                target="_blank"
                className="p-6 rounded-2xl border border-surface-700 hover:border-blue-500/50 bg-surface-800/50 transition-all"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                    <Target className="w-6 h-6 text-blue-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Annotation Studio</h3>
                    <p className="text-sm text-surface-400">BBox, NER, Segmentation <span className="text-xs text-surface-500">(opens in new tab)</span></p>
                  </div>
                </div>
              </Link>
            </div>

            {/* Active Learning */}
            <Link
              href={`/dashboard/dataset?project=${selectedProjectId}`}
              target="_blank"
              className="block p-4 rounded-xl bg-orange-500/10 border border-orange-500/30 hover:border-orange-500/50 transition-colors"
            >
              <div className="flex items-center gap-4">
                <Brain className="w-6 h-6 text-orange-400" />
                <div>
                  <h3 className="font-semibold text-orange-400">Active Learning</h3>
                  <p className="text-sm text-surface-400">
                    Get smart suggestions for more effective labeling
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-orange-400 ml-auto" />
              </div>
            </Link>

            {/* Info */}
            <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-400 mt-0.5" />
              <div className="text-sm">
                <p className="text-blue-400 font-medium">Note</p>
                <p className="text-surface-400">
                  Labeling is optional. If your data is already labeled or doesn't need labels,
                  you can skip this step.
                </p>
              </div>
            </div>
          </div>
        )

      case 'split':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">Dataset Splitting</h2>
              <p className="text-surface-400">
                Split data into Train, Validation, and Test sets
              </p>
            </div>

            {/* Current Split Stats */}
            {splitStats && (
              <div className="p-6 rounded-2xl bg-surface-800/50">
                <h3 className="text-lg font-semibold mb-4">Current Status</h3>
                <div className="flex gap-2 h-10 rounded-lg overflow-hidden mb-4">
                  <div 
                    className="bg-green-500 flex items-center justify-center text-sm font-medium text-white"
                    style={{ width: `${(splitStats.train_count / splitStats.total) * 100}%` }}
                  >
                    {splitStats.train_count > 0 && `Train (${splitStats.train_count})`}
                  </div>
                  <div 
                    className="bg-blue-500 flex items-center justify-center text-sm font-medium text-white"
                    style={{ width: `${(splitStats.val_count / splitStats.total) * 100}%` }}
                  >
                    {splitStats.val_count > 0 && `Val (${splitStats.val_count})`}
                  </div>
                  <div 
                    className="bg-purple-500 flex items-center justify-center text-sm font-medium text-white"
                    style={{ width: `${(splitStats.test_count / splitStats.total) * 100}%` }}
                  >
                    {splitStats.test_count > 0 && `Test (${splitStats.test_count})`}
                  </div>
                  <div 
                    className="bg-surface-600 flex items-center justify-center text-sm font-medium text-surface-300"
                    style={{ width: `${(splitStats.unassigned_count / splitStats.total) * 100}%` }}
                  >
                    {splitStats.unassigned_count > 0 && `Unassigned (${splitStats.unassigned_count})`}
                  </div>
                </div>
              </div>
            )}

            {/* Split Configuration */}
            <div className="p-6 rounded-2xl bg-surface-800/50">
              <h3 className="text-lg font-semibold mb-4">Split Configuration</h3>
              
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div>
                  <label className="block text-sm text-surface-400 mb-2">Train</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      value={splitConfig.train_ratio}
                      onChange={(e) => setSplitConfig({ ...splitConfig, train_ratio: parseFloat(e.target.value) })}
                      className="flex-1 px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                    />
                    <span className="text-green-400 font-medium w-12">
                      {(splitConfig.train_ratio * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-surface-400 mb-2">Validation</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      value={splitConfig.val_ratio}
                      onChange={(e) => setSplitConfig({ ...splitConfig, val_ratio: parseFloat(e.target.value) })}
                      className="flex-1 px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                    />
                    <span className="text-blue-400 font-medium w-12">
                      {(splitConfig.val_ratio * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-surface-400 mb-2">Test</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      value={splitConfig.test_ratio}
                      onChange={(e) => setSplitConfig({ ...splitConfig, test_ratio: parseFloat(e.target.value) })}
                      className="flex-1 px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                    />
                    <span className="text-purple-400 font-medium w-12">
                      {(splitConfig.test_ratio * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Options */}
              <div className="flex items-center gap-6 mb-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={splitConfig.stratify_by === 'labels'}
                    onChange={(e) => setSplitConfig({ ...splitConfig, stratify_by: e.target.checked ? 'labels' : undefined as any })}
                    className="rounded"
                  />
                  <span className="text-sm text-surface-300">Stratify by labels</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={splitConfig.shuffle}
                    onChange={(e) => setSplitConfig({ ...splitConfig, shuffle: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm text-surface-300">Shuffle data</span>
                </label>
              </div>

              {/* Validation */}
              {splitConfig.train_ratio + splitConfig.val_ratio + splitConfig.test_ratio !== 1 && (
                <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30 mb-4">
                  <p className="text-sm text-yellow-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    Ratios must sum to 100% (1.0)
                  </p>
                </div>
              )}

              {/* Split Button */}
              <button
                onClick={() => autoSplitMutation.mutate()}
                disabled={
                  autoSplitMutation.isPending || 
                  !selectedProjectId || 
                  (projectStats?.total_items || 0) === 0 ||
                  splitConfig.train_ratio + splitConfig.val_ratio + splitConfig.test_ratio !== 1
                }
                className="w-full px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {autoSplitMutation.isPending ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Split className="w-5 h-5" />
                )}
                Auto Split
              </button>
              
              {!selectedProjectId && (
                <p className="text-sm text-yellow-400 mt-2">Please select a project first.</p>
              )}
              {selectedProjectId && (projectStats?.total_items || 0) === 0 && (
                <p className="text-sm text-yellow-400 mt-2">No data items available. Collect some data first.</p>
              )}
            </div>

            {/* Info */}
            <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 flex items-start gap-3">
              <Info className="w-5 h-5 text-green-400 mt-0.5" />
              <div className="text-sm">
                <p className="text-green-400 font-medium">Recommended Ratios</p>
                <p className="text-surface-400">
                  Large dataset: 80/10/10 | Small dataset: 70/15/15
                </p>
              </div>
            </div>
          </div>
        )

      case 'augment':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">Data Augmentation</h2>
              <p className="text-surface-400">
                Increase dataset size with various techniques
              </p>
            </div>

            {/* Augmentation Options */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Link
                href={`/dashboard/dataset/augmentation?project=${selectedProjectId}`}
                target="_blank"
                className="p-6 rounded-2xl border border-surface-700 hover:border-green-500/50 bg-surface-800/50 transition-all group"
              >
                <div className="w-14 h-14 rounded-xl bg-green-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <Wand2 className="w-7 h-7 text-green-400" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Augmentation Settings</h3>
                <p className="text-sm text-surface-400 mb-4">
                  Create augmentation rules for text and images
                </p>
                <div className="flex items-center gap-2 text-green-400 text-sm">
                  <span>Go to Settings</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </Link>

              <div className="p-6 rounded-2xl border border-surface-700 bg-surface-800/50">
                <h3 className="text-lg font-semibold mb-4">Available Techniques</h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-blue-400" />
                    <div>
                      <p className="font-medium">Text</p>
                      <p className="text-xs text-surface-400">Synonym, Swap, Delete, Insert, Noise</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <ImageIcon className="w-5 h-5 text-purple-400" />
                    <div>
                      <p className="font-medium">Image</p>
                      <p className="text-xs text-surface-400">Flip, Rotate, Brightness, Crop, Blur</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Warning */}
            <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-400 mt-0.5" />
              <div className="text-sm">
                <p className="text-yellow-400 font-medium">Important Warning</p>
                <p className="text-surface-400">
                  Only augment Train data! Test and Validation data should remain original.
                </p>
              </div>
            </div>

            {/* Skip Info */}
            <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-400 mt-0.5" />
              <div className="text-sm">
                <p className="text-blue-400 font-medium">Optional</p>
                <p className="text-surface-400">
                  Data Augmentation is optional. If your dataset is large enough,
                  you can skip this step.
                </p>
              </div>
            </div>
          </div>
        )

      case 'document':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">Dataset Documentation</h2>
              <p className="text-surface-400">
                Create a Dataset Card (HuggingFace style)
              </p>
            </div>

            {/* Dataset Card Form */}
            <div className="p-6 rounded-2xl bg-surface-800/50 space-y-4">
              <div>
                <label className="block text-sm text-surface-400 mb-2">Dataset Title *</label>
                <input
                  type="text"
                  placeholder="e.g., Sentiment Analysis Dataset"
                  value={datasetCard.title}
                  onChange={(e) => setDatasetCard({ ...datasetCard, title: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-700 border border-surface-600 focus:border-brand-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-sm text-surface-400 mb-2">Description</label>
                <textarea
                  placeholder="Full description of the dataset, how it was collected, use cases..."
                  value={datasetCard.description}
                  onChange={(e) => setDatasetCard({ ...datasetCard, description: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-700 border border-surface-600 focus:border-brand-500 transition-colors h-32 resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-surface-400 mb-2">License</label>
                  <select
                    value={datasetCard.license}
                    onChange={(e) => setDatasetCard({ ...datasetCard, license: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-700 border border-surface-600"
                  >
                    <option value="mit">MIT</option>
                    <option value="apache-2.0">Apache 2.0</option>
                    <option value="cc-by-4.0">CC BY 4.0</option>
                    <option value="cc-by-sa-4.0">CC BY-SA 4.0</option>
                    <option value="cc0-1.0">CC0 (Public Domain)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-surface-400 mb-2">Languages</label>
                  <div className="flex flex-wrap gap-2">
                    {['en', 'fa', 'ar', 'de', 'fr'].map((lang) => (
                      <button
                        key={lang}
                        onClick={() => {
                          if (datasetCard.languages.includes(lang)) {
                            setDatasetCard({ ...datasetCard, languages: datasetCard.languages.filter(l => l !== lang) })
                          } else {
                            setDatasetCard({ ...datasetCard, languages: [...datasetCard.languages, lang] })
                          }
                        }}
                        className={cn(
                          'px-3 py-1.5 rounded-lg text-sm transition-colors',
                          datasetCard.languages.includes(lang)
                            ? 'bg-cyan-500 text-white'
                            : 'bg-surface-600 text-surface-300 hover:bg-surface-500'
                        )}
                      >
                        {lang.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm text-surface-400 mb-2">Tasks</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    'text-classification',
                    'token-classification',
                    'question-answering',
                    'summarization',
                    'translation',
                    'image-classification',
                    'object-detection',
                  ].map((task) => (
                    <button
                      key={task}
                      onClick={() => {
                        if (datasetCard.task_categories.includes(task)) {
                          setDatasetCard({ ...datasetCard, task_categories: datasetCard.task_categories.filter(t => t !== task) })
                        } else {
                          setDatasetCard({ ...datasetCard, task_categories: [...datasetCard.task_categories, task] })
                        }
                      }}
                      className={cn(
                        'px-3 py-1.5 rounded-lg text-sm transition-colors',
                        datasetCard.task_categories.includes(task)
                          ? 'bg-brand-500 text-white'
                          : 'bg-surface-600 text-surface-300 hover:bg-surface-500'
                      )}
                    >
                      {task}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={() => createDatasetCardMutation.mutate()}
                disabled={!datasetCard.title || createDatasetCardMutation.isPending}
                className="w-full px-6 py-3 rounded-xl bg-cyan-500 text-white font-semibold hover:bg-cyan-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {createDatasetCardMutation.isPending ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <BookOpen className="w-5 h-5" />
                )}
                Create Dataset Card
              </button>
            </div>
          </div>
        )

      case 'export':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">Export Dataset</h2>
              <p className="text-surface-400">
                Export your ML-ready dataset in your preferred format
              </p>
            </div>

            {/* Export Configuration */}
            <div className="p-6 rounded-2xl bg-surface-800/50 space-y-4">
              <div>
                <label className="block text-sm text-surface-400 mb-2">Export Name</label>
                <input
                  type="text"
                  placeholder="dataset-v1"
                  value={exportConfig.name}
                  onChange={(e) => setExportConfig({ ...exportConfig, name: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-700 border border-surface-600 focus:border-brand-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-sm text-surface-400 mb-2">Export Format</label>
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { value: 'jsonl', label: 'JSONL', desc: 'Line-by-line JSON' },
                    { value: 'csv', label: 'CSV', desc: 'Tabular' },
                    { value: 'huggingface', label: 'HuggingFace', desc: 'Ready to upload' },
                    { value: 'coco', label: 'COCO', desc: 'Object Detection' },
                  ].map((format) => (
                    <button
                      key={format.value}
                      onClick={() => setExportConfig({ ...exportConfig, format: format.value })}
                      className={cn(
                        'p-4 rounded-xl border transition-all text-center',
                        exportConfig.format === format.value
                          ? 'border-brand-500 bg-brand-500/10'
                          : 'border-surface-600 hover:border-surface-500'
                      )}
                    >
                      <p className="font-semibold">{format.label}</p>
                      <p className="text-xs text-surface-400">{format.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm text-surface-400 mb-2">Splits to Include</label>
                <div className="flex gap-3">
                  {['train', 'val', 'test'].map((split) => (
                    <label key={split} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={exportConfig.splits.includes(split)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setExportConfig({ ...exportConfig, splits: [...exportConfig.splits, split] })
                          } else {
                            setExportConfig({ ...exportConfig, splits: exportConfig.splits.filter(s => s !== split) })
                          }
                        }}
                        className="rounded"
                      />
                      <span className="capitalize">{split}</span>
                    </label>
                  ))}
                </div>
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={exportConfig.include_annotations}
                  onChange={(e) => setExportConfig({ ...exportConfig, include_annotations: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm text-surface-300">Include annotations</span>
              </label>

              <button
                onClick={() => createExportMutation.mutate()}
                disabled={!exportConfig.name || createExportMutation.isPending}
                className="w-full px-6 py-3 rounded-xl bg-green-500 text-white font-semibold hover:bg-green-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {createExportMutation.isPending ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Download className="w-5 h-5" />
                )}
                Create Export
              </button>
            </div>

            {/* Success Message */}
            {stepCompletion.export && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-6 rounded-2xl bg-green-500/10 border border-green-500/30 text-center"
              >
                <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-green-400 mb-2">Congratulations! 🎉</h3>
                <p className="text-surface-400 mb-4">
                  Your ML dataset is ready and export is being prepared.
                </p>
                <Link
                  href="/dashboard/exports"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-green-500 text-white hover:bg-green-600 transition-colors"
                >
                  View Exports
                  <ArrowRight className="w-5 h-5" />
                </Link>
              </motion.div>
            )}
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="ML Dataset Wizard Guide"
        description="Learn how to prepare your data for machine learning"
        sections={wizardTutorial}
        storageKey="wizard"
      />

      {/* Header */}
      <div className="max-w-5xl mx-auto mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/20">
              <Wand2 className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">ML Dataset Preparation Wizard</h1>
              <p className="text-surface-400">
                Step by step, prepare your dataset for model training
              </p>
            </div>
          </div>
          
          {/* Progress Indicator & Reset */}
          <div className="flex items-center gap-3">
            {selectedProjectId && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-400">Progress saved</span>
              </div>
            )}
            <button
              onClick={() => {
                if (confirm('Are you sure you want to start over? All progress will be lost.')) {
                  localStorage.removeItem(WIZARD_STORAGE_KEY)
                  setCurrentStep(0)
                  setSelectedProjectId('')
                  setStepCompletion({
                    project: false,
                    collect: false,
                    process: false,
                    label: false,
                    split: false,
                    augment: false,
                    document: false,
                    export: false,
                  })
                  setSplitConfig({
                    train_ratio: 0.8,
                    val_ratio: 0.1,
                    test_ratio: 0.1,
                    stratify_by: 'labels',
                    shuffle: true,
                  })
                  setDatasetCard({
                    title: '',
                    description: '',
                    license: 'mit',
                    languages: ['en'],
                    task_categories: [],
                    tags: [],
                  })
                  setExportConfig({
                    name: '',
                    format: 'jsonl',
                    splits: ['train', 'val', 'test'],
                    include_annotations: true,
                  })
                }
              }}
              className="px-3 py-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 text-surface-400 hover:text-white text-sm transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Start Over
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            {STEPS.map((step, index) => {
              const isCompleted = stepCompletion[step.id]
              const isCurrent = currentStep === index
              const isPast = currentStep > index
              
              return (
                <button
                  key={step.id}
                  onClick={() => setCurrentStep(index)}
                  className={cn(
                    'flex flex-col items-center gap-2 relative group',
                    isCurrent ? 'text-brand-400' : isCompleted ? 'text-green-400' : 'text-surface-500'
                  )}
                >
                  {/* Connector Line */}
                  {index < STEPS.length - 1 && (
                    <div className={cn(
                      'absolute top-5 left-1/2 w-full h-0.5 -translate-y-1/2',
                      isPast || isCompleted ? 'bg-green-500' : 'bg-surface-700'
                    )} style={{ width: 'calc(100% + 2rem)' }} />
                  )}
                  
                  {/* Step Icon */}
                  <div className={cn(
                    'w-10 h-10 rounded-xl flex items-center justify-center z-10 transition-all',
                    isCurrent ? 'bg-brand-500 text-white scale-110' :
                    isCompleted ? 'bg-green-500 text-white' :
                    'bg-surface-700 text-surface-400 group-hover:bg-surface-600'
                  )}>
                    {isCompleted ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      <step.icon className="w-5 h-5" />
                    )}
                  </div>
                  
                  {/* Step Label */}
                  <span className="text-xs font-medium">{step.title}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Step Content */}
      <div className="max-w-4xl mx-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
            className="p-8 rounded-3xl glass"
          >
            {renderStepContent()}
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-8">
          <button
            onClick={goToPrevStep}
            disabled={currentStep === 0}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-surface-800 text-surface-300 hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
            Previous Step
          </button>

          <div className="text-surface-400 text-sm">
            Step {currentStep + 1} of {STEPS.length}
          </div>

          <button
            onClick={goToNextStep}
            disabled={currentStep === STEPS.length - 1}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next Step
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}


'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { qualityApi, projectsApi } from '@/lib/api'
import { useTranslations } from 'next-intl'
import { 
  ShieldCheck, 
  AlertTriangle, 
  FileSearch, 
  Layers, 
  Database,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3,
  FileText,
  Image,
  Mic,
  Loader2,
  RefreshCw,
  Download,
  Trash2,
  Upload,
  Users,
  Link2,
  TrendingUp,
  Volume2,
  Video,
  Copy,
  Scissors,
  Network,
  Box,
  FileOutput,
  Share2,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const qualityTutorial: TutorialSection[] = [
  {
    title: 'Quality & Validation Overview',
    content: 'This comprehensive dashboard helps you ensure data quality, detect issues, and validate your datasets before ML training. Use the tabs to access different quality tools.',
    tips: [
      'Start with the Overview tab for a quick health check',
      'Always run Data Leakage detection before training models',
      'Create backups before major data operations',
    ],
  },
  {
    title: 'Data Leakage Detection',
    content: 'Data leakage occurs when information from your test set leaks into training, leading to overly optimistic results. This tool detects common leakage patterns.',
    steps: [
      { title: 'Exact Duplicates', description: 'Identical items appearing in both train and test sets' },
      { title: 'Near Duplicates', description: 'Very similar items that could cause leakage' },
      { title: 'Source Overlap', description: 'Items from the same source in different splits' },
      { title: 'Temporal Leakage', description: 'Future data appearing in training set' },
    ],
    warning: 'Always fix leakage issues before training production models.',
  },
  {
    title: 'Inter-Annotator Agreement',
    content: 'Measure labeling consistency when multiple annotators work on the same data. Cohen\'s Kappa quantifies agreement beyond chance.',
    steps: [
      { title: 'Almost Perfect (>0.8)', description: 'Excellent agreement - labels are reliable' },
      { title: 'Substantial (0.6-0.8)', description: 'Good agreement - minor inconsistencies' },
      { title: 'Moderate (0.4-0.6)', description: 'Fair agreement - review labeling guidelines' },
      { title: 'Below 0.4', description: 'Poor agreement - retrain annotators' },
    ],
  },
  {
    title: 'Quality Metrics',
    content: 'Automatic quality analysis for different data types.',
    steps: [
      { title: 'Images', description: 'Detect blur, check brightness, verify resolution' },
      { title: 'Text', description: 'Analyze readability, coherence, language quality' },
      { title: 'Audio', description: 'Measure SNR, detect noise, check clarity' },
    ],
  },
  {
    title: 'Video & Audio Tools',
    content: 'Specialized tools for multimedia data processing.',
    steps: [
      { title: 'Video Duplicates', description: 'Find duplicate videos using perceptual hashing' },
      { title: 'Scene Detection', description: 'Identify scene boundaries for video segmentation' },
      { title: 'Noise Reduction', description: 'Remove background noise from audio files' },
      { title: 'Speaker Analysis', description: 'Identify and cluster speakers in audio' },
    ],
  },
  {
    title: 'Multimodal Alignment',
    content: 'Tools for aligning and grouping related items across different modalities (text, image, audio, video).',
    steps: [
      { title: 'Auto-Align by Time', description: 'Group items created within 60 seconds of each other' },
      { title: 'Auto-Align by Content', description: 'Group items based on semantic similarity' },
      { title: 'Cross-Modal Search', description: 'Search images/audio/video using text queries' },
    ],
    tips: [
      'Multimodal alignment is crucial for training vision-language models',
      'Use CLIP embeddings for best image-text alignment results',
    ],
  },
  {
    title: 'Time Series & Graph Analysis',
    content: 'Specialized analysis tools for temporal and relational data.',
    steps: [
      { title: 'Stationarity Tests', description: 'Check if time series data is stationary' },
      { title: 'Anomaly Detection', description: 'Find outliers using statistical methods' },
      { title: 'Graph Centrality', description: 'Identify important nodes in graph data' },
      { title: 'Community Detection', description: 'Find clusters in graph structures' },
    ],
  },
  {
    title: 'Export Tools & Backups',
    content: 'Export to external annotation tools and manage backups.',
    steps: [
      { title: 'CVAT Export', description: 'Export annotations for CVAT (Computer Vision Annotation Tool)' },
      { title: 'Labelbox Export', description: 'Export to Labelbox format' },
      { title: 'Label Studio', description: 'Export to Label Studio JSON format' },
      { title: 'Backups', description: 'Create and restore dataset backups' },
    ],
    tips: [
      'Create backups before bulk operations',
      'Use external tools for complex annotation tasks',
    ],
  },
]

interface Project {
  id: string
  name: string
  data_type: string
}

interface LeakageResult {
  overall_status: string
  total_issues: number
  recommendations: string[]
  checks: {
    exact_duplicates?: { has_leakage: boolean; exact_duplicates_found: number }
    near_duplicates?: { has_leakage: boolean; near_duplicates_found: number }
    source_overlap?: { has_leakage: boolean }
    temporal_leakage?: { has_leakage: boolean }
  }
}

interface AgreementResult {
  annotator_count: number
  item_count: number
  average_cohens_kappa: number
  fleiss_kappa: number | null
  overall_interpretation: string
  quality_threshold_met: boolean
}

interface QualityBatchResult {
  total_checked: number
  passed: number
  failed: number
  pass_rate: number
  issues_summary: Record<string, number>
}

interface BackupInfo {
  name: string
  path: string
  compressed: boolean
  size_bytes: number
  modified_at: string
  manifest?: {
    item_count: number
    project_name: string
  }
}

export default function QualityDashboardPage() {
  const t = useTranslations()
  const searchParams = useSearchParams()
  const projectIdParam = searchParams.get('project_id')
  
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<string>(projectIdParam || '')
  const [activeTab, setActiveTab] = useState<'overview' | 'leakage' | 'agreement' | 'metrics' | 'validation' | 'backup' | 'audio' | 'multimodal' | 'timeseries' | 'video' | 'graph' | 'threed' | 'export'>('overview')
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Results
  const [leakageResult, setLeakageResult] = useState<LeakageResult | null>(null)
  const [agreementResult, setAgreementResult] = useState<AgreementResult | null>(null)
  const [qualityResult, setQualityResult] = useState<QualityBatchResult | null>(null)
  const [backups, setBackups] = useState<BackupInfo[]>([])
  
  useEffect(() => {
    loadProjects()
  }, [])
  
  useEffect(() => {
    if (selectedProject) {
      loadBackups()
    }
  }, [selectedProject])
  
  const loadProjects = async () => {
    try {
      const result = await projectsApi.list({ limit: 100 })
      // API returns array directly, not { items: [] }
      const projectList = Array.isArray(result) ? result : (result.items || [])
      setProjects(projectList)
      if (!selectedProject && projectList.length > 0) {
        setSelectedProject(projectList[0].id)
      }
    } catch (err) {
      console.error('Failed to load projects:', err)
    }
  }
  
  const loadBackups = async () => {
    if (!selectedProject) {
      setBackups([])
      return
    }
    try {
      const result = await qualityApi.listBackups(selectedProject)
      setBackups(result.backups || [])
    } catch (err) {
      // Silently handle - backups may not be available
      setBackups([])
    }
  }
  
  const runLeakageCheck = async () => {
    if (!selectedProject) return
    setLoading(true)
    setError(null)
    try {
      const result = await qualityApi.checkLeakage(selectedProject)
      setLeakageResult(result)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to check leakage')
    } finally {
      setLoading(false)
    }
  }
  
  const runAgreementCheck = async () => {
    if (!selectedProject) return
    setLoading(true)
    setError(null)
    try {
      const result = await qualityApi.calculateAgreement(selectedProject)
      setAgreementResult(result)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to calculate agreement')
    } finally {
      setLoading(false)
    }
  }
  
  const runQualityCheck = async () => {
    if (!selectedProject) return
    setLoading(true)
    setError(null)
    try {
      const result = await qualityApi.batchQualityCheck(selectedProject)
      setQualityResult(result)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to run quality check')
    } finally {
      setLoading(false)
    }
  }
  
  const createBackup = async () => {
    if (!selectedProject) return
    setLoading(true)
    setError(null)
    try {
      await qualityApi.createBackup(selectedProject)
      await loadBackups()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create backup')
    } finally {
      setLoading(false)
    }
  }
  
  const deleteBackup = async (backupName: string) => {
    if (!confirm('Are you sure you want to delete this backup?')) return
    try {
      await qualityApi.deleteBackup(backupName)
      await loadBackups()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete backup')
    }
  }
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'clean': return 'text-green-600 bg-green-100'
      case 'warning': return 'text-yellow-600 bg-yellow-100'
      case 'critical': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }
  
  const getInterpretationColor = (interpretation: string) => {
    switch (interpretation) {
      case 'almost_perfect': return 'text-green-600'
      case 'substantial': return 'text-green-500'
      case 'moderate': return 'text-yellow-600'
      case 'fair': return 'text-orange-500'
      case 'slight': return 'text-red-500'
      default: return 'text-red-600'
    }
  }
  
  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'leakage', label: 'Data Leakage', icon: FileSearch },
    { id: 'agreement', label: 'Agreement', icon: ShieldCheck },
    { id: 'metrics', label: 'Metrics', icon: Layers },
    { id: 'video', label: 'Video', icon: Video },
    { id: 'audio', label: 'Audio', icon: Volume2 },
    { id: 'multimodal', label: 'Multimodal', icon: Link2 },
    { id: 'timeseries', label: 'Time Series', icon: TrendingUp },
    { id: 'graph', label: 'Graph', icon: Network },
    { id: 'threed', label: '3D Data', icon: Box },
    { id: 'export', label: 'Export Tools', icon: FileOutput },
    { id: 'validation', label: 'Validation', icon: CheckCircle },
    { id: 'backup', label: 'Backups', icon: Database },
  ]

  return (
    <div className="space-y-6 p-6">
      {/* Tutorial */}
      <TutorialPanel
        title="Quality & Validation Guide"
        description="Learn how to validate data quality and detect issues"
        sections={qualityTutorial}
        storageKey="quality"
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('nav.quality')}</h1>
          <p className="text-surface-400 mt-1">{t('quality.description') || 'Check data quality, detect issues, and manage backups'}</p>
        </div>
        
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="px-4 py-2 bg-surface-800 border border-surface-700 rounded-lg text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
        >
          <option value="">Select project...</option>
          {projects.map(project => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </div>
      
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}
      
      {/* Tabs */}
      <div className="border-b border-surface-700">
        <nav className="flex space-x-8">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-1 py-4 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-brand-500 text-brand-400'
                  : 'border-transparent text-surface-400 hover:text-white hover:border-surface-600'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
      
      {/* Content */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
        {!selectedProject ? (
          <div className="text-center py-12 text-surface-400">
            Please select a project to continue
          </div>
        ) : (
          <>
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-white">Quality Overview</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                    <div className="flex items-center gap-3">
                      <FileSearch className="w-8 h-8 text-blue-400" />
                      <div>
                        <h3 className="font-medium text-white">Data Leakage</h3>
                        <p className="text-sm text-surface-400">Check for data leakage between splits</p>
                      </div>
                    </div>
                    <button
                      onClick={runLeakageCheck}
                      disabled={loading}
                      className="mt-4 w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Run Check'}
                    </button>
                  </div>
                  
                  <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4">
                    <div className="flex items-center gap-3">
                      <ShieldCheck className="w-8 h-8 text-green-400" />
                      <div>
                        <h3 className="font-medium text-white">Annotator Agreement</h3>
                        <p className="text-sm text-surface-400">Calculate Cohen's Kappa</p>
                      </div>
                    </div>
                    <button
                      onClick={runAgreementCheck}
                      disabled={loading}
                      className="mt-4 w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Calculate'}
                    </button>
                  </div>
                  
                  <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-4">
                    <div className="flex items-center gap-3">
                      <Layers className="w-8 h-8 text-purple-400" />
                      <div>
                        <h3 className="font-medium text-white">Quality Metrics</h3>
                        <p className="text-sm text-surface-400">Blur, SNR, Readability</p>
                      </div>
                    </div>
                    <button
                      onClick={runQualityCheck}
                      disabled={loading}
                      className="mt-4 w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Analyze'}
                    </button>
                  </div>
                </div>
                
                {/* Quick Results */}
                {leakageResult && (
                  <div className={`rounded-lg p-4 ${getStatusColor(leakageResult.overall_status)}`}>
                    <h3 className="font-medium">Data Leakage Result:</h3>
                    <p>Status: {leakageResult.overall_status} | Issues: {leakageResult.total_issues}</p>
                  </div>
                )}
                
                {agreementResult && (
                  <div className="bg-surface-800 rounded-lg p-4">
                    <h3 className="font-medium text-white">Agreement Result:</h3>
                    <p className={getInterpretationColor(agreementResult.overall_interpretation || 'unknown')}>
                      Cohen's Kappa: {(agreementResult.average_cohens_kappa ?? 0).toFixed(3)} ({agreementResult.overall_interpretation || 'N/A'})
                    </p>
                  </div>
                )}
                
                {qualityResult && (
                  <div className="bg-surface-800 rounded-lg p-4">
                    <h3 className="font-medium text-white">Quality Result:</h3>
                    <p className="text-surface-300">
                      Passed: {qualityResult.passed ?? 0} of {qualityResult.total_checked ?? 0} 
                      ({((qualityResult.pass_rate ?? 0) * 100).toFixed(1)}%)
                    </p>
                  </div>
                )}
              </div>
            )}
            
            {/* Leakage Tab */}
            {activeTab === 'leakage' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">Data Leakage Detection</h2>
                  <button
                    onClick={runLeakageCheck}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Run Check
                  </button>
                </div>
                
                {leakageResult ? (
                  <div className="space-y-4">
                    <div className={`rounded-lg p-4 ${getStatusColor(leakageResult.overall_status)}`}>
                      <div className="flex items-center gap-2">
                        {leakageResult.overall_status === 'clean' ? (
                          <CheckCircle className="w-5 h-5" />
                        ) : (
                          <AlertTriangle className="w-5 h-5" />
                        )}
                        <span className="font-medium">
                          Overall Status: {leakageResult.overall_status}
                        </span>
                      </div>
                      <p className="mt-1">Total Issues: {leakageResult.total_issues}</p>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="border border-surface-700 rounded-lg p-4">
                        <h3 className="font-medium text-white mb-2">Exact Duplicates</h3>
                        {leakageResult.checks.exact_duplicates ? (
                          <div className="flex items-center gap-2">
                            {leakageResult.checks.exact_duplicates.has_leakage ? (
                              <XCircle className="w-5 h-5 text-red-500" />
                            ) : (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            )}
                            <span className="text-surface-300">{leakageResult.checks.exact_duplicates.exact_duplicates_found} found</span>
                          </div>
                        ) : (
                          <span className="text-surface-500">Not checked</span>
                        )}
                      </div>
                      
                      <div className="border border-surface-700 rounded-lg p-4">
                        <h3 className="font-medium text-white mb-2">Near Duplicates</h3>
                        {leakageResult.checks.near_duplicates ? (
                          <div className="flex items-center gap-2">
                            {leakageResult.checks.near_duplicates.has_leakage ? (
                              <XCircle className="w-5 h-5 text-red-500" />
                            ) : (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            )}
                            <span className="text-surface-300">{leakageResult.checks.near_duplicates.near_duplicates_found} found</span>
                          </div>
                        ) : (
                          <span className="text-surface-500">Not checked</span>
                        )}
                      </div>
                      
                      <div className="border border-surface-700 rounded-lg p-4">
                        <h3 className="font-medium text-white mb-2">Source Overlap</h3>
                        {leakageResult.checks.source_overlap ? (
                          <div className="flex items-center gap-2">
                            {leakageResult.checks.source_overlap.has_leakage ? (
                              <XCircle className="w-5 h-5 text-red-500" />
                            ) : (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            )}
                            <span className="text-surface-300">{leakageResult.checks.source_overlap.has_leakage ? 'Detected' : 'Clean'}</span>
                          </div>
                        ) : (
                          <span className="text-surface-500">Not checked</span>
                        )}
                      </div>
                      
                      <div className="border border-surface-700 rounded-lg p-4">
                        <h3 className="font-medium text-white mb-2">Temporal Leakage</h3>
                        {leakageResult.checks.temporal_leakage ? (
                          <div className="flex items-center gap-2">
                            {leakageResult.checks.temporal_leakage.has_leakage ? (
                              <XCircle className="w-5 h-5 text-red-500" />
                            ) : (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            )}
                            <span className="text-surface-300">{leakageResult.checks.temporal_leakage.has_leakage ? 'Detected' : 'Clean'}</span>
                          </div>
                        ) : (
                          <span className="text-surface-500">Not checked</span>
                        )}
                      </div>
                    </div>
                    
                    {leakageResult.recommendations.length > 0 && (
                      <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                        <h3 className="font-medium text-yellow-400 mb-2">Recommendations:</h3>
                        <ul className="list-disc list-inside text-yellow-300 space-y-1">
                          {leakageResult.recommendations.map((rec, i) => (
                            <li key={i}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-surface-400">
                    Click "Run Check" to start the leakage detection
                  </div>
                )}
              </div>
            )}
            
            {/* Agreement Tab */}
            {activeTab === 'agreement' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">Inter-Annotator Agreement</h2>
                  <button
                    onClick={runAgreementCheck}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Calculate
                  </button>
                </div>
                
                {agreementResult ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-surface-800 rounded-lg p-4 text-center">
                        <div className="text-3xl font-bold text-white">
                          {agreementResult.annotator_count}
                        </div>
                        <div className="text-sm text-surface-400">Annotators</div>
                      </div>
                      
                      <div className="bg-surface-800 rounded-lg p-4 text-center">
                        <div className="text-3xl font-bold text-white">
                          {agreementResult.item_count}
                        </div>
                        <div className="text-sm text-surface-400">Items</div>
                      </div>
                      
                      <div className="bg-surface-800 rounded-lg p-4 text-center">
                        <div className={`text-3xl font-bold ${getInterpretationColor(agreementResult.overall_interpretation || 'unknown')}`}>
                          {(agreementResult.average_cohens_kappa ?? 0).toFixed(3)}
                        </div>
                        <div className="text-sm text-surface-400">Cohen's Kappa</div>
                      </div>
                    </div>
                    
                    <div className={`rounded-lg p-4 ${
                      agreementResult.quality_threshold_met ? 'bg-green-500/10 border border-green-500/20 text-green-400' : 'bg-yellow-500/10 border border-yellow-500/20 text-yellow-400'
                    }`}>
                      <div className="flex items-center gap-2">
                        {agreementResult.quality_threshold_met ? (
                          <CheckCircle className="w-5 h-5" />
                        ) : (
                          <AlertTriangle className="w-5 h-5" />
                        )}
                        <span className="font-medium">
                          Interpretation: {agreementResult.overall_interpretation}
                        </span>
                      </div>
                      <p className="mt-1 text-sm">
                        {agreementResult.quality_threshold_met
                          ? 'Labeling quality meets acceptable threshold'
                          : 'Labeling quality needs improvement'}
                      </p>
                    </div>
                    
                    {agreementResult.fleiss_kappa != null && (
                      <div className="bg-surface-800 rounded-lg p-4">
                        <h3 className="font-medium text-white mb-2">Fleiss' Kappa (Multi-Annotator):</h3>
                        <div className="text-2xl font-bold text-white">
                          {(agreementResult.fleiss_kappa ?? 0).toFixed(3)}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-surface-400">
                    Click "Calculate" to compute inter-annotator agreement
                  </div>
                )}
              </div>
            )}
            
            {/* Metrics Tab */}
            {activeTab === 'metrics' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">Advanced Quality Metrics</h2>
                  <button
                    onClick={runQualityCheck}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Analyze
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Image className="w-5 h-5 text-blue-400" />
                      <h3 className="font-medium text-white">Images</h3>
                    </div>
                    <p className="text-sm text-surface-400">Blur, Brightness, Resolution</p>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="w-5 h-5 text-green-400" />
                      <h3 className="font-medium text-white">Text</h3>
                    </div>
                    <p className="text-sm text-surface-400">Readability, Coherence</p>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Mic className="w-5 h-5 text-purple-400" />
                      <h3 className="font-medium text-white">Audio</h3>
                    </div>
                    <p className="text-sm text-surface-400">SNR, Clarity</p>
                  </div>
                </div>
                
                {qualityResult && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-center">
                        <div className="text-3xl font-bold text-green-400">
                          {qualityResult.passed}
                        </div>
                        <div className="text-sm text-surface-400">Passed</div>
                      </div>
                      
                      <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-center">
                        <div className="text-3xl font-bold text-red-400">
                          {qualityResult.failed}
                        </div>
                        <div className="text-sm text-surface-400">Failed</div>
                      </div>
                      
                      <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 text-center">
                        <div className="text-3xl font-bold text-blue-400">
                          {((qualityResult.pass_rate ?? 0) * 100).toFixed(1)}%
                        </div>
                        <div className="text-sm text-surface-400">Pass Rate</div>
                      </div>
                    </div>
                    
                    {qualityResult.issues_summary && Object.keys(qualityResult.issues_summary).length > 0 && (
                      <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                        <h3 className="font-medium text-yellow-400 mb-2">Issues Detected:</h3>
                        <div className="space-y-1">
                          {Object.entries(qualityResult.issues_summary).map(([issue, count]) => (
                            <div key={issue} className="flex justify-between text-yellow-300">
                              <span>{issue}</span>
                              <span>{count} items</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            
            {/* Validation Tab */}
            {activeTab === 'validation' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-white">Data Validation</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border border-surface-700 rounded-lg p-4">
                    <h3 className="font-medium text-white mb-2">Schema Validation</h3>
                    <p className="text-sm text-surface-400 mb-4">
                      Validate data structure with JSON Schema
                    </p>
                    <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                      Configure Schema
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <h3 className="font-medium text-white mb-2">Missing Values</h3>
                    <p className="text-sm text-surface-400 mb-4">
                      Check for missing and incomplete values
                    </p>
                    <button 
                      onClick={async () => {
                        try {
                          const result = await qualityApi.checkCompleteness(selectedProject)
                          console.log('Completeness:', result)
                          alert(`Completeness: ${((result.overall_completeness ?? 0) * 100).toFixed(1)}%`)
                        } catch (err) {
                          console.error(err)
                        }
                      }}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    >
                      Check Completeness
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <h3 className="font-medium text-white mb-2">Outlier Detection</h3>
                    <p className="text-sm text-surface-400 mb-4">
                      Detect outliers using IQR/Z-score methods
                    </p>
                    <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                      Detect Outliers
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <h3 className="font-medium text-white mb-2">Temporal Split</h3>
                    <p className="text-sm text-surface-400 mb-4">
                      Time-based splitting for Time Series data
                    </p>
                    <button 
                      onClick={async () => {
                        try {
                          const result = await qualityApi.temporalSplit({
                            project_id: selectedProject,
                            train_ratio: 0.7,
                            val_ratio: 0.15,
                            test_ratio: 0.15,
                            gap_days: 0
                          })
                          alert(`Split completed: Train=${result.train?.count}, Val=${result.val?.count}, Test=${result.test?.count}`)
                        } catch (err) {
                          console.error(err)
                        }
                      }}
                      className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
                    >
                      Apply Temporal Split
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Video Tab */}
            {activeTab === 'video' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">Video Quality & Analysis</h2>
                  <button
                    onClick={async () => {
                      if (!selectedProject) return
                      try {
                        setLoading(true)
                        const result = await qualityApi.batchAnalyzeVideos(selectedProject)
                        alert(`Analyzed ${result.analyzed}/${result.total} videos\n\nQuality Summary:\n• Excellent: ${result.quality_summary.excellent}\n• Good: ${result.quality_summary.good}\n• Fair: ${result.quality_summary.fair}\n• Poor: ${result.quality_summary.poor}\n\nIssues found: ${result.issues.length}`)
                      } catch (err) {
                        console.error(err)
                      } finally {
                        setLoading(false)
                      }
                    }}
                    disabled={loading}
                    className="px-3 py-1.5 bg-surface-700 text-surface-300 rounded-lg hover:bg-surface-600 transition-colors text-sm flex items-center gap-2"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                    Batch Analyze All
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Duplicate Detection */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Copy className="w-5 h-5 text-red-400" />
                      <h3 className="font-medium text-white">Duplicate Detection</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Find duplicate videos using perceptual hashing
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.findDuplicateVideos(selectedProject)
                          if (result.duplicate_pairs > 0) {
                            alert(`Found ${result.duplicate_pairs} duplicate pairs out of ${result.total_videos} videos!\n\nDetails logged to console.`)
                            console.log('Duplicate videos:', result.duplicates)
                          } else {
                            alert(`No duplicates found in ${result.total_videos} videos`)
                          }
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to find duplicates')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Find Duplicates'}
                    </button>
                  </div>
                  
                  {/* Scene Detection */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Scissors className="w-5 h-5 text-blue-400" />
                      <h3 className="font-medium text-white">Scene Detection</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Detect scene boundaries in videos
                    </p>
                    <input
                      type="text"
                      placeholder="Video Item ID..."
                      id="sceneVideoId"
                      className="w-full mb-2 px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white placeholder-surface-500 text-sm focus:outline-none focus:border-brand-500"
                    />
                    <button 
                      onClick={async () => {
                        const itemId = (document.getElementById('sceneVideoId') as HTMLInputElement)?.value
                        if (!itemId) {
                          alert('Please enter a video item ID')
                          return
                        }
                        try {
                          setLoading(true)
                          const result = await qualityApi.detectVideoScenes(itemId)
                          alert(`Detected ${result.scene_count} scenes\nTotal duration: ${result.total_duration?.toFixed(1)}s`)
                          console.log('Scenes:', result.scenes)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to detect scenes')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Detect Scenes'}
                    </button>
                  </div>
                  
                  {/* Quality Analysis */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart3 className="w-5 h-5 text-green-400" />
                      <h3 className="font-medium text-white">Quality Analysis</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Analyze blur, brightness, contrast, stability
                    </p>
                    <input
                      type="text"
                      placeholder="Video Item ID..."
                      id="qualityVideoId"
                      className="w-full mb-2 px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white placeholder-surface-500 text-sm focus:outline-none focus:border-brand-500"
                    />
                    <button 
                      onClick={async () => {
                        const itemId = (document.getElementById('qualityVideoId') as HTMLInputElement)?.value
                        if (!itemId) {
                          alert('Please enter a video item ID')
                          return
                        }
                        try {
                          setLoading(true)
                          const result = await qualityApi.analyzeVideoQuality(itemId)
                          alert(`Quality Grade: ${result.quality_grade?.toUpperCase()}\nScore: ${result.quality_score}/100\n\nBlur: ${result.blur_score}\nBrightness: ${result.brightness_avg}\nContrast: ${result.contrast_avg}\nStability: ${result.frame_stability}%\n\nBlurry: ${result.is_blurry ? 'Yes' : 'No'}\nCamera Shake: ${result.camera_shake ? 'Yes' : 'No'}`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to analyze quality')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Analyze Quality'}
                    </button>
                  </div>
                  
                  {/* Smart Thumbnail */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Image className="w-5 h-5 text-purple-400" />
                      <h3 className="font-medium text-white">Smart Thumbnail</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Generate thumbnail from best quality frame
                    </p>
                    <input
                      type="text"
                      placeholder="Video Item ID..."
                      id="thumbVideoId"
                      className="w-full mb-2 px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white placeholder-surface-500 text-sm focus:outline-none focus:border-brand-500"
                    />
                    <button 
                      onClick={async () => {
                        const itemId = (document.getElementById('thumbVideoId') as HTMLInputElement)?.value
                        if (!itemId) {
                          alert('Please enter a video item ID')
                          return
                        }
                        try {
                          setLoading(true)
                          const result = await qualityApi.generateSmartThumbnail(itemId)
                          alert(`Thumbnail generated!\nTime offset: ${result.time_offset}s\nQuality score: ${result.quality_score}`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to generate thumbnail')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate Thumbnail'}
                    </button>
                  </div>
                </div>
                
                {/* Info Section */}
                <div className="border border-surface-700 rounded-lg p-4">
                  <h3 className="font-medium text-white mb-3">Video Analysis Features</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">🔍</div>
                      <h4 className="text-sm font-medium text-white">Perceptual Hash</h4>
                      <p className="text-xs text-surface-400">Duplicate detection</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">✂️</div>
                      <h4 className="text-sm font-medium text-white">Scene Detection</h4>
                      <p className="text-xs text-surface-400">Find scene boundaries</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">📊</div>
                      <h4 className="text-sm font-medium text-white">Quality Metrics</h4>
                      <p className="text-xs text-surface-400">Blur, brightness, stability</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">🖼️</div>
                      <h4 className="text-sm font-medium text-white">Smart Thumbnail</h4>
                      <p className="text-xs text-surface-400">Best frame selection</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Audio Tab */}
            {activeTab === 'audio' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-white">Audio Processing & Analysis</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Volume2 className="w-5 h-5 text-purple-400" />
                      <h3 className="font-medium text-white">Noise Reduction</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Remove background noise using spectral gating
                    </p>
                    <button 
                      onClick={async () => {
                        alert('Select an audio item from the Data page to apply noise reduction')
                      }}
                      className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                    >
                      Reduce Noise
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Users className="w-5 h-5 text-blue-400" />
                      <h3 className="font-medium text-white">Speaker Analysis</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Identify and cluster speakers in audio files
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.analyzeSpeakers(selectedProject)
                          alert(`Found ${result.unique_speakers} unique speakers in ${result.total_items_analyzed} items`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to analyze speakers')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Analyze Speakers'}
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Mic className="w-5 h-5 text-green-400" />
                      <h3 className="font-medium text-white">Voice Activity Detection</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Detect speech segments in audio
                    </p>
                    <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
                      Detect VAD
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Users className="w-5 h-5 text-orange-400" />
                      <h3 className="font-medium text-white">Speaker Diarization</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Identify who spoke when in audio
                    </p>
                    <button className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors">
                      Diarize Audio
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Multimodal Tab */}
            {activeTab === 'multimodal' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">Multimodal Alignment</h2>
                  <button
                    onClick={async () => {
                      if (!selectedProject) return
                      try {
                        const result = await qualityApi.getMultimodalStatistics(selectedProject)
                        alert(`Statistics:\n• Total Items: ${result.total_items}\n• Grouped: ${result.grouped_items}\n• Ungrouped: ${result.ungrouped_items}\n• Total Groups: ${result.total_groups}`)
                      } catch (err) {
                        console.error(err)
                      }
                    }}
                    className="px-3 py-1.5 bg-surface-700 text-surface-300 rounded-lg hover:bg-surface-600 transition-colors text-sm"
                  >
                    View Statistics
                  </button>
                </div>
                
                {/* Auto Alignment Section */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="w-5 h-5 text-blue-400" />
                      <h3 className="font-medium text-white">Auto-Align by Timestamp</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Group items created within 60 seconds of each other
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.autoAlignMultimodal(selectedProject)
                          alert(`Created ${result.groups_created} groups from ${result.items_processed} items`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to auto-align')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Align by Time'}
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Layers className="w-5 h-5 text-purple-400" />
                      <h3 className="font-medium text-white">Auto-Align by Content</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Group items based on content similarity (CLIP/embeddings)
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.autoAlignByContent(selectedProject)
                          alert(`Created ${result.groups_created} groups based on content similarity`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to auto-align by content')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Align by Content'}
                    </button>
                  </div>
                </div>
                
                {/* Cross-Modal Search */}
                <div className="border border-surface-700 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <FileSearch className="w-5 h-5 text-green-400" />
                    <h3 className="font-medium text-white">Cross-Modal Search</h3>
                  </div>
                  <p className="text-sm text-surface-400 mb-4">
                    Search for images/audio/video using natural language
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Enter search query..."
                      id="crossModalSearch"
                      className="flex-1 px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white placeholder-surface-500 focus:outline-none focus:border-brand-500"
                    />
                    <select
                      id="targetModality"
                      className="px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white focus:outline-none focus:border-brand-500"
                    >
                      <option value="image">Images</option>
                      <option value="audio">Audio</option>
                      <option value="video">Video</option>
                    </select>
                    <button
                      onClick={async () => {
                        if (!selectedProject) return
                        const query = (document.getElementById('crossModalSearch') as HTMLInputElement)?.value
                        const modality = (document.getElementById('targetModality') as HTMLSelectElement)?.value
                        if (!query) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.crossModalSearch(selectedProject, query, modality)
                          if (result.results?.length > 0) {
                            alert(`Found ${result.total} matches!\nTop result score: ${result.results[0].score}`)
                          } else {
                            alert('No matching items found')
                          }
                          console.log('Search results:', result)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Search failed')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
                    </button>
                  </div>
                </div>
                
                {/* Group Management */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Link2 className="w-5 h-5 text-blue-400" />
                      <h3 className="font-medium text-white">List Groups</h3>
                    </div>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          const result = await qualityApi.listMultimodalGroups(selectedProject)
                          if (result.groups?.length > 0) {
                            const groupList = result.groups.map((g: any) => `• ${g.group_name}: ${g.item_count} items (${g.data_types.join(', ')})`).join('\n')
                            alert(`${result.total_groups} Groups:\n${groupList}`)
                          } else {
                            alert('No multimodal groups found')
                          }
                          console.log('Groups:', result)
                        } catch (err) {
                          console.error(err)
                        }
                      }}
                      className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      View All Groups
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <FileSearch className="w-5 h-5 text-yellow-400" />
                      <h3 className="font-medium text-white">Unaligned Items</h3>
                    </div>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          const result = await qualityApi.getUnalignedItems(selectedProject)
                          alert(`${result.unaligned_count} unaligned items out of ${result.total_items} total`)
                        } catch (err) {
                          console.error(err)
                        }
                      }}
                      className="w-full px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
                    >
                      Find Unaligned
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart3 className="w-5 h-5 text-orange-400" />
                      <h3 className="font-medium text-white">Compute Alignment</h3>
                    </div>
                    <input
                      type="text"
                      placeholder="Group ID..."
                      id="alignmentGroupId"
                      className="w-full mb-2 px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white placeholder-surface-500 text-sm focus:outline-none focus:border-brand-500"
                    />
                    <button 
                      onClick={async () => {
                        const groupId = (document.getElementById('alignmentGroupId') as HTMLInputElement)?.value
                        if (!groupId) return
                        try {
                          const result = await qualityApi.computeMultimodalAlignment(groupId)
                          alert(`Alignment Score: ${((result.overall_alignment_score ?? 0) * 100).toFixed(1)}%\nWell Aligned: ${result.is_well_aligned ? 'Yes' : 'No'}`)
                        } catch (err) {
                          console.error(err)
                        }
                      }}
                      className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
                    >
                      Check Alignment
                    </button>
                  </div>
                </div>
                
                {/* Alignment Methods Info */}
                <div className="border border-surface-700 rounded-lg p-4">
                  <h3 className="font-medium text-white mb-3">Supported Alignment Methods</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">🖼️↔️📝</div>
                      <h4 className="text-sm font-medium text-white">Image-Text</h4>
                      <p className="text-xs text-surface-400">CLIP embeddings</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">🎵↔️📝</div>
                      <h4 className="text-sm font-medium text-white">Audio-Text</h4>
                      <p className="text-xs text-surface-400">Transcription matching</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">🎬↔️📝</div>
                      <h4 className="text-sm font-medium text-white">Video-Text</h4>
                      <p className="text-xs text-surface-400">Keyframe analysis</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">🖼️↔️🎵</div>
                      <h4 className="text-sm font-medium text-white">Image-Audio</h4>
                      <p className="text-xs text-surface-400">Via transcription</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Time Series Tab */}
            {activeTab === 'timeseries' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-white">Time Series Analysis</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="w-5 h-5 text-blue-400" />
                      <h3 className="font-medium text-white">Stationarity Test</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Test for stationarity using ADF and KPSS tests
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.analyzeProjectTimeSeries(selectedProject)
                          if (result.stationarity) {
                            alert(`Stationarity: ${result.stationarity.conclusion}\n${result.stationarity.recommendation}`)
                          } else {
                            alert('Analysis completed. Check console for details.')
                          }
                          console.log('Time series analysis:', result)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to analyze time series')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Test Stationarity'}
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-5 h-5 text-red-400" />
                      <h3 className="font-medium text-white">Anomaly Detection</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Detect anomalies using Z-score, IQR, or Isolation Forest
                    </p>
                    <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
                      Detect Anomalies
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart3 className="w-5 h-5 text-green-400" />
                      <h3 className="font-medium text-white">Seasonal Decomposition</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Decompose into trend, seasonal, and residual
                    </p>
                    <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
                      Decompose
                    </button>
                  </div>
                  
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <RefreshCw className="w-5 h-5 text-purple-400" />
                      <h3 className="font-medium text-white">Interpolation</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Fill missing values (linear, spline, forward/backward)
                    </p>
                    <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                      Interpolate Missing
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Graph Tab */}
            {activeTab === 'graph' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">Graph Data Analysis</h2>
                  <button
                    onClick={async () => {
                      if (!selectedProject) return
                      try {
                        setLoading(true)
                        const result = await qualityApi.analyzeGraph(selectedProject)
                        alert(`Graph Analysis:\n• Nodes: ${result.basic_metrics?.num_nodes || 0}\n• Edges: ${result.basic_metrics?.num_edges || 0}\n• Density: ${result.basic_metrics?.density || 0}\n• Communities: ${result.communities?.count || 0}`)
                        console.log('Graph analysis:', result)
                      } catch (err) {
                        console.error(err)
                      } finally {
                        setLoading(false)
                      }
                    }}
                    disabled={loading}
                    className="px-3 py-1.5 bg-surface-700 text-surface-300 rounded-lg hover:bg-surface-600 transition-colors text-sm flex items-center gap-2"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                    Analyze Graph
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Create Graph */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Network className="w-5 h-5 text-blue-400" />
                      <h3 className="font-medium text-white">Create Graph</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Create graph structure from project items
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.createGraph(selectedProject)
                          alert(`Graph created!\n• Nodes: ${result.metrics?.num_nodes || 0}\n• Edges: ${result.metrics?.num_edges || 0}\n• Density: ${(result.metrics?.density || 0).toFixed(4)}`)
                          console.log('Graph:', result)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to create graph')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create Graph'}
                    </button>
                  </div>
                  
                  {/* Graph Metrics */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart3 className="w-5 h-5 text-green-400" />
                      <h3 className="font-medium text-white">Centrality Analysis</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Compute degree, betweenness, and closeness centrality
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.analyzeGraph(selectedProject)
                          if (result.top_nodes?.length > 0) {
                            const topList = result.top_nodes.slice(0, 5).map((n: any) => 
                              `${n.node}: ${(n.degree_centrality || 0).toFixed(3)}`
                            ).join('\n')
                            alert(`Top 5 Nodes by Centrality:\n${topList}`)
                          } else {
                            alert('No centrality data available')
                          }
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to analyze')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Analyze Centrality'}
                    </button>
                  </div>
                  
                  {/* Export Graph */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Download className="w-5 h-5 text-purple-400" />
                      <h3 className="font-medium text-white">Export Graph</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-3">
                      Export to different formats
                    </p>
                    <select
                      id="graphFormat"
                      className="w-full mb-2 px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                    >
                      <option value="graphml">GraphML</option>
                      <option value="gml">GML</option>
                      <option value="networkx">NetworkX JSON</option>
                      <option value="cytoscape">Cytoscape JSON</option>
                    </select>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        const format = (document.getElementById('graphFormat') as HTMLSelectElement)?.value || 'graphml'
                        try {
                          setLoading(true)
                          const result = await qualityApi.exportGraph(selectedProject, format)
                          alert(`Graph exported!\nFormat: ${result.format}\nNodes: ${result.nodes}\nEdges: ${result.edges}`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to export')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Export'}
                    </button>
                  </div>
                  
                  {/* Community Detection */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Users className="w-5 h-5 text-orange-400" />
                      <h3 className="font-medium text-white">Community Detection</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Find communities using label propagation
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.analyzeGraph(selectedProject)
                          if (result.communities) {
                            const sizes = result.communities.sizes?.join(', ') || 'N/A'
                            alert(`Communities Found: ${result.communities.count}\nSizes: ${sizes}`)
                          }
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to detect')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Find Communities'}
                    </button>
                  </div>
                </div>
                
                {/* Graph Features Info */}
                <div className="border border-surface-700 rounded-lg p-4">
                  <h3 className="font-medium text-white mb-3">Supported Graph Features</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">🔗</div>
                      <h4 className="text-sm font-medium text-white">Node/Edge</h4>
                      <p className="text-xs text-surface-400">Data model</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">📊</div>
                      <h4 className="text-sm font-medium text-white">Centrality</h4>
                      <p className="text-xs text-surface-400">Degree, Betweenness</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">👥</div>
                      <h4 className="text-sm font-medium text-white">Communities</h4>
                      <p className="text-xs text-surface-400">Label propagation</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">📤</div>
                      <h4 className="text-sm font-medium text-white">Export</h4>
                      <p className="text-xs text-surface-400">GraphML, GML, JSON</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* 3D Data Tab */}
            {activeTab === 'threed' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">3D Data Analysis</h2>
                  <button
                    onClick={async () => {
                      if (!selectedProject) return
                      try {
                        setLoading(true)
                        const result = await qualityApi.analyze3dData(selectedProject)
                        alert(`3D Analysis:\n• Items: ${result.items_count}\n• Total Points: ${result.total_points}\n• Annotations: ${result.total_annotations}\n• Labels: ${result.unique_labels?.join(', ') || 'None'}`)
                      } catch (err) {
                        console.error(err)
                      } finally {
                        setLoading(false)
                      }
                    }}
                    disabled={loading}
                    className="px-3 py-1.5 bg-surface-700 text-surface-300 rounded-lg hover:bg-surface-600 transition-colors text-sm flex items-center gap-2"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                    Analyze Project
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Parse Point Cloud */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Box className="w-5 h-5 text-blue-400" />
                      <h3 className="font-medium text-white">Parse Point Cloud</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-3">
                      Parse and analyze point cloud data
                    </p>
                    <input
                      type="text"
                      placeholder="Item ID..."
                      id="pointCloudItemId"
                      className="w-full mb-2 px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white placeholder-surface-500 text-sm focus:outline-none focus:border-brand-500"
                    />
                    <button 
                      onClick={async () => {
                        const itemId = (document.getElementById('pointCloudItemId') as HTMLInputElement)?.value
                        if (!itemId) {
                          alert('Please enter an item ID')
                          return
                        }
                        try {
                          setLoading(true)
                          const result = await qualityApi.parsePointCloud(itemId)
                          const stats = result.statistics || {}
                          alert(`Point Cloud Statistics:\n• Points: ${stats.num_points || 0}\n• Volume: ${stats.volume || 0}\n• Density: ${stats.density || 0}\n• Has Color: ${stats.has_color ? 'Yes' : 'No'}`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to parse')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Parse'}
                    </button>
                  </div>
                  
                  {/* Export 3D */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Download className="w-5 h-5 text-purple-400" />
                      <h3 className="font-medium text-white">Export 3D Data</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-3">
                      Export point cloud to various formats
                    </p>
                    <input
                      type="text"
                      placeholder="Item ID..."
                      id="export3dItemId"
                      className="w-full mb-2 px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white placeholder-surface-500 text-sm focus:outline-none focus:border-brand-500"
                    />
                    <select
                      id="export3dFormat"
                      className="w-full mb-2 px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                    >
                      <option value="ply">PLY</option>
                      <option value="pcd">PCD</option>
                      <option value="xyz">XYZ</option>
                      <option value="kitti">KITTI (Annotations)</option>
                    </select>
                    <button 
                      onClick={async () => {
                        const itemId = (document.getElementById('export3dItemId') as HTMLInputElement)?.value
                        const format = (document.getElementById('export3dFormat') as HTMLSelectElement)?.value || 'ply'
                        if (!itemId) {
                          alert('Please enter an item ID')
                          return
                        }
                        try {
                          setLoading(true)
                          const result = await qualityApi.export3d(itemId, format)
                          alert(`Export complete!\nFormat: ${result.format}\nPoints: ${result.points}\nAnnotations: ${result.annotations}`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to export')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Export'}
                    </button>
                  </div>
                </div>
                
                {/* 3D Features Info */}
                <div className="border border-surface-700 rounded-lg p-4">
                  <h3 className="font-medium text-white mb-3">Supported 3D Features</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">☁️</div>
                      <h4 className="text-sm font-medium text-white">Point Cloud</h4>
                      <p className="text-xs text-surface-400">XYZ + RGB</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">📦</div>
                      <h4 className="text-sm font-medium text-white">3D BBox</h4>
                      <p className="text-xs text-surface-400">Annotations</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">📊</div>
                      <h4 className="text-sm font-medium text-white">Statistics</h4>
                      <p className="text-xs text-surface-400">Bounds, density</p>
                    </div>
                    <div className="bg-surface-800 rounded p-3 text-center">
                      <div className="text-2xl mb-1">📤</div>
                      <h4 className="text-sm font-medium text-white">Export</h4>
                      <p className="text-xs text-surface-400">PLY, PCD, KITTI</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Export Tools Tab */}
            {activeTab === 'export' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-white">External Annotation Tools</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* CVAT Export */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <FileOutput className="w-5 h-5 text-blue-400" />
                      <h3 className="font-medium text-white">CVAT Export</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Export to CVAT XML format for image/video annotation
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.exportToCvat(selectedProject)
                          alert(`CVAT Export complete!\nItems: ${result.items_count}\nFilename: ${result.filename}`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to export')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Export to CVAT'}
                    </button>
                  </div>
                  
                  {/* Labelbox Export */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Share2 className="w-5 h-5 text-green-400" />
                      <h3 className="font-medium text-white">Labelbox Export</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Export to Labelbox NDJSON format
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.exportToLabelbox(selectedProject)
                          alert(`Labelbox Export complete!\nItems: ${result.items_count}\nFilename: ${result.filename}`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to export')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Export to Labelbox'}
                    </button>
                  </div>
                  
                  {/* Label Studio Export */}
                  <div className="border border-surface-700 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="w-5 h-5 text-purple-400" />
                      <h3 className="font-medium text-white">Label Studio Export</h3>
                    </div>
                    <p className="text-sm text-surface-400 mb-4">
                      Export to Label Studio JSON format
                    </p>
                    <button 
                      onClick={async () => {
                        if (!selectedProject) return
                        try {
                          setLoading(true)
                          const result = await qualityApi.exportToLabelStudio(selectedProject)
                          alert(`Label Studio Export complete!\nItems: ${result.items_count}\nFilename: ${result.filename}`)
                        } catch (err: any) {
                          setError(err.response?.data?.detail || 'Failed to export')
                        } finally {
                          setLoading(false)
                        }
                      }}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Export to Label Studio'}
                    </button>
                  </div>
                </div>
                
                {/* Supported Formats Info */}
                <div className="border border-surface-700 rounded-lg p-4">
                  <h3 className="font-medium text-white mb-3">Supported Export Formats</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-surface-800 rounded p-4">
                      <h4 className="font-medium text-blue-400 mb-2">CVAT</h4>
                      <ul className="text-sm text-surface-400 space-y-1">
                        <li>• Bounding boxes</li>
                        <li>• Polygons</li>
                        <li>• Polylines</li>
                        <li>• Points</li>
                        <li>• Video tracks</li>
                      </ul>
                    </div>
                    <div className="bg-surface-800 rounded p-4">
                      <h4 className="font-medium text-green-400 mb-2">Labelbox</h4>
                      <ul className="text-sm text-surface-400 space-y-1">
                        <li>• Bounding boxes</li>
                        <li>• Polygons</li>
                        <li>• Points</li>
                        <li>• Classifications</li>
                        <li>• Text annotations</li>
                      </ul>
                    </div>
                    <div className="bg-surface-800 rounded p-4">
                      <h4 className="font-medium text-purple-400 mb-2">Label Studio</h4>
                      <ul className="text-sm text-surface-400 space-y-1">
                        <li>• Rectangle labels</li>
                        <li>• Polygon labels</li>
                        <li>• Choices</li>
                        <li>• Text annotations</li>
                        <li>• Image/Audio/Video</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Backup Tab */}
            {activeTab === 'backup' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">Backup Management</h2>
                  <button
                    onClick={createBackup}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                    Create Backup
                  </button>
                </div>
                
                <div className="space-y-4">
                  {backups.length === 0 ? (
                    <div className="text-center py-12 text-surface-400">
                      No backups available
                    </div>
                  ) : (
                    backups.map(backup => (
                      <div key={backup.name} className="border border-surface-700 rounded-lg p-4 flex items-center justify-between">
                        <div>
                          <div className="font-medium text-white">{backup.name}</div>
                          <div className="text-sm text-surface-400">
                            {new Date(backup.modified_at).toLocaleString()}
                            {backup.size_bytes && ` • ${(backup.size_bytes / 1024 / 1024).toFixed(2)} MB`}
                            {backup.manifest && ` • ${backup.manifest.item_count} items`}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button className="p-2 text-blue-400 hover:bg-blue-500/10 rounded transition-colors">
                            <Upload className="w-4 h-4" />
                          </button>
                          <button 
                            onClick={() => deleteBackup(backup.name)}
                            className="p-2 text-red-400 hover:bg-red-500/10 rounded transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

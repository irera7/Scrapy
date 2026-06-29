'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobsApi, projectsApi } from '@/lib/api'
import { formatNumber, formatDateTime, getStatusColor } from '@/lib/utils'
import { motion } from 'framer-motion'
import { Link } from '@/i18n/navigation'
import { useSearchParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import {
  Plus,
  Play,
  Square,
  Trash2,
  Loader2,
  PlayCircle,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Clock,
  XCircle,
  RotateCcw,
  Edit,
  MousePointer,
  FileCode,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const jobsTutorial: TutorialSection[] = [
  {
    title: 'What are Scraping Jobs?',
    content: 'Jobs are automated tasks that collect data from various sources like Google, Twitter, Reddit, YouTube, and custom websites. Each job runs independently and saves data to its associated project.',
    tips: [
      'You can run multiple jobs simultaneously',
      'Jobs automatically retry on temporary failures',
      'Monitor progress in real-time with live updates',
    ],
  },
  {
    title: 'Creating a New Job',
    content: 'Click "New Job" to create a scraping task. You\'ll configure the data source, search parameters, and collection settings.',
    steps: [
      { title: 'Select Project', description: 'Choose which project will store the collected data' },
      { title: 'Choose Provider', description: 'Select data source (SerpAPI, Twitter, Reddit, Custom, etc.)' },
      { title: 'Configure Query', description: 'Set search terms, filters, and data limits' },
      { title: 'Set Schedule', description: 'Optional: Schedule recurring data collection' },
    ],
    warning: 'Some providers require API keys. Configure them in the Providers page first.',
  },
  {
    title: 'Job Status Guide',
    content: 'Jobs go through several states during execution. Understanding these helps you monitor and troubleshoot effectively.',
    steps: [
      { title: 'Pending', description: 'Job is created but not yet started' },
      { title: 'Running', description: 'Actively collecting data (shows spinner)' },
      { title: 'Completed', description: 'Successfully finished collecting data' },
      { title: 'Failed', description: 'Encountered an error - check error message' },
      { title: 'Cancelled', description: 'Manually stopped by user' },
    ],
  },
  {
    title: 'Job Actions',
    content: 'Each job has action buttons depending on its current status.',
    steps: [
      { title: 'Play Button', description: 'Start or re-run a pending/completed job' },
      { title: 'Stop Button', description: 'Cancel a running job' },
      { title: 'Retry Button', description: 'Restart a failed or cancelled job' },
      { title: 'Edit Button', description: 'Modify job configuration' },
      { title: 'Delete Button', description: 'Remove job (keeps collected data)' },
    ],
    tips: [
      'Use filters to find specific jobs by project or status',
      'Check the Visual Scraper for point-and-click selector building',
      'Use Templates for commonly scraped websites',
    ],
  },
]

const statusIcons: Record<string, any> = {
  pending: Clock,
  queued: Clock,
  running: Loader2,
  completed: CheckCircle,
  failed: AlertTriangle,
  cancelled: XCircle,
}

export default function JobsPage() {
  const t = useTranslations()
  const searchParams = useSearchParams()
  const projectId = searchParams.get('project')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const queryClient = useQueryClient()

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const { data: jobs, isLoading, refetch } = useQuery({
    queryKey: ['jobs', projectId, statusFilter],
    queryFn: () => jobsApi.list({
      project_id: projectId || undefined,
      status_filter: statusFilter || undefined,
    }),
    refetchInterval: 5000,
  })

  const runMutation = useMutation({
    mutationFn: (id: string) => jobsApi.run(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job started')
    },
    onError: () => {
      toast.error('Failed to start job')
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (id: string) => jobsApi.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job cancelled')
    },
  })

  const retryMutation = useMutation({
    mutationFn: (id: string) => jobsApi.retry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job restarted')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => jobsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job deleted')
    },
  })

  const stats = {
    total: jobs?.length || 0,
    running: jobs?.filter((j: any) => j.status === 'running').length || 0,
    completed: jobs?.filter((j: any) => j.status === 'completed').length || 0,
    failed: jobs?.filter((j: any) => j.status === 'failed').length || 0,
  }

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Scraping Jobs Guide"
        description="Learn how to create, run, and manage data collection jobs"
        sections={jobsTutorial}
        storageKey="jobs"
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">{t('jobs.title')}</h1>
          <p className="text-surface-400">{t('jobs.description') || 'Manage your data collection jobs'}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => refetch()}
            className="p-3 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <Link
            href="/dashboard/visual-scraper"
            className="inline-flex items-center gap-2 px-4 py-3 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors text-surface-300 hover:text-white"
            title="Visual Scraper"
          >
            <MousePointer className="w-5 h-5" />
            <span className="hidden sm:inline">Visual Scraper</span>
          </Link>
          <Link
            href="/dashboard/templates"
            className="inline-flex items-center gap-2 px-4 py-3 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors text-surface-300 hover:text-white"
            title="Templates"
          >
            <FileCode className="w-5 h-5" />
            <span className="hidden sm:inline">Templates</span>
          </Link>
          <Link
            href="/dashboard/jobs/new"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors"
          >
            <Plus className="w-5 h-5" />
            {t('jobs.newJob')}
          </Link>
        </div>
      </div>

      {/* Stats */}
      {jobs?.length > 0 && (
        <div className="flex gap-4 mb-6">
          <div className="px-4 py-2 rounded-xl bg-surface-800/50 border border-surface-700">
            <span className="text-surface-400 text-sm">Total: </span>
            <span className="font-medium">{stats.total}</span>
          </div>
          {stats.running > 0 && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
              <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
              <span className="text-yellow-400 text-sm font-medium">{stats.running} running</span>
            </div>
          )}
          <div className="px-4 py-2 rounded-xl bg-green-500/10 border border-green-500/20">
            <span className="text-green-400 text-sm">Completed: </span>
            <span className="font-medium text-green-400">{stats.completed}</span>
          </div>
          {stats.failed > 0 && (
            <div className="px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
              <span className="text-red-400 text-sm">Failed: </span>
              <span className="font-medium text-red-400">{stats.failed}</span>
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <select
          value={projectId || ''}
          onChange={(e) => {
            const url = new URL(window.location.href)
            if (e.target.value) {
              url.searchParams.set('project', e.target.value)
            } else {
              url.searchParams.delete('project')
            }
            window.history.pushState({}, '', url)
            location.reload()
          }}
          className="px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
        >
          <option value="">All projects</option>
          {projects?.map((project: any) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
        
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Jobs List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
        </div>
      ) : jobs?.length > 0 ? (
        <div className="space-y-4">
          {jobs.map((job: any, index: number) => {
            const StatusIcon = statusIcons[job.status] || Clock
            const projectName = projects?.find((p: any) => p.id === job.project_id)?.name
            
            return (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="rounded-xl glass p-6"
              >
                <div className="flex items-center gap-6">
                  {/* Status Icon */}
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    job.status === 'completed' ? 'bg-green-500/10 text-green-400' :
                    job.status === 'running' ? 'bg-yellow-500/10 text-yellow-400' :
                    job.status === 'failed' ? 'bg-red-500/10 text-red-400' :
                    'bg-surface-700 text-surface-400'
                  }`}>
                    <StatusIcon className={`w-6 h-6 ${job.status === 'running' ? 'animate-spin' : ''}`} />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <Link 
                      href={`/dashboard/jobs/${job.id}`}
                      className="font-semibold hover:text-brand-400 transition-colors"
                    >
                      {job.name}
                    </Link>
                    <div className="flex items-center gap-4 text-sm text-surface-400 mt-1">
                      <span className="px-2 py-0.5 rounded bg-surface-700 text-xs">
                        {job.provider}
                      </span>
                      {projectName && (
                        <span className="truncate">{projectName}</span>
                      )}
                      <span>{formatNumber(job.items_collected || 0)} collected</span>
                      {job.last_run && (
                        <span>Last run: {formatDateTime(job.last_run)}</span>
                      )}
                    </div>
                    {job.error_message && job.status === 'failed' && (
                      <p className="text-xs text-red-400 mt-2 truncate">{job.error_message}</p>
                    )}
                  </div>

                  {/* Status Badge */}
                  <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${getStatusColor(job.status)}`}>
                    {job.status}
                  </span>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {(job.status === 'pending' || job.status === 'completed') && (
                      <button
                        onClick={() => runMutation.mutate(job.id)}
                        disabled={runMutation.isPending}
                        className="p-2 rounded-lg bg-brand-500 hover:bg-brand-600 text-white transition-colors"
                        title="Run job"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    )}
                    {job.status === 'running' && (
                      <button
                        onClick={() => cancelMutation.mutate(job.id)}
                        disabled={cancelMutation.isPending}
                        className="p-2 rounded-lg bg-yellow-500 hover:bg-yellow-600 text-white transition-colors"
                        title="Cancel job"
                      >
                        <Square className="w-4 h-4" />
                      </button>
                    )}
                    {(job.status === 'failed' || job.status === 'cancelled') && (
                      <button
                        onClick={() => retryMutation.mutate(job.id)}
                        disabled={retryMutation.isPending}
                        className="p-2 rounded-lg bg-brand-500 hover:bg-brand-600 text-white transition-colors"
                        title="Retry job"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                    <Link
                      href={`/dashboard/jobs/${job.id}/edit`}
                      className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors"
                      title="Edit job"
                    >
                      <Edit className="w-4 h-4" />
                    </Link>
                    <Link
                      href={`/dashboard/jobs/${job.id}`}
                      className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors"
                      title="View details"
                    >
                      <PlayCircle className="w-4 h-4" />
                    </Link>
                    <button
                      onClick={() => {
                        if (confirm('Delete this job?')) {
                          deleteMutation.mutate(job.id)
                        }
                      }}
                      className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-red-400 transition-colors"
                      title="Delete job"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      ) : (
        <div className="text-center py-20">
          <div className="w-20 h-20 rounded-full bg-surface-800 flex items-center justify-center mx-auto mb-4">
            <PlayCircle className="w-10 h-10 text-surface-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">{t('jobs.noJobs')}</h3>
          <p className="text-surface-400 mb-6">
            {t('jobs.createFirst')}
          </p>
          <Link
            href="/dashboard/jobs/new"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors"
          >
            <Plus className="w-5 h-5" />
            {t('jobs.newJob')}
          </Link>
        </div>
      )}
    </div>
  )
}

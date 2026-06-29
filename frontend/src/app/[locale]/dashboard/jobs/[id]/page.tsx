'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobsApi, projectsApi } from '@/lib/api'
import { formatNumber, formatDateTime, getStatusColor } from '@/lib/utils'
import { motion } from 'framer-motion'
import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import {
  ArrowLeft,
  Play,
  Square,
  RotateCcw,
  Trash2,
  Loader2,
  CheckCircle,
  AlertTriangle,
  Clock,
  XCircle,
  Activity,
  Terminal,
  Settings,
  Database,
  RefreshCw,
  Info,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import toast from 'react-hot-toast'

const statusIcons: Record<string, any> = {
  pending: Clock,
  queued: Clock,
  running: Loader2,
  completed: CheckCircle,
  failed: AlertTriangle,
  cancelled: XCircle,
}

const logLevelColors: Record<string, string> = {
  info: 'text-blue-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
  debug: 'text-surface-400',
}

export default function JobDetailPage({ params }: { params: { id: string } }) {
  const { id } = params
  const queryClient = useQueryClient()
  const [showConfig, setShowConfig] = useState(false)
  const [logLevel, setLogLevel] = useState<string>('')

  const { data: job, isLoading } = useQuery({
    queryKey: ['job', id],
    queryFn: () => jobsApi.get(id),
    refetchInterval: 5000,
  })

  const { data: project } = useQuery({
    queryKey: ['project', job?.project_id],
    queryFn: () => projectsApi.get(job.project_id),
    enabled: !!job?.project_id,
  })

  const { data: logs, refetch: refetchLogs } = useQuery({
    queryKey: ['job-logs', id, logLevel],
    queryFn: () => jobsApi.getLogs(id, { level: logLevel || undefined, limit: 100 }),
    enabled: !!job,
    refetchInterval: job?.status === 'running' ? 3000 : false,
  })

  const runMutation = useMutation({
    mutationFn: () => jobsApi.run(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', id] })
      toast.success('Job started')
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () => jobsApi.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', id] })
      toast.success('Job cancelled')
    },
  })

  const retryMutation = useMutation({
    mutationFn: () => jobsApi.retry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', id] })
      toast.success('Job restarted')
    },
  })

  const resetMutation = useMutation({
    mutationFn: () => jobsApi.reset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', id] })
      toast.success('Job reset')
    },
  })

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
      </div>
    )
  }

  if (!job) {
    return (
      <div className="p-8">
        <Link
          href="/dashboard/jobs"
          className="inline-flex items-center gap-2 text-surface-400 hover:text-white mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Jobs
        </Link>
        <p className="text-surface-400">Job not found</p>
      </div>
    )
  }

  const StatusIcon = statusIcons[job.status] || Clock

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/dashboard/jobs"
          className="inline-flex items-center gap-2 text-surface-400 hover:text-white mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Jobs
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${
              job.status === 'completed' ? 'bg-green-500/10 text-green-400' :
              job.status === 'running' ? 'bg-yellow-500/10 text-yellow-400' :
              job.status === 'failed' ? 'bg-red-500/10 text-red-400' :
              'bg-surface-700 text-surface-400'
            }`}>
              <StatusIcon className={`w-8 h-8 ${job.status === 'running' ? 'animate-spin' : ''}`} />
            </div>
            <div>
              <h1 className="text-3xl font-bold">{job.name}</h1>
              <div className="flex items-center gap-3 mt-1">
                <span className="px-2 py-1 rounded-lg text-xs bg-surface-700">
                  {job.provider}
                </span>
                <span className={`px-2 py-1 rounded-lg text-xs font-medium ${getStatusColor(job.status)}`}>
                  {job.status}
                </span>
                {project && (
                  <Link 
                    href={`/dashboard/projects/${project.id}`}
                    className="text-sm text-brand-400 hover:text-brand-300"
                  >
                    {project.name}
                  </Link>
                )}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            {(job.status === 'pending' || job.status === 'completed') && (
              <button
                onClick={() => runMutation.mutate()}
                disabled={runMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 text-white font-medium hover:bg-brand-600 transition-colors"
              >
                <Play className="w-4 h-4" />
                Run
              </button>
            )}
            {job.status === 'running' && (
              <button
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-yellow-500 text-white font-medium hover:bg-yellow-600 transition-colors"
              >
                <Square className="w-4 h-4" />
                Cancel
              </button>
            )}
            {(job.status === 'failed' || job.status === 'cancelled') && (
              <button
                onClick={() => retryMutation.mutate()}
                disabled={retryMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 text-white font-medium hover:bg-brand-600 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Retry
              </button>
            )}
            <button
              onClick={() => resetMutation.mutate()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={<Database className="w-5 h-5" />}
          label="Items Collected"
          value={formatNumber(job.items_collected || 0)}
          color="bg-brand-500/10 text-brand-400"
        />
        <StatCard
          icon={<Activity className="w-5 h-5" />}
          label="Priority"
          value={String(job.priority)}
          color="bg-blue-500/10 text-blue-400"
        />
        <StatCard
          icon={<RotateCcw className="w-5 h-5" />}
          label="Retries"
          value={`${job.retry_count} / ${job.max_retries}`}
          color="bg-yellow-500/10 text-yellow-400"
        />
        <StatCard
          icon={<Clock className="w-5 h-5" />}
          label="Last Run"
          value={job.last_run ? formatDateTime(job.last_run) : 'Never'}
          color="bg-purple-500/10 text-purple-400"
        />
      </div>

      {/* Error Message */}
      {job.error_message && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
            <div>
              <h3 className="font-medium text-red-400">Error</h3>
              <p className="text-sm text-red-300 mt-1">{job.error_message}</p>
            </div>
          </div>
        </motion.div>
      )}

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Configuration */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl glass p-6"
        >
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center justify-between w-full mb-4"
          >
            <div className="flex items-center gap-3">
              <Settings className="w-5 h-5 text-surface-400" />
              <h2 className="text-lg font-semibold">Configuration</h2>
            </div>
            {showConfig ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
          
          {showConfig && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-surface-400 mb-1">Provider</h3>
                  <p className="capitalize">{job.provider}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-surface-400 mb-1">Schedule</h3>
                  <p>{job.schedule || 'Manual'}</p>
                </div>
              </div>
              
              {job.config && Object.keys(job.config).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-surface-400 mb-2">Job Config</h3>
                  <pre className="text-xs bg-surface-800 p-4 rounded-lg overflow-x-auto">
                    {JSON.stringify(job.config, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
          
          {!showConfig && (
            <p className="text-sm text-surface-400">Click to view job configuration</p>
          )}
        </motion.div>

        {/* Info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl glass p-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <Info className="w-5 h-5 text-surface-400" />
            <h2 className="text-lg font-semibold">Details</h2>
          </div>
          
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-surface-400">Job ID</span>
              <span className="font-mono text-xs">{job.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-surface-400">Created</span>
              <span>{formatDateTime(job.created_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-surface-400">Updated</span>
              <span>{formatDateTime(job.updated_at)}</span>
            </div>
            {job.next_run && (
              <div className="flex justify-between">
                <span className="text-surface-400">Next Run</span>
                <span>{formatDateTime(job.next_run)}</span>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Logs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="mt-8 rounded-2xl glass p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Terminal className="w-5 h-5 text-surface-400" />
            <h2 className="text-lg font-semibold">Logs</h2>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={logLevel}
              onChange={(e) => setLogLevel(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-surface-800 border border-surface-700 text-sm"
            >
              <option value="">All levels</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="debug">Debug</option>
            </select>
            <button
              onClick={() => refetchLogs()}
              className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {logs?.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto font-mono text-sm">
            {logs.map((log: any) => (
              <div key={log.id} className="p-3 rounded-lg bg-surface-800/50 flex items-start gap-3">
                <span className="text-xs text-surface-500 min-w-[140px]">
                  {formatDateTime(log.created_at)}
                </span>
                <span className={`text-xs uppercase font-semibold min-w-[60px] ${logLevelColors[log.level] || 'text-surface-400'}`}>
                  [{log.level}]
                </span>
                <span className="flex-1">{log.message}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-surface-400">
            <Terminal className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p>No logs yet</p>
          </div>
        )}
      </motion.div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode
  label: string
  value: string
  color: string
}) {
  return (
    <div className="rounded-xl glass p-4">
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center`}>
          {icon}
        </div>
      </div>
      <p className="text-sm text-surface-400">{label}</p>
      <p className="text-xl font-bold">{value}</p>
    </div>
  )
}

'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { workersApi } from '@/lib/api'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useTranslations } from 'next-intl'
import {
  Activity,
  Server,
  Cpu,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Loader2,
  PlayCircle,
  PauseCircle,
  Trash2,
  Layers,
  Zap,
  Timer,
  MemoryStick,
  Box,
  List,
  X,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const workersTutorial: TutorialSection[] = [
  {
    title: 'Worker Monitor Overview',
    content: 'The Worker Monitor shows the status of Celery background workers that process scraping jobs, exports, and data processing tasks. Monitor active tasks, queue status, and worker health.',
    tips: [
      'Workers handle all background processing tasks',
      'Page auto-refreshes every 5 seconds for real-time status',
      'Green banner indicates workers are online and ready',
    ],
  },
  {
    title: 'Worker Status',
    content: 'The status banner shows if workers are online. If workers are offline, scraping jobs and exports will be queued but not processed until workers start.',
    steps: [
      { title: 'Check Status', description: 'Green "Workers Online" means workers are running' },
      { title: 'View Details', description: 'See total workers and active task count' },
      { title: 'Last Checked', description: 'Timestamp shows when status was last updated' },
    ],
    warning: 'If workers are offline, start them using the command shown in the Troubleshooting section.',
  },
  {
    title: 'Stats Overview',
    content: 'The stats grid shows key metrics: total workers, active tasks currently running, queued tasks waiting to run, and total task queues.',
    tips: [
      'Active tasks are currently being processed',
      'Queued tasks are waiting for available workers',
      'Multiple queues help prioritize different task types',
    ],
  },
  {
    title: 'Active & Queued Tasks',
    content: 'View real-time lists of active and queued tasks. Each task shows its type, ID, and worker assignment. You can cancel running tasks if needed.',
    steps: [
      { title: 'View Active', description: 'See tasks currently being processed by workers' },
      { title: 'View Queued', description: 'See tasks waiting in queue' },
      { title: 'Cancel Task', description: 'Click X button to cancel a running task' },
    ],
    warning: 'Canceling a task may leave data in an incomplete state.',
  },
  {
    title: 'Task Types',
    content: 'Tasks are color-coded by type: blue for scraping, green for exports, purple for processing, and yellow for scheduled tasks. This helps identify what work is happening.',
    tips: [
      'Scraping tasks collect data from web sources',
      'Export tasks generate downloadable data files',
      'Processing tasks handle NLP and media analysis',
      'Scheduled tasks are triggered by the scheduler',
    ],
  },
  {
    title: 'Troubleshooting',
    content: 'If workers are offline, you need to start the Celery worker process. Use the provided command in your terminal to start workers.',
    steps: [
      { title: 'Start Workers', description: 'Run: celery -A app.workers.celery_app worker --loglevel=info --pool=solo' },
      { title: 'Verify', description: 'Refresh this page to see workers come online' },
      { title: 'Monitor with Flower', description: 'Optionally run Flower for a detailed monitoring dashboard' },
    ],
  },
]

export default function WorkersPage() {
  const t = useTranslations()
  const queryClient = useQueryClient()
  const [selectedTask, setSelectedTask] = useState<string | null>(null)

  // Fetch worker status
  const { data: status, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['workers-status'],
    queryFn: () => workersApi.getStatus(),
    refetchInterval: 5000, // Auto refresh every 5 seconds
  })

  // Fetch active tasks
  const { data: activeTasks, refetch: refetchActive } = useQuery({
    queryKey: ['workers-active-tasks'],
    queryFn: () => workersApi.getActiveTasks(),
    refetchInterval: 3000,
  })

  // Fetch reserved tasks
  const { data: reservedTasks, refetch: refetchReserved } = useQuery({
    queryKey: ['workers-reserved-tasks'],
    queryFn: () => workersApi.getReservedTasks(),
    refetchInterval: 5000,
  })

  // Fetch queues
  const { data: queues } = useQuery({
    queryKey: ['workers-queues'],
    queryFn: () => workersApi.getQueues(),
    refetchInterval: 10000,
  })

  // Fetch task result
  const { data: taskResult, isLoading: taskResultLoading } = useQuery({
    queryKey: ['task-result', selectedTask],
    queryFn: () => workersApi.getTaskResult(selectedTask!),
    enabled: !!selectedTask,
  })

  // Revoke task mutation
  const revokeMutation = useMutation({
    mutationFn: ({ taskId, terminate }: { taskId: string; terminate: boolean }) =>
      workersApi.revokeTask(taskId, terminate),
    onSuccess: () => {
      toast.success('Task revoked')
      queryClient.invalidateQueries({ queryKey: ['workers-active-tasks'] })
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to revoke task')
    },
  })

  const refreshAll = () => {
    refetchStatus()
    refetchActive()
    refetchReserved()
  }

  const getTaskTypeColor = (taskName: string) => {
    if (taskName.includes('scraping')) return 'text-blue-400 bg-blue-500/10'
    if (taskName.includes('export')) return 'text-green-400 bg-green-500/10'
    if (taskName.includes('process')) return 'text-purple-400 bg-purple-500/10'
    if (taskName.includes('scheduled')) return 'text-yellow-400 bg-yellow-500/10'
    return 'text-surface-400 bg-surface-700'
  }

  const formatUptime = (seconds: number) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Worker Monitor Guide"
        description="Learn how to monitor background tasks and workers"
        sections={workersTutorial}
        storageKey="workers"
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">{t('nav.workers')}</h1>
          <p className="text-surface-400">{t('workers.description') || 'Monitor Celery workers, tasks, and queues'}</p>
        </div>
        <button
          onClick={refreshAll}
          className="p-3 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Status Banner */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-6 rounded-2xl mb-8 ${
          status?.online
            ? 'bg-gradient-to-r from-green-600/20 to-emerald-600/20 border border-green-500/30'
            : 'bg-gradient-to-r from-red-600/20 to-orange-600/20 border border-red-500/30'
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${
              status?.online ? 'bg-green-500/20' : 'bg-red-500/20'
            }`}>
              {statusLoading ? (
                <Loader2 className="w-7 h-7 animate-spin text-surface-400" />
              ) : status?.online ? (
                <Activity className="w-7 h-7 text-green-400" />
              ) : (
                <XCircle className="w-7 h-7 text-red-400" />
              )}
            </div>
            <div>
              <h2 className={`text-xl font-bold ${status?.online ? 'text-green-400' : 'text-red-400'}`}>
                {status?.online ? 'Workers Online' : 'Workers Offline'}
              </h2>
              <p className="text-surface-400">
                {status?.message || `${status?.total_workers || 0} workers, ${status?.total_active_tasks || 0} active tasks`}
              </p>
            </div>
          </div>
          {status?.checked_at && (
            <div className="text-sm text-surface-500">
              Last checked: {new Date(status.checked_at).toLocaleTimeString()}
            </div>
          )}
        </div>
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-6 rounded-2xl glass"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-surface-400">Workers</span>
            <Server className="w-5 h-5 text-brand-400" />
          </div>
          <p className="text-3xl font-bold">{status?.total_workers || 0}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="p-6 rounded-2xl glass"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-surface-400">Active Tasks</span>
            <Zap className="w-5 h-5 text-yellow-400" />
          </div>
          <p className="text-3xl font-bold text-yellow-400">{activeTasks?.count || 0}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="p-6 rounded-2xl glass"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-surface-400">Queued Tasks</span>
            <List className="w-5 h-5 text-blue-400" />
          </div>
          <p className="text-3xl font-bold text-blue-400">{reservedTasks?.count || 0}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="p-6 rounded-2xl glass"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-surface-400">Queues</span>
            <Layers className="w-5 h-5 text-purple-400" />
          </div>
          <p className="text-3xl font-bold text-purple-400">{queues?.count || 0}</p>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Workers List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="p-6 rounded-2xl glass"
        >
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <Server className="w-5 h-5" />
            Workers
          </h3>
          
          {status?.workers?.length > 0 ? (
            <div className="space-y-3">
              {status.workers.map((worker: any) => (
                <div key={worker.name} className="p-4 rounded-xl bg-surface-800/50 border border-surface-700">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
                      <span className="font-medium">{worker.name}</span>
                    </div>
                    <span className="text-xs text-surface-500">
                      PID: {worker.pool?.processes?.[0] || 'N/A'}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-surface-500">Active</p>
                      <p className="font-medium text-yellow-400">{worker.active_tasks}</p>
                    </div>
                    <div>
                      <p className="text-surface-500">Reserved</p>
                      <p className="font-medium text-blue-400">{worker.reserved_tasks}</p>
                    </div>
                    <div>
                      <p className="text-surface-500">Concurrency</p>
                      <p className="font-medium">{worker.prefetch_count || 'N/A'}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Server className="w-12 h-12 text-surface-500 mx-auto mb-3" />
              <p className="text-surface-400">No workers online</p>
              <p className="text-sm text-surface-500">Start Celery workers to see them here</p>
            </div>
          )}
        </motion.div>

        {/* Active Tasks */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="p-6 rounded-2xl glass"
        >
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-yellow-400" />
            Active Tasks
          </h3>
          
          {activeTasks?.tasks?.length > 0 ? (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {activeTasks.tasks.map((task: any) => (
                <div key={task.id} className="p-4 rounded-xl bg-surface-800/50 border border-surface-700">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded text-xs ${getTaskTypeColor(task.name)}`}>
                          {task.name.split('.').pop()}
                        </span>
                        <Loader2 className="w-3 h-3 animate-spin text-yellow-400" />
                      </div>
                      <code className="text-xs text-surface-500 truncate block">
                        {task.id}
                      </code>
                      <p className="text-xs text-surface-400 mt-1">
                        Worker: {task.worker}
                      </p>
                    </div>
                    <button
                      onClick={() => revokeMutation.mutate({ taskId: task.id, terminate: true })}
                      disabled={revokeMutation.isPending}
                      className="p-2 rounded-lg text-surface-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Cancel task"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <p className="text-surface-400">No active tasks</p>
              <p className="text-sm text-surface-500">All tasks completed</p>
            </div>
          )}
        </motion.div>

        {/* Queued Tasks */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="p-6 rounded-2xl glass"
        >
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <List className="w-5 h-5 text-blue-400" />
            Queued Tasks
          </h3>
          
          {reservedTasks?.tasks?.length > 0 ? (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {reservedTasks.tasks.map((task: any) => (
                <div key={task.id} className="p-4 rounded-xl bg-surface-800/50 border border-surface-700">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className={`px-2 py-0.5 rounded text-xs ${getTaskTypeColor(task.name)}`}>
                        {task.name.split('.').pop()}
                      </span>
                      <code className="text-xs text-surface-500 ml-2">
                        {task.id.slice(0, 8)}...
                      </code>
                    </div>
                    <div className="flex items-center gap-2 text-blue-400">
                      <Timer className="w-4 h-4" />
                      <span className="text-xs">Waiting</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <List className="w-12 h-12 text-surface-500 mx-auto mb-3" />
              <p className="text-surface-400">No queued tasks</p>
            </div>
          )}
        </motion.div>

        {/* Queues */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="p-6 rounded-2xl glass"
        >
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <Layers className="w-5 h-5 text-purple-400" />
            Task Queues
          </h3>
          
          {queues?.queues?.length > 0 ? (
            <div className="space-y-3">
              {queues.queues.map((queue: any) => (
                <div key={queue.name} className="p-4 rounded-xl bg-surface-800/50 border border-surface-700">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{queue.name}</span>
                    <span className="px-2 py-0.5 rounded text-xs bg-purple-500/20 text-purple-400">
                      {queue.workers?.length || 0} workers
                    </span>
                  </div>
                  <div className="text-xs text-surface-500">
                    <p>Routing Key: {queue.routing_key || 'default'}</p>
                    {queue.exchange && <p>Exchange: {queue.exchange}</p>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Layers className="w-12 h-12 text-surface-500 mx-auto mb-3" />
              <p className="text-surface-400">No queues found</p>
            </div>
          )}
        </motion.div>
      </div>

      {/* Task Types Legend */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
        className="mt-8 p-6 rounded-2xl glass"
      >
        <h3 className="text-lg font-semibold mb-4">Task Types</h3>
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded text-sm bg-blue-500/10 text-blue-400">scraping</span>
            <span className="text-surface-400">Web scraping jobs</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded text-sm bg-green-500/10 text-green-400">export</span>
            <span className="text-surface-400">Data exports</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded text-sm bg-purple-500/10 text-purple-400">process</span>
            <span className="text-surface-400">Data processing</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded text-sm bg-yellow-500/10 text-yellow-400">scheduled</span>
            <span className="text-surface-400">Scheduled tasks</span>
          </div>
        </div>
      </motion.div>

      {/* Help Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="mt-6 p-6 rounded-2xl bg-surface-800/50 border border-surface-700"
      >
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
          Troubleshooting
        </h3>
        <div className="text-sm text-surface-400 space-y-2">
          <p>If workers are offline, start them with:</p>
          <code className="block p-3 rounded-lg bg-surface-900 text-green-400 font-mono">
            celery -A app.workers.celery_app worker --loglevel=info --pool=solo
          </code>
          <p className="mt-3">For Flower monitoring dashboard:</p>
          <code className="block p-3 rounded-lg bg-surface-900 text-green-400 font-mono">
            celery -A app.workers.celery_app flower --port=5555
          </code>
        </div>
      </motion.div>
    </div>
  )
}

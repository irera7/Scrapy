'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { schedulerApi, projectsApi } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import {
  Clock,
  Play,
  Pause,
  Trash2,
  Plus,
  RefreshCw,
  Calendar,
  Activity,
  AlertTriangle,
  CheckCircle,
  Settings,
  ChevronRight,
  Timer,
  Zap,
  Power,
  PowerOff,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const schedulerTutorial: TutorialSection[] = [
  {
    title: 'Scheduler Overview',
    content: 'The Scheduler automates your scraping jobs to run at specified times or intervals. Set up recurring data collection without manual intervention.',
    tips: [
      'Schedule jobs to collect fresh data automatically',
      'Use cron expressions for precise timing control',
      'Monitor job history and catch any failures',
    ],
  },
  {
    title: 'Starting the Scheduler',
    content: 'The scheduler service must be running for scheduled jobs to execute. Use the Start/Stop buttons to control the scheduler daemon.',
    steps: [
      { title: 'Check Status', description: 'View the "Status" card to see if scheduler is running' },
      { title: 'Start Scheduler', description: 'Click "Start Scheduler" if it shows Stopped' },
      { title: 'Verify', description: 'Status should change to "Running" with green indicator' },
    ],
    warning: 'Scheduled jobs will not run if the scheduler service is stopped.',
  },
  {
    title: 'Schedule Types',
    content: 'Choose from different schedule types based on your needs: Cron for complex schedules, Interval for regular repetition, One-time for single runs, or Conditional for triggered execution.',
    steps: [
      { title: 'Cron', description: 'Unix-style cron expressions (e.g., "0 9 * * *" for 9 AM daily)' },
      { title: 'Interval', description: 'Run every X minutes/hours/days' },
      { title: 'Once', description: 'Execute at a specific date and time' },
      { title: 'On Change', description: 'Trigger when source content changes' },
    ],
  },
  {
    title: 'Quick Presets',
    content: 'Use quick schedule presets for common timing patterns. Click on a preset to use its cron expression when creating a new schedule.',
    tips: [
      '"Every hour" - Great for frequently updated sources',
      '"Daily at midnight" - Good for daily data collection',
      '"Weekly" - Suitable for slower-changing content',
    ],
  },
  {
    title: 'Managing Scheduled Jobs',
    content: 'View all scheduled jobs, their status, run count, and next execution time. You can pause, resume, or delete jobs as needed.',
    steps: [
      { title: 'View Jobs', description: 'See all scheduled jobs with their current status' },
      { title: 'Pause/Resume', description: 'Temporarily pause jobs without deleting them' },
      { title: 'View Details', description: 'Click settings icon to see full job configuration' },
      { title: 'Delete', description: 'Remove jobs you no longer need' },
    ],
  },
  {
    title: 'Monitoring & Troubleshooting',
    content: 'Monitor job execution history and catch any errors. The scheduler tracks run counts, last execution time, and any error messages.',
    tips: [
      'Red warning icon indicates the last run had an error',
      'Check "Workers" page to see if tasks are processing',
      'View job details for complete error messages',
    ],
  },
]

export default function SchedulerPage() {
  const t = useTranslations()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  
  // Fetch scheduler stats
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['scheduler-stats'],
    queryFn: schedulerApi.getStats,
    refetchInterval: 5000,
  })
  
  // Fetch scheduled jobs
  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['scheduled-jobs'],
    queryFn: () => schedulerApi.listJobs({}),
    refetchInterval: 5000,
  })
  
  // Fetch cron presets
  const { data: presets } = useQuery({
    queryKey: ['cron-presets'],
    queryFn: schedulerApi.getCronPresets,
  })
  
  // Start scheduler mutation
  const startScheduler = useMutation({
    mutationFn: schedulerApi.start,
    onSuccess: () => {
      refetchStats()
    },
  })
  
  // Stop scheduler mutation
  const stopScheduler = useMutation({
    mutationFn: schedulerApi.stop,
    onSuccess: () => {
      refetchStats()
    },
  })
  
  // Pause job mutation
  const pauseJob = useMutation({
    mutationFn: schedulerApi.pauseJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-jobs'] })
    },
  })
  
  // Resume job mutation
  const resumeJob = useMutation({
    mutationFn: schedulerApi.resumeJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-jobs'] })
    },
  })
  
  // Delete job mutation
  const deleteJob = useMutation({
    mutationFn: schedulerApi.deleteJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-jobs'] })
    },
  })

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Scheduler Guide"
        description="Learn how to automate your scraping jobs with schedules"
        sections={schedulerTutorial}
        storageKey="scheduler"
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">{t('nav.scheduler')}</h1>
          <p className="text-surface-400">{t('scheduler.description') || 'Manage automated scraping schedules'}</p>
        </div>
        <div className="flex items-center gap-3">
          {stats?.running ? (
            <button
              onClick={() => stopScheduler.mutate()}
              disabled={stopScheduler.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
            >
              <PowerOff className="w-5 h-5" />
              Stop Scheduler
            </button>
          ) : (
            <button
              onClick={() => startScheduler.mutate()}
              disabled={startScheduler.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-colors"
            >
              <Power className="w-5 h-5" />
              Start Scheduler
            </button>
          )}
          <Link
            href="/dashboard/scheduler/new"
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors"
          >
            <Plus className="w-5 h-5" />
            New Schedule
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={<Activity className="w-6 h-6" />}
          label="Status"
          value={stats?.running ? 'Running' : 'Stopped'}
          color={stats?.running ? 'green' : 'red'}
        />
        <StatCard
          icon={<Calendar className="w-6 h-6" />}
          label="Total Jobs"
          value={stats?.total_jobs || 0}
          color="blue"
        />
        <StatCard
          icon={<Play className="w-6 h-6" />}
          label="Active Jobs"
          value={stats?.active_jobs || 0}
          color="brand"
        />
        <StatCard
          icon={<Clock className="w-6 h-6" />}
          label="Next Due"
          value={stats?.next_due ? formatDate(stats.next_due) : 'None'}
          color="purple"
          small
        />
      </div>

      {/* Cron Presets */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl glass p-6 mb-8"
      >
        <h2 className="text-xl font-semibold mb-4">Quick Schedule Presets</h2>
        <div className="flex flex-wrap gap-3">
          {presets?.presets?.map((preset: any) => (
            <div
              key={preset.key}
              className="px-4 py-2 rounded-xl bg-surface-800/50 hover:bg-surface-800 transition-colors cursor-pointer"
            >
              <div className="font-medium">{preset.name}</div>
              <div className="text-xs text-surface-400 font-mono">{preset.expression}</div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Scheduled Jobs List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="rounded-2xl glass p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Scheduled Jobs</h2>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['scheduled-jobs'] })}
            className="p-2 rounded-lg hover:bg-surface-800 transition-colors"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>

        {jobsLoading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin text-surface-400" />
          </div>
        ) : jobs?.length > 0 ? (
          <div className="space-y-4">
            {jobs.map((job: any) => (
              <ScheduledJobCard
                key={job.id}
                job={job}
                onPause={() => pauseJob.mutate(job.id)}
                onResume={() => resumeJob.mutate(job.id)}
                onDelete={() => {
                  if (confirm('Are you sure you want to delete this scheduled job?')) {
                    deleteJob.mutate(job.id)
                  }
                }}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Calendar className="w-12 h-12 mx-auto mb-4 text-surface-500" />
            <h3 className="text-lg font-medium mb-2">No Scheduled Jobs</h3>
            <p className="text-surface-400 mb-4">Create your first scheduled scraping job</p>
            <Link
              href="/dashboard/scheduler/new"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 text-white hover:bg-brand-600 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create Schedule
            </Link>
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
  small = false,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  color: 'brand' | 'blue' | 'green' | 'purple' | 'red'
  small?: boolean
}) {
  const colors = {
    brand: 'bg-brand-500/10 text-brand-400',
    blue: 'bg-blue-500/10 text-blue-400',
    green: 'bg-green-500/10 text-green-400',
    purple: 'bg-purple-500/10 text-purple-400',
    red: 'bg-red-500/10 text-red-400',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl glass p-6"
    >
      <div className={`w-12 h-12 rounded-xl ${colors[color]} flex items-center justify-center mb-4`}>
        {icon}
      </div>
      <p className="text-surface-400 text-sm mb-1">{label}</p>
      <p className={`font-bold ${small ? 'text-lg' : 'text-2xl'}`}>{value}</p>
    </motion.div>
  )
}

function ScheduledJobCard({
  job,
  onPause,
  onResume,
  onDelete,
}: {
  job: any
  onPause: () => void
  onResume: () => void
  onDelete: () => void
}) {
  const scheduleTypeLabels: Record<string, string> = {
    cron: 'Cron',
    interval: 'Interval',
    once: 'One-time',
    on_change: 'On Change',
    conditional: 'Conditional',
  }

  return (
    <div className="p-4 rounded-xl bg-surface-800/50 hover:bg-surface-800 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            job.is_active 
              ? 'bg-green-500/10 text-green-400' 
              : 'bg-surface-700 text-surface-400'
          }`}>
            {job.is_active ? (
              <Play className="w-5 h-5" />
            ) : (
              <Pause className="w-5 h-5" />
            )}
          </div>
          <div>
            <h3 className="font-medium">{job.name}</h3>
            <div className="flex items-center gap-3 text-sm text-surface-400">
              <span className="flex items-center gap-1">
                <Timer className="w-4 h-4" />
                {scheduleTypeLabels[job.schedule_type] || job.schedule_type}
              </span>
              <span>•</span>
              <span>{job.run_count} runs</span>
              {job.last_run && (
                <>
                  <span>•</span>
                  <span>Last: {formatDate(job.last_run)}</span>
                </>
              )}
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {job.next_run && (
            <div className="text-sm text-surface-400 mr-4">
              Next: {formatDate(job.next_run)}
            </div>
          )}
          
          {job.last_error && (
            <div className="p-2 rounded-lg bg-red-500/10 text-red-400" title={job.last_error}>
              <AlertTriangle className="w-4 h-4" />
            </div>
          )}
          
          {job.is_active ? (
            <button
              onClick={onPause}
              className="p-2 rounded-lg hover:bg-surface-700 transition-colors text-yellow-400"
              title="Pause"
            >
              <Pause className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={onResume}
              className="p-2 rounded-lg hover:bg-surface-700 transition-colors text-green-400"
              title="Resume"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          
          <Link
            href={`/dashboard/scheduler/${job.id}`}
            className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
            title="View Details"
          >
            <Settings className="w-4 h-4" />
          </Link>
          
          <button
            onClick={onDelete}
            className="p-2 rounded-lg hover:bg-red-500/10 text-red-400 transition-colors"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}


'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { projectsApi, jobsApi, dataApi } from '@/lib/api'
import { formatNumber, formatDate, getStatusColor, getDataTypeIcon } from '@/lib/utils'
import { motion } from 'framer-motion'
import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import {
  ArrowLeft,
  Plus,
  PlayCircle,
  Database,
  Download,
  Settings,
  Loader2,
  BarChart3,
  TrendingUp,
  FileText,
  Image as ImageIcon,
  Music,
  Video,
  Package,
  Tag,
  Zap,
} from 'lucide-react'

const dataTypeIcons: Record<string, any> = {
  text: FileText,
  image: ImageIcon,
  audio: Music,
  video: Video,
  mixed: Package,
}

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const { id } = params
  const queryClient = useQueryClient()

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id),
  })

  const { data: stats } = useQuery({
    queryKey: ['project-stats', id],
    queryFn: () => projectsApi.getStats(id),
    enabled: !!project,
  })

  const { data: jobs } = useQuery({
    queryKey: ['project-jobs', id],
    queryFn: () => jobsApi.list({ project_id: id, limit: 5 }),
    enabled: !!project,
  })

  const { data: dataItems } = useQuery({
    queryKey: ['project-data', id],
    queryFn: () => dataApi.list(id, { limit: 10 }),
    enabled: !!project,
  })

  if (projectLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="p-8">
        <Link
          href="/dashboard/projects"
          className="inline-flex items-center gap-2 text-surface-400 hover:text-white mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Projects
        </Link>
        <p className="text-surface-400">Project not found</p>
      </div>
    )
  }

  const TypeIcon = dataTypeIcons[project.data_type] || Package

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/dashboard/projects"
          className="inline-flex items-center gap-2 text-surface-400 hover:text-white mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Projects
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/10 flex items-center justify-center">
              <TypeIcon className="w-8 h-8 text-brand-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">{project.name}</h1>
              <p className="text-surface-400">
                {project.description || 'No description'}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-1 rounded-lg text-xs bg-surface-700 capitalize">
                  {project.data_type}
                </span>
                {project.is_active ? (
                  <span className="px-2 py-1 rounded-lg text-xs bg-green-500/10 text-green-400">
                    Active
                  </span>
                ) : (
                  <span className="px-2 py-1 rounded-lg text-xs bg-surface-700 text-surface-400">
                    Inactive
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <Link
              href={`/dashboard/jobs/new?project=${id}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 text-white font-medium hover:bg-brand-600 transition-colors"
            >
              <Zap className="w-4 h-4" />
              New Job
            </Link>
            <Link
              href={`/dashboard/data?project=${id}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors"
            >
              <Database className="w-4 h-4" />
              Browse Data
            </Link>
            <Link
              href={`/dashboard/exports/new?project=${id}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors"
            >
              <Download className="w-4 h-4" />
              Export
            </Link>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={<PlayCircle className="w-5 h-5" />}
          label="Total Jobs"
          value={formatNumber(stats?.total_jobs || jobs?.length || 0)}
          color="bg-blue-500/10 text-blue-400"
        />
        <StatCard
          icon={<TrendingUp className="w-5 h-5" />}
          label="Active Jobs"
          value={formatNumber(stats?.active_jobs || jobs?.filter((j: any) => j.status === 'running').length || 0)}
          color="bg-yellow-500/10 text-yellow-400"
        />
        <StatCard
          icon={<Database className="w-5 h-5" />}
          label="Data Items"
          value={formatNumber(stats?.total_data_items || project.data_count || 0)}
          color="bg-purple-500/10 text-purple-400"
        />
        <StatCard
          icon={<Tag className="w-5 h-5" />}
          label="Labeled"
          value={formatNumber(stats?.labeled_items || 0)}
          color="bg-green-500/10 text-green-400"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Recent Jobs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl glass p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Jobs</h2>
            <Link
              href={`/dashboard/jobs?project=${id}`}
              className="text-sm text-brand-400 hover:text-brand-300"
            >
              View all
            </Link>
          </div>

          {jobs?.length > 0 ? (
            <div className="space-y-3">
              {jobs.map((job: any) => (
                <Link
                  key={job.id}
                  href={`/dashboard/jobs/${job.id}`}
                  className="block p-3 rounded-xl bg-surface-800/50 hover:bg-surface-800 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{job.name}</p>
                      <p className="text-sm text-surface-400">
                        {job.provider} • {formatNumber(job.items_collected || 0)} collected
                      </p>
                    </div>
                    <span className={`px-2 py-1 rounded-lg text-xs ${getStatusColor(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <PlayCircle className="w-10 h-10 text-surface-600 mx-auto mb-2" />
              <p className="text-surface-400">No jobs yet</p>
              <Link
                href={`/dashboard/jobs/new?project=${id}`}
                className="text-sm text-brand-400 hover:text-brand-300 mt-1 inline-block"
              >
                Create your first job
              </Link>
            </div>
          )}
        </motion.div>

        {/* Recent Data */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl glass p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Data</h2>
            <Link
              href={`/dashboard/data?project=${id}`}
              className="text-sm text-brand-400 hover:text-brand-300"
            >
              View all
            </Link>
          </div>

          {dataItems?.length > 0 ? (
            <div className="space-y-3">
              {dataItems.map((item: any) => (
                <div
                  key={item.id}
                  className="p-3 rounded-xl bg-surface-800/50"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{getDataTypeIcon(item.data_type)}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">
                        {item.content?.slice(0, 50) || item.source_url || 'No content'}
                      </p>
                      <p className="text-sm text-surface-400">
                        {item.data_type} • {formatDate(item.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {item.is_labeled && (
                        <span className="px-2 py-1 rounded-lg text-xs bg-green-500/10 text-green-400">
                          Labeled
                        </span>
                      )}
                      {item.is_processed && (
                        <span className="px-2 py-1 rounded-lg text-xs bg-blue-500/10 text-blue-400">
                          Processed
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Database className="w-10 h-10 text-surface-600 mx-auto mb-2" />
              <p className="text-surface-400">No data collected yet</p>
              <p className="text-sm text-surface-500 mt-1">Run a job to start collecting data</p>
            </div>
          )}
        </motion.div>
      </div>

      {/* Project Settings */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="mt-8 rounded-2xl glass p-6"
      >
        <div className="flex items-center gap-3 mb-4">
          <Settings className="w-5 h-5 text-surface-400" />
          <h2 className="text-lg font-semibold">Project Information</h2>
        </div>
        
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-surface-400 mb-1">Project ID</h3>
            <p className="font-mono text-sm">{project.id}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-surface-400 mb-1">Created</h3>
            <p>{formatDate(project.created_at)}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-surface-400 mb-1">Last Updated</h3>
            <p>{formatDate(project.updated_at)}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-surface-400 mb-1">Data Type</h3>
            <p className="capitalize">{project.data_type}</p>
          </div>
          {project.settings && Object.keys(project.settings).length > 0 && (
            <div className="md:col-span-2">
              <h3 className="text-sm font-medium text-surface-400 mb-1">Settings</h3>
              <pre className="text-xs bg-surface-800 p-3 rounded-lg overflow-x-auto">
                {JSON.stringify(project.settings, null, 2)}
              </pre>
            </div>
          )}
        </div>
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
      <p className="text-2xl font-bold">{value}</p>
    </div>
  )
}

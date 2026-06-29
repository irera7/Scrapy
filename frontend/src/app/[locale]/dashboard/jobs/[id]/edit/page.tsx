'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { useRouter, Link } from '@/i18n/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobsApi, projectsApi, providersApi } from '@/lib/api'
import { motion } from 'framer-motion'
import { ArrowLeft, Loader2, Info, AlertCircle } from 'lucide-react'
import { useTranslations } from 'next-intl'
import toast from 'react-hot-toast'

export default function EditJobPage() {
  const router = useRouter()
  const params = useParams()
  const jobId = params.id as string
  const queryClient = useQueryClient()

  const [projectId, setProjectId] = useState('')
  const [name, setName] = useState('')
  const [provider, setProvider] = useState('')
  const [config, setConfig] = useState<Record<string, any>>({})
  const [schedule, setSchedule] = useState('')
  const [isLoaded, setIsLoaded] = useState(false)

  // Fetch existing job
  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.get(jobId),
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: () => providersApi.list(),
  })

  // Load job data into form
  useEffect(() => {
    if (job && !isLoaded) {
      setProjectId(job.project_id)
      setName(job.name)
      setProvider(job.provider)
      setConfig(job.config || {})
      setSchedule(job.schedule || '')
      setIsLoaded(true)
    }
  }, [job, isLoaded])

  const updateMutation = useMutation({
    mutationFn: (data: any) => jobsApi.update(jobId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['job', jobId] })
      toast.success('Job updated!')
      router.push(`/dashboard/jobs/${jobId}`)
    },
    onError: () => {
      toast.error('Failed to update job')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate({
      project_id: projectId,
      name,
      provider,
      config,
      schedule: schedule || undefined,
    })
  }

  const renderConfigFields = () => {
    // Add a toggle for download_media for all providers
    const commonFields = (
      <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
        <div className="flex items-start gap-2 mb-3">
          <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-yellow-400">Media Download Settings</h4>
            <p className="text-sm text-yellow-300/80 mt-1">
              Enable this to download actual media files (images, audio, video) to storage.
              Without this, only metadata and source URLs are saved.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-3">
          <input
            type="checkbox"
            id="download_media"
            checked={config.download_media || false}
            onChange={(e) => setConfig({ ...config, download_media: e.target.checked })}
            className="rounded border-surface-700 bg-surface-800"
          />
          <label htmlFor="download_media" className="text-sm font-medium">
            Download media files to storage (enables preview/download in Data Browser)
          </label>
        </div>
      </div>
    )

    switch (provider) {
      case 'image_scraper':
      case 'audio_scraper':
      case 'video_scraper':
      case 'wikimedia':
        return (
          <>
            {commonFields}
            <div className="mt-4">
              <label className="block text-sm font-medium mb-2">Search Query *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="Search query"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Results</label>
              <input
                type="number"
                value={config.max_results || 50}
                onChange={(e) => setConfig({ ...config, max_results: parseInt(e.target.value) })}
                min={1}
                max={500}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              />
            </div>
          </>
        )

      default:
        return (
          <>
            {commonFields}
            <div className="mt-4">
              <label className="block text-sm font-medium mb-2">Configuration (JSON)</label>
              <textarea
                value={JSON.stringify(config, null, 2)}
                onChange={(e) => {
                  try {
                    setConfig(JSON.parse(e.target.value))
                  } catch (err) {
                    // Keep typing, don't update until valid JSON
                  }
                }}
                rows={10}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                placeholder='{"key": "value"}'
              />
              <p className="text-xs text-surface-500 mt-1">
                Edit the job configuration as JSON. Make sure it's valid JSON before saving.
              </p>
            </div>
          </>
        )
    }
  }

  if (jobLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
      </div>
    )
  }

  if (!job) {
    return (
      <div className="p-8">
        <div className="text-center py-20">
          <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold mb-2">Job Not Found</h2>
          <p className="text-surface-400 mb-6">The job you're looking for doesn't exist.</p>
          <Link
            href="/dashboard/jobs"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500 text-white hover:bg-brand-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Jobs
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-2xl">
      <Link
        href={`/dashboard/jobs/${jobId}`}
        className="inline-flex items-center gap-2 text-surface-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Job Details
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold mb-2">Edit Job</h1>
        <p className="text-surface-400 mb-8">Update job configuration</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Project Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Project *</label>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
            >
              <option value="">Select a project</option>
              {projects?.map((project: any) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          {/* Job Name */}
          <div>
            <label className="block text-sm font-medium mb-2">Job Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              placeholder="Daily news scrape"
            />
          </div>

          {/* Provider (Read-only) */}
          <div>
            <label className="block text-sm font-medium mb-2">Provider</label>
            <input
              type="text"
              value={provider}
              disabled
              className="w-full px-4 py-3 rounded-xl bg-surface-700 border border-surface-600 text-surface-400 cursor-not-allowed"
            />
            <p className="text-xs text-surface-500 mt-1">
              Provider cannot be changed after creation
            </p>
          </div>

          {/* Provider-specific config */}
          <div className="space-y-4 p-4 rounded-xl bg-surface-800/50 border border-surface-700">
            <h3 className="font-medium">Configuration</h3>
            {renderConfigFields()}
          </div>

          {/* Schedule */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Schedule (optional)
              <span className="text-surface-400 font-normal ml-2">cron expression</span>
            </label>
            <input
              type="text"
              value={schedule}
              onChange={(e) => setSchedule(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono"
              placeholder="0 */6 * * * (every 6 hours)"
            />
            <p className="text-xs text-surface-500 mt-1">
              Leave empty for manual runs only
            </p>
          </div>

          {/* Submit */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={updateMutation.isPending || !projectId || !name}
              className="flex-1 py-3 px-4 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </button>
            <Link
              href={`/dashboard/jobs/${jobId}`}
              className="px-6 py-3 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors"
            >
              Cancel
            </Link>
          </div>
        </form>
      </motion.div>
    </div>
  )
}


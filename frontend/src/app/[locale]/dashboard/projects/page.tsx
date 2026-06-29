'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi } from '@/lib/api'
import { formatNumber, formatDate, getDataTypeIcon } from '@/lib/utils'
import { motion } from 'framer-motion'
import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import {
  Plus,
  Search,
  Trash2,
  Loader2,
  FolderKanban,
  FileText,
  Image as ImageIcon,
  Music,
  Video,
  Package,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const projectsTutorial: TutorialSection[] = [
  {
    title: 'What are Projects?',
    content: 'Projects are containers that organize your collected data by topic, source, or purpose. Each project can hold multiple types of data (text, images, audio, video) and have multiple scraping jobs associated with it.',
    tips: [
      'Create separate projects for different ML tasks (e.g., "Sentiment Analysis", "Image Classification")',
      'Use descriptive names to easily identify project contents later',
    ],
  },
  {
    title: 'Creating a Project',
    content: 'Click the "New Project" button to create a new project. You\'ll need to provide a name, optional description, and select the primary data type.',
    steps: [
      { title: 'Name Your Project', description: 'Choose a descriptive name that reflects the data content' },
      { title: 'Add Description', description: 'Describe the project purpose and data sources' },
      { title: 'Select Data Type', description: 'Choose text, image, audio, video, or mixed' },
      { title: 'Create & Start', description: 'Your project is ready for data collection' },
    ],
  },
  {
    title: 'Managing Projects',
    content: 'Click on any project card to view its details, including collected data, associated jobs, and statistics. You can search projects using the search bar above.',
    tips: [
      'The data count shows total items collected across all jobs',
      'Hover over a project to reveal the delete button',
      'Projects can be filtered by data type using the search',
    ],
    warning: 'Deleting a project will also delete all associated jobs and collected data. This action cannot be undone.',
  },
  {
    title: 'Project Data Types',
    content: 'Each project has a primary data type that determines how data is processed and exported.',
    steps: [
      { title: 'Text', description: 'Articles, comments, reviews, social media posts' },
      { title: 'Image', description: 'Photos, screenshots, diagrams, artwork' },
      { title: 'Audio', description: 'Podcasts, music, voice recordings' },
      { title: 'Video', description: 'Video clips, streams, tutorials' },
      { title: 'Mixed', description: 'Multi-modal data with various types' },
    ],
  },
]

const dataTypeIcons: Record<string, any> = {
  text: FileText,
  image: ImageIcon,
  audio: Music,
  video: Video,
  mixed: Package,
}

export default function ProjectsPage() {
  const t = useTranslations()
  const [searchQuery, setSearchQuery] = useState('')
  const queryClient = useQueryClient()

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const deleteMutation = useMutation({
    mutationFn: projectsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Project deleted')
    },
    onError: () => {
      toast.error('Failed to delete project')
    },
  })

  const filteredProjects = projects?.filter((project: any) =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const stats = {
    total: projects?.length || 0,
    totalData: projects?.reduce((acc: number, p: any) => acc + (p.data_count || 0), 0) || 0,
    totalJobs: projects?.reduce((acc: number, p: any) => acc + (p.job_count || 0), 0) || 0,
  }

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Projects Guide"
        description="Learn how to create and manage data collection projects"
        sections={projectsTutorial}
        storageKey="projects"
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">{t('projects.title')}</h1>
          <p className="text-surface-400">{t('projects.description') || 'Manage your data collection projects'}</p>
        </div>
        <Link
          href="/dashboard/projects/new"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors"
        >
          <Plus className="w-5 h-5" />
          {t('projects.newProject')}
        </Link>
      </div>

      {/* Stats */}
      {projects?.length > 0 && (
        <div className="flex gap-4 mb-6">
          <div className="px-4 py-2 rounded-xl bg-surface-800/50 border border-surface-700">
            <span className="text-surface-400 text-sm">Projects: </span>
            <span className="font-medium">{stats.total}</span>
          </div>
          <div className="px-4 py-2 rounded-xl bg-brand-500/10 border border-brand-500/20">
            <span className="text-brand-400 text-sm">Total Data: </span>
            <span className="font-medium text-brand-400">{formatNumber(stats.totalData)}</span>
          </div>
          <div className="px-4 py-2 rounded-xl bg-blue-500/10 border border-blue-500/20">
            <span className="text-blue-400 text-sm">Total Jobs: </span>
            <span className="font-medium text-blue-400">{formatNumber(stats.totalJobs)}</span>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute start-4 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t('common.search') + '...'}
          className="w-full ps-12 pe-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
        />
      </div>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
        </div>
      ) : filteredProjects?.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project: any, index: number) => {
            const TypeIcon = dataTypeIcons[project.data_type] || Package
            
            return (
              <motion.div
                key={project.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="rounded-2xl glass p-6 card-hover group relative"
              >
                <Link href={`/dashboard/projects/${project.id}`} className="block">
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center">
                      <TypeIcon className="w-6 h-6 text-brand-400" />
                    </div>
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        if (confirm('Delete this project? This will also delete all associated jobs and data.')) {
                          deleteMutation.mutate(project.id)
                        }
                      }}
                      className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-red-400 transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <h3 className="text-lg font-semibold mb-2 group-hover:text-brand-400 transition-colors">
                    {project.name}
                  </h3>
                  <p className="text-sm text-surface-400 mb-4 line-clamp-2">
                    {project.description || 'No description'}
                  </p>

                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4">
                      <span className="text-surface-400">
                        {formatNumber(project.data_count || 0)} items
                      </span>
                      <span className="text-surface-400">
                        {project.job_count || 0} jobs
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-surface-800">
                    <span className="px-2 py-1 rounded-lg text-xs bg-surface-700 capitalize">
                      {project.data_type}
                    </span>
                    <span className="text-surface-500 text-xs">
                      {formatDate(project.updated_at)}
                    </span>
                  </div>
                </Link>
              </motion.div>
            )
          })}
        </div>
      ) : searchQuery ? (
        <div className="text-center py-20">
          <Search className="w-16 h-16 text-surface-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">{t('common.noResults')}</h3>
          <p className="text-surface-400">
            {searchQuery}
          </p>
        </div>
      ) : (
        <div className="text-center py-20">
          <div className="w-20 h-20 rounded-full bg-surface-800 flex items-center justify-center mx-auto mb-4">
            <FolderKanban className="w-10 h-10 text-surface-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">{t('projects.noProjects')}</h3>
          <p className="text-surface-400 mb-6">
            {t('projects.createFirst')}
          </p>
          <Link
            href="/dashboard/projects/new"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors"
          >
            <Plus className="w-5 h-5" />
            {t('projects.newProject')}
          </Link>
        </div>
      )}
    </div>
  )
}

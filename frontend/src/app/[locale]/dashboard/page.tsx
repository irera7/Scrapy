'use client'

import { useQuery } from '@tanstack/react-query'
import { projectsApi, jobsApi, exportsApi } from '@/lib/api'
import { formatNumber, getStatusColor, formatDate } from '@/lib/utils'
import { motion } from 'framer-motion'
import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import {
  FolderKanban,
  PlayCircle,
  Database,
  Plus,
  ArrowRight,
  Loader2,
  Download,
  CheckCircle,
  AlertTriangle,
  Clock,
  Activity,
  Zap,
  FileText,
  Image as ImageIcon,
  Music,
  Video,
  BarChart3,
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  Wand2,
  Rocket,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

export default function DashboardPage() {
  const t = useTranslations()
  
  const dashboardTutorial: TutorialSection[] = [
    {
      title: 'Welcome to AI Data Collector',
      content: 'This is your command center for web scraping and ML dataset management.',
      tips: [
        'Check the Dashboard regularly to monitor job status',
        'Click on any stat card to navigate to its detail page',
        'Use the ML Wizard banner for guided dataset creation',
      ],
    },
    {
      title: 'Understanding the Stats',
      content: 'The top section shows key metrics: total projects, active jobs, collected data items, and exports.',
      steps: [
        { title: t('nav.projects'), description: 'Containers that organize your scraped data' },
        { title: t('nav.jobs'), description: 'Individual scraping tasks that collect data' },
        { title: t('dashboard.stats.dataItems'), description: 'Individual pieces of content' },
        { title: t('nav.exports'), description: 'Processed datasets ready for ML training' },
      ],
    },
  ]
  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list({ limit: 5 }),
  })

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.list({ limit: 10 }),
    refetchInterval: 5000,
  })

  const { data: exports } = useQuery({
    queryKey: ['exports'],
    queryFn: () => exportsApi.list({ limit: 5 }),
  })

  const totalProjects = projects?.length || 0
  const totalJobs = jobs?.length || 0
  const runningJobs = jobs?.filter((j: any) => j.status === 'running').length || 0
  const failedJobs = jobs?.filter((j: any) => j.status === 'failed').length || 0
  const completedJobs = jobs?.filter((j: any) => j.status === 'completed').length || 0
  const totalData = projects?.reduce((acc: number, p: any) => acc + (p.data_count || 0), 0) || 0
  const totalExports = exports?.filter((e: any) => e.status === 'completed').length || 0

  const dataTypeStats = {
    text: projects?.reduce((acc: number, p: any) => acc + (p.text_count || 0), 0) || 0,
    image: projects?.reduce((acc: number, p: any) => acc + (p.image_count || 0), 0) || 0,
    audio: projects?.reduce((acc: number, p: any) => acc + (p.audio_count || 0), 0) || 0,
    video: projects?.reduce((acc: number, p: any) => acc + (p.video_count || 0), 0) || 0,
  }

  const totalJobsWithStatus = completedJobs + failedJobs
  const successRate = totalJobsWithStatus > 0 
    ? Math.round((completedJobs / totalJobsWithStatus) * 100) 
    : 100

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Dashboard Overview"
        description="Learn how to navigate and use the main dashboard"
        sections={dashboardTutorial}
        storageKey="dashboard"
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <motion.h1 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl font-bold mb-2"
          >
            {t('dashboard.title')}
          </motion.h1>
          <p className="text-surface-400">{t('dashboard.overview')}</p>
        </div>
        <Link
          href="/dashboard/projects/new"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors"
        >
          <Plus className="w-5 h-5" />
          {t('projects.newProject')}
        </Link>
      </div>

      {/* ML Wizard Banner */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <Link
          href="/dashboard/wizard"
          className="block p-6 rounded-2xl bg-gradient-to-r from-brand-500/10 via-purple-500/10 to-cyan-500/10 border border-brand-500/20 hover:border-brand-500/40 transition-all group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/20 group-hover:scale-110 transition-transform">
                <Wand2 className="w-7 h-7 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold flex items-center gap-2">
                  {t('nav.mlWizard')}
                  <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400">New</span>
                </h3>
                <p className="text-surface-400">
                  {t('nav.datasetPrepGuide')}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 text-brand-400">
              <span className="hidden sm:block">{t('home.getStarted')}</span>
              <Rocket className="w-5 h-5 group-hover:translate-x-1 rtl:group-hover:-translate-x-1 transition-transform" />
            </div>
          </div>
        </Link>
      </motion.div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={<FolderKanban className="w-6 h-6" />}
          label={t('nav.projects')}
          value={formatNumber(totalProjects)}
          color="brand"
          href="/dashboard/projects"
        />
        <StatCard
          icon={<PlayCircle className="w-6 h-6" />}
          label={t('nav.jobs')}
          value={formatNumber(totalJobs)}
          subValue={runningJobs > 0 ? `${runningJobs} ${t('notifications.running')}` : undefined}
          subColor={runningJobs > 0 ? 'text-yellow-400' : undefined}
          color="blue"
          href="/dashboard/jobs"
        />
        <StatCard
          icon={<Database className="w-6 h-6" />}
          label={t('dashboard.stats.dataItems')}
          value={formatNumber(totalData)}
          color="purple"
          href="/dashboard/data"
        />
        <StatCard
          icon={<Download className="w-6 h-6" />}
          label={t('nav.exports')}
          value={formatNumber(totalExports)}
          color="cyan"
          href="/dashboard/exports"
        />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Success Rate */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl glass p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-surface-400 text-sm font-medium">{t('jobs.status')}</h3>
            <Activity className="w-5 h-5 text-surface-500" />
          </div>
          <div className="flex items-end gap-4">
            <span className="text-4xl font-bold">{successRate}%</span>
            <div className={`flex items-center gap-1 text-sm ${successRate >= 80 ? 'text-green-400' : 'text-red-400'}`}>
              {successRate >= 80 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
              <span>{completedJobs} / {totalJobsWithStatus}</span>
            </div>
          </div>
          <div className="mt-4 h-2 bg-surface-800 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-500 ${successRate >= 80 ? 'bg-green-500' : successRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${successRate}%` }}
            />
          </div>
        </motion.div>

        {/* Job Status Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="rounded-2xl glass p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-surface-400 text-sm font-medium">{t('jobs.status')}</h3>
            <PieChart className="w-5 h-5 text-surface-500" />
          </div>
          <div className="space-y-3">
            <StatusBar label={t('notifications.completed')} count={completedJobs} total={totalJobs} color="bg-green-500" />
            <StatusBar label={t('notifications.running')} count={runningJobs} total={totalJobs} color="bg-yellow-500" />
            <StatusBar label={t('notifications.failed')} count={failedJobs} total={totalJobs} color="bg-red-500" />
          </div>
        </motion.div>

        {/* Data Type Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl glass p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-surface-400 text-sm font-medium">{t('nav.data')}</h3>
            <BarChart3 className="w-5 h-5 text-surface-500" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <DataTypeCard icon={<FileText className="w-4 h-4" />} label="Text" count={dataTypeStats.text} color="text-yellow-400" />
            <DataTypeCard icon={<ImageIcon className="w-4 h-4" />} label="Image" count={dataTypeStats.image} color="text-pink-400" />
            <DataTypeCard icon={<Music className="w-4 h-4" />} label="Audio" count={dataTypeStats.audio} color="text-blue-400" />
            <DataTypeCard icon={<Video className="w-4 h-4" />} label="Video" count={dataTypeStats.video} color="text-purple-400" />
          </div>
        </motion.div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Recent Projects */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="rounded-2xl glass p-6"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">{t('dashboard.recentActivity')}</h2>
            <Link
              href="/dashboard/projects"
              className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
            >
              {t('common.next')} <ArrowRight className="w-4 h-4 rtl:rotate-180" />
            </Link>
          </div>

          {projectsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
            </div>
          ) : projects?.length > 0 ? (
            <div className="space-y-3">
              {projects.map((project: any) => (
                <Link
                  key={project.id}
                  href={`/dashboard/projects/${project.id}`}
                  className="block p-4 rounded-xl bg-surface-800/50 hover:bg-surface-800 transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-brand-500/10 flex items-center justify-center">
                        <FolderKanban className="w-5 h-5 text-brand-400" />
                      </div>
                      <div>
                        <h3 className="font-medium group-hover:text-brand-400 transition-colors">{project.name}</h3>
                        <p className="text-sm text-surface-400">
                          {project.data_type} • {formatNumber(project.data_count || 0)} items
                        </p>
                      </div>
                    </div>
                    <span className="text-xs text-surface-500">
                      {formatDate(project.updated_at)}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-surface-400">
              <p>{t('projects.noProjects')}</p>
              <Link href="/dashboard/projects/new" className="text-brand-400 hover:text-brand-300">
                {t('projects.createFirst')}
              </Link>
            </div>
          )}
        </motion.div>

        {/* Recent Jobs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="rounded-2xl glass p-6"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">{t('nav.jobs')}</h2>
            <Link
              href="/dashboard/jobs"
              className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
            >
              {t('common.next')} <ArrowRight className="w-4 h-4 rtl:rotate-180" />
            </Link>
          </div>

          {jobsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
            </div>
          ) : jobs?.length > 0 ? (
            <div className="space-y-3">
              {jobs.slice(0, 5).map((job: any) => (
                <Link
                  key={job.id}
                  href={`/dashboard/jobs/${job.id}`}
                  className="block p-4 rounded-xl bg-surface-800/50 hover:bg-surface-800 transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        job.status === 'completed' ? 'bg-green-500/10' :
                        job.status === 'running' ? 'bg-yellow-500/10' :
                        job.status === 'failed' ? 'bg-red-500/10' :
                        'bg-surface-700'
                      }`}>
                        {job.status === 'completed' && <CheckCircle className="w-5 h-5 text-green-400" />}
                        {job.status === 'running' && <Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />}
                        {job.status === 'failed' && <AlertTriangle className="w-5 h-5 text-red-400" />}
                        {!['completed', 'running', 'failed'].includes(job.status) && <Clock className="w-5 h-5 text-surface-400" />}
                      </div>
                      <div>
                        <h3 className="font-medium group-hover:text-brand-400 transition-colors">{job.name}</h3>
                        <p className="text-sm text-surface-400">
                          {job.provider} • {formatNumber(job.items_collected || 0)} collected
                        </p>
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded-lg text-xs ${getStatusColor(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-surface-400">
              <p>{t('jobs.noJobs')}</p>
              <Link href="/dashboard/jobs/new" className="text-brand-400 hover:text-brand-300">
                {t('jobs.createFirst')}
              </Link>
            </div>
          )}
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="mt-8 rounded-2xl glass p-6"
      >
        <h2 className="text-xl font-semibold mb-4">{t('dashboard.quickActions')}</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <QuickAction 
            href="/dashboard/wizard" 
            icon={<Wand2 className="w-5 h-5" />} 
            label={t('nav.mlWizard')}
            color="bg-gradient-to-r from-brand-500/20 to-purple-500/20 text-brand-400 hover:from-brand-500/30 hover:to-purple-500/30 border border-brand-500/20"
          />
          <QuickAction 
            href="/dashboard/projects/new" 
            icon={<Plus className="w-5 h-5" />} 
            label={t('projects.newProject')}
            color="bg-brand-500/10 text-brand-400 hover:bg-brand-500/20"
          />
          <QuickAction 
            href="/dashboard/jobs/new" 
            icon={<Zap className="w-5 h-5" />} 
            label={t('jobs.newJob')}
            color="bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20"
          />
          <QuickAction 
            href="/dashboard/exports/new" 
            icon={<Download className="w-5 h-5" />} 
            label={t('exports.newExport')}
            color="bg-purple-500/10 text-purple-400 hover:bg-purple-500/20"
          />
          <QuickAction 
            href="/dashboard/providers" 
            icon={<Activity className="w-5 h-5" />} 
            label={t('nav.apiKeys')}
            color="bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20"
          />
        </div>
      </motion.div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  subValue,
  subColor,
  color,
  href,
}: {
  icon: React.ReactNode
  label: string
  value: string
  subValue?: string
  subColor?: string
  color: 'brand' | 'blue' | 'yellow' | 'purple' | 'cyan'
  href: string
}) {
  const colors = {
    brand: 'bg-brand-500/10 text-brand-400',
    blue: 'bg-blue-500/10 text-blue-400',
    yellow: 'bg-yellow-500/10 text-yellow-400',
    purple: 'bg-purple-500/10 text-purple-400',
    cyan: 'bg-cyan-500/10 text-cyan-400',
  }

  return (
    <Link href={href}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl glass p-6 card-hover cursor-pointer group"
      >
        <div className={`w-12 h-12 rounded-xl ${colors[color]} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
          {icon}
        </div>
        <p className="text-surface-400 text-sm mb-1">{label}</p>
        <p className="text-3xl font-bold">{value}</p>
        {subValue && (
          <p className={`text-xs mt-1 ${subColor || 'text-surface-500'}`}>{subValue}</p>
        )}
      </motion.div>
    </Link>
  )
}

function StatusBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const percentage = total > 0 ? (count / total) * 100 : 0
  
  return (
    <div className="flex items-center gap-3">
      <div className="w-20 text-sm text-surface-400">{label}</div>
      <div className="flex-1 h-2 bg-surface-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${percentage}%` }} />
      </div>
      <div className="w-12 text-sm text-right">{count}</div>
    </div>
  )
}

function DataTypeCard({ icon, label, count, color }: { icon: React.ReactNode; label: string; count: number; color: string }) {
  return (
    <div className="p-3 rounded-xl bg-surface-800/50 flex items-center gap-2">
      <span className={color}>{icon}</span>
      <div>
        <p className="text-xs text-surface-400">{label}</p>
        <p className="font-semibold">{formatNumber(count)}</p>
      </div>
    </div>
  )
}

function QuickAction({ href, icon, label, color }: { href: string; icon: React.ReactNode; label: string; color: string }) {
  return (
    <Link 
      href={href}
      className={`flex items-center gap-3 p-4 rounded-xl transition-colors ${color}`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </Link>
  )
}

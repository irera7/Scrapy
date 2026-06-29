'use client'

import { useEffect, useState } from 'react'
import { useRouter, Link } from '@/i18n/navigation'
import { usePathname } from '@/i18n/navigation'
import { useAuth } from '@/hooks/useAuth'
import { useQuery } from '@tanstack/react-query'
import { jobsApi } from '@/lib/api'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslations, useLocale } from 'next-intl'
import { isRtlLocale, type Locale } from '@/i18n/config'
import { LanguageSwitcher } from '@/components/ui/language-switcher'
import {
  LayoutDashboard,
  FolderKanban,
  PlayCircle,
  Database,
  Download,
  Settings,
  LogOut,
  Loader2,
  Key,
  Menu,
  X,
  Bell,
  ChevronDown,
  Activity,
  CheckCircle,
  AlertTriangle,
  Zap,
  Clock,
  BarChart3,
  Server,
  Sparkles,
  ShieldCheck,
  Wand2,
  Rocket,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, isLoading, isAuthenticated, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const t = useTranslations()
  const locale = useLocale() as Locale
  const isRtl = isRtlLocale(locale)

  const navItems = [
    { href: '/dashboard', label: t('nav.dashboard'), icon: LayoutDashboard },
    { href: '/dashboard/projects', label: t('nav.projects'), icon: FolderKanban },
    { href: '/dashboard/jobs', label: t('nav.jobs'), icon: PlayCircle },
    { href: '/dashboard/scheduler', label: t('nav.scheduler'), icon: Clock },
    { href: '/dashboard/data', label: t('nav.data'), icon: Database },
    { href: '/dashboard/processing', label: t('nav.processing'), icon: Sparkles },
    { href: '/dashboard/dataset', label: t('nav.mlDataset'), icon: BarChart3 },
    { href: '/dashboard/quality', label: t('nav.quality'), icon: ShieldCheck },
    { href: '/dashboard/exports', label: t('nav.exports'), icon: Download },
    { href: '/dashboard/workers', label: t('nav.workers'), icon: Server },
    { href: '/dashboard/providers', label: t('nav.apiKeys'), icon: Key },
    { href: '/dashboard/settings', label: t('nav.settings'), icon: Settings },
  ]

  // Fetch running jobs for notifications
  const { data: jobs } = useQuery({
    queryKey: ['jobs-status'],
    queryFn: () => jobsApi.list({ limit: 20 }),
    refetchInterval: 5000,
    enabled: isAuthenticated,
  })

  const runningJobs = jobs?.filter((j: any) => j.status === 'running') || []
  const failedJobs = jobs?.filter((j: any) => j.status === 'failed' && !j.seen) || []
  const recentCompletedJobs = jobs?.filter((j: any) => 
    j.status === 'completed' && 
    new Date(j.completed_at || j.updated_at).getTime() > Date.now() - 300000
  ) || []

  const notifications = [
    ...runningJobs.map((j: any) => ({ type: 'running', job: j })),
    ...failedJobs.map((j: any) => ({ type: 'failed', job: j })),
    ...recentCompletedJobs.map((j: any) => ({ type: 'completed', job: j })),
  ]

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/auth/login')
    }
  }, [isLoading, isAuthenticated, router])

  useEffect(() => {
    const handleClick = () => {
      setShowNotifications(false)
      setShowUserMenu(false)
    }
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-950">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-brand-500 mx-auto mb-4" />
          <p className="text-surface-400">{t('common.loading')}</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen flex bg-surface-950">
      {/* Mobile Overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside className={cn(
        "fixed lg:static inset-y-0 z-50 w-64 bg-surface-900/95 backdrop-blur-xl border-surface-800 flex flex-col transform transition-transform duration-300 lg:translate-x-0",
        isRtl ? "right-0 border-l" : "left-0 border-r",
        sidebarOpen 
          ? "translate-x-0" 
          : isRtl 
            ? "translate-x-full lg:translate-x-0" 
            : "-translate-x-full lg:translate-x-0"
      )}>
        {/* Logo */}
        <div className="p-6 border-b border-surface-800">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg">AI Data</span>
              <span className="text-xs text-surface-400 block">Collector</span>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {/* Wizard Button - Special Highlighted */}
          <Link
            href="/dashboard/wizard"
            onClick={() => setSidebarOpen(false)}
            className={cn(
              'flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all relative mb-4',
              'bg-gradient-to-r from-brand-500/20 to-purple-500/20 border border-brand-500/30',
              'hover:from-brand-500/30 hover:to-purple-500/30 hover:border-brand-500/50',
              pathname === '/dashboard/wizard'
                ? 'border-brand-500 from-brand-500/30 to-purple-500/30'
                : ''
            )}
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center">
              <Wand2 className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1">
              <span className="font-semibold text-brand-400 block text-sm">{t('nav.mlWizard')}</span>
              <span className="text-xs text-surface-400">{t('nav.datasetPrepGuide')}</span>
            </div>
            <Rocket className="w-4 h-4 text-purple-400" />
          </Link>

          <div className="h-px bg-surface-800 my-3" />

          {navItems.map((item) => {
            const isActive = pathname === item.href || 
              (item.href !== '/dashboard' && pathname.startsWith(item.href))
            
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-xl transition-all relative',
                  isActive
                    ? 'bg-brand-500/10 text-brand-400'
                    : 'text-surface-400 hover:bg-surface-800 hover:text-white'
                )}
              >
                {isActive && (
                  <motion.div 
                    layoutId="activeNav"
                    className={cn(
                      "absolute top-1/2 -translate-y-1/2 w-1 h-8 bg-brand-500",
                      isRtl ? "right-0 rounded-l-full" : "left-0 rounded-r-full"
                    )}
                  />
                )}
                <item.icon className="w-5 h-5" />
                {item.label}
                {item.href === '/dashboard/jobs' && runningJobs.length > 0 && (
                  <span className={cn(
                    "px-2 py-0.5 rounded-full text-xs bg-yellow-500/20 text-yellow-400",
                    isRtl ? "mr-auto" : "ml-auto"
                  )}>
                    {runningJobs.length}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-surface-800">
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface-800/50">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand-500 to-emerald-500 flex items-center justify-center text-white font-semibold">
              {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{user?.full_name || 'User'}</p>
              <p className="text-xs text-surface-400 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-surface-400 hover:bg-red-500/10 hover:text-red-400 transition-all mt-2"
          >
            <LogOut className="w-5 h-5" />
            {t('auth.logout')}
          </button>
        </div>
      </aside>

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 border-b border-surface-800 bg-surface-900/50 backdrop-blur-xl flex items-center justify-between px-4 lg:px-8">
          {/* Mobile Menu Button */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-xl hover:bg-surface-800 lg:hidden"
          >
            {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>

          {/* Breadcrumb / Page Title */}
          <div className="hidden lg:block">
            <h2 className="text-lg font-semibold">
              {navItems.find(item => 
                pathname === item.href || 
                (item.href !== '/dashboard' && pathname.startsWith(item.href))
              )?.label || 'Dashboard'}
            </h2>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {/* Running Jobs Indicator */}
            {runningJobs.length > 0 && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-yellow-500/10 text-yellow-400 text-sm">
                <Activity className="w-4 h-4 animate-pulse" />
                <span>{runningJobs.length} {t('notifications.running')}</span>
              </div>
            )}

            {/* Language Switcher */}
            <LanguageSwitcher />

            {/* Notifications */}
            <div className="relative" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="p-2 rounded-xl hover:bg-surface-800 relative"
              >
                <Bell className="w-5 h-5" />
                {notifications.length > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-brand-500 rounded-full" />
                )}
              </button>

              <AnimatePresence>
                {showNotifications && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className={cn(
                      "absolute mt-2 w-80 rounded-2xl bg-surface-900 border border-surface-800 shadow-xl z-50 overflow-hidden",
                      isRtl ? "left-0" : "right-0"
                    )}
                  >
                    <div className="p-4 border-b border-surface-800">
                      <h3 className="font-semibold">{t('notifications.title')}</h3>
                    </div>
                    <div className="max-h-96 overflow-y-auto">
                      {notifications.length > 0 ? (
                        notifications.map((notif, idx) => (
                          <Link
                            key={idx}
                            href={`/dashboard/jobs/${notif.job.id}`}
                            className="flex items-center gap-3 p-4 hover:bg-surface-800/50 transition-colors"
                            onClick={() => setShowNotifications(false)}
                          >
                            <div className={cn(
                              "w-10 h-10 rounded-full flex items-center justify-center",
                              notif.type === 'running' && "bg-yellow-500/10 text-yellow-400",
                              notif.type === 'completed' && "bg-green-500/10 text-green-400",
                              notif.type === 'failed' && "bg-red-500/10 text-red-400",
                            )}>
                              {notif.type === 'running' && <Loader2 className="w-5 h-5 animate-spin" />}
                              {notif.type === 'completed' && <CheckCircle className="w-5 h-5" />}
                              {notif.type === 'failed' && <AlertTriangle className="w-5 h-5" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{notif.job.name}</p>
                              <p className="text-xs text-surface-400">
                                {notif.type === 'running' && t('notifications.running')}
                                {notif.type === 'completed' && t('notifications.completed')}
                                {notif.type === 'failed' && t('notifications.failed')}
                              </p>
                            </div>
                          </Link>
                        ))
                      ) : (
                        <div className="p-8 text-center text-surface-400">
                          <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
                          <p>{t('notifications.noNotifications')}</p>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* User Menu (Mobile) */}
            <div className="relative lg:hidden" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 p-2 rounded-xl hover:bg-surface-800"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-emerald-500 flex items-center justify-center text-white text-sm font-semibold">
                  {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase()}
                </div>
                <ChevronDown className="w-4 h-4" />
              </button>

              <AnimatePresence>
                {showUserMenu && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className={cn(
                      "absolute mt-2 w-48 rounded-xl bg-surface-900 border border-surface-800 shadow-xl z-50 overflow-hidden",
                      isRtl ? "left-0" : "right-0"
                    )}
                  >
                    <div className="p-3 border-b border-surface-800">
                      <p className="font-medium truncate">{user?.full_name}</p>
                      <p className="text-xs text-surface-400 truncate">{user?.email}</p>
                    </div>
                    <Link
                      href="/dashboard/settings"
                      className="flex items-center gap-2 px-4 py-3 hover:bg-surface-800 transition-colors"
                      onClick={() => setShowUserMenu(false)}
                    >
                      <Settings className="w-4 h-4" />
                      {t('nav.settings')}
                    </Link>
                    <button
                      onClick={() => {
                        setShowUserMenu(false)
                        logout()
                      }}
                      className="flex items-center gap-2 px-4 py-3 w-full text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      {t('auth.logout')}
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <motion.div
            key={pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  )
}

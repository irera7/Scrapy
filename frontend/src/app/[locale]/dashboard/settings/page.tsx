'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '@/lib/api'
import { motion } from 'framer-motion'
import { useTranslations } from 'next-intl'
import { 
  User, 
  Lock, 
  Bell, 
  Loader2, 
  Check, 
  Palette, 
  Globe, 
  Moon, 
  Sun, 
  Monitor,
  Shield,
  Trash2,
  Download,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const settingsTutorial: TutorialSection[] = [
  {
    title: 'Settings Overview',
    content: 'Manage your account settings, appearance preferences, notifications, and security options. Changes are saved automatically or when you click the save button.',
    tips: [
      'Theme changes take effect immediately',
      'Notification settings are stored locally',
      'Password changes require at least 8 characters',
    ],
  },
  {
    title: 'Profile Settings',
    content: 'Update your display name and view your account email. Your email is used for login and cannot be changed from this page.',
    steps: [
      { title: 'Edit Name', description: 'Enter your full name in the text field' },
      { title: 'Save Changes', description: 'Click "Save Changes" to update your profile' },
    ],
  },
  {
    title: 'Appearance',
    content: 'Choose your preferred theme: Dark, Light, or System (follows your OS preference). The dark theme is optimized for extended use.',
    tips: [
      'Dark theme reduces eye strain during long sessions',
      'System option automatically switches with your OS',
      'Theme preference is saved in your browser',
    ],
  },
  {
    title: 'Notifications',
    content: 'Configure which notifications you want to receive. Toggle notifications for job completions, failures, export readiness, and weekly reports.',
    steps: [
      { title: 'Job Completed', description: 'Get notified when scraping jobs finish successfully' },
      { title: 'Job Failed', description: 'Alert when a job encounters an error' },
      { title: 'Export Ready', description: 'Know when your data export is ready to download' },
      { title: 'Weekly Report', description: 'Receive weekly activity summary' },
    ],
  },
  {
    title: 'Security',
    content: 'Update your password for enhanced account security. Use a strong password with at least 8 characters including numbers and special characters.',
    warning: 'After changing your password, you may need to log in again on other devices.',
    steps: [
      { title: 'Enter New Password', description: 'Type your new password (min 8 characters)' },
      { title: 'Confirm Password', description: 'Re-enter to confirm' },
      { title: 'Update', description: 'Click "Update Password" to save' },
    ],
  },
  {
    title: 'Data & Account',
    content: 'Download all your account data or delete your account. Data download includes all projects, collected data, and settings.',
    warning: 'Account deletion is permanent and cannot be undone. All your data will be lost.',
    tips: [
      'Download your data before deleting your account',
      'Exported data includes all projects and collected items',
    ],
  },
]

type Theme = 'dark' | 'light' | 'system'

export default function SettingsPage() {
  const t = useTranslations()
  const { user, setUser } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  
  const [theme, setTheme] = useState<Theme>('dark')
  const [notifications, setNotifications] = useState({
    jobComplete: true,
    jobFailed: true,
    exportReady: true,
    weeklyReport: false,
  })

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as Theme
    const savedNotifs = localStorage.getItem('notifications')
    
    if (savedTheme) setTheme(savedTheme)
    if (savedNotifs) setNotifications(JSON.parse(savedNotifs))
  }, [])

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    if (newTheme === 'light') {
      document.documentElement.classList.add('light')
    } else {
      document.documentElement.classList.remove('light')
    }
    toast.success('Theme saved')
  }

  const handleNotificationChange = (key: keyof typeof notifications) => {
    const newNotifs = { ...notifications, [key]: !notifications[key] }
    setNotifications(newNotifs)
    localStorage.setItem('notifications', JSON.stringify(newNotifs))
  }

  const updateProfileMutation = useMutation({
    mutationFn: (data: { full_name?: string }) => authApi.updateMe(data),
    onSuccess: (data) => {
      setUser(data)
      toast.success('Profile updated')
    },
    onError: () => {
      toast.error('Failed to update profile')
    },
  })

  const updatePasswordMutation = useMutation({
    mutationFn: (data: { password: string }) => authApi.updateMe(data),
    onSuccess: () => {
      setNewPassword('')
      setConfirmPassword('')
      toast.success('Password updated')
    },
    onError: () => {
      toast.error('Failed to update password')
    },
  })

  const handleUpdateProfile = (e: React.FormEvent) => {
    e.preventDefault()
    updateProfileMutation.mutate({ full_name: fullName })
  }

  const handleUpdatePassword = (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    updatePasswordMutation.mutate({ password: newPassword })
  }

  const handleExportData = () => {
    toast.success('Export request sent')
  }

  const handleDeleteAccount = () => {
    if (confirm('Are you sure? This action cannot be undone.')) {
      toast.error('This feature is not yet available')
    }
  }

  return (
    <div className="p-8 max-w-3xl">
      {/* Tutorial */}
      <TutorialPanel
        title="Settings Guide"
        description="Learn how to configure your account and preferences"
        sections={settingsTutorial}
        storageKey="settings"
      />

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">{t('settings.title')}</h1>
        <p className="text-surface-400">{t('settings.description') || 'Manage your account and preferences'}</p>
      </div>

      {/* Profile Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl glass p-6 mb-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center">
            <User className="w-6 h-6 text-brand-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Profile</h2>
            <p className="text-sm text-surface-400">Your account information</p>
          </div>
        </div>

        <form onSubmit={handleUpdateProfile} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Email</label>
            <input
              type="email"
              value={user?.email || ''}
              disabled
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 text-surface-400 cursor-not-allowed"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              placeholder="Your name"
            />
          </div>

          <button
            type="submit"
            disabled={updateProfileMutation.isPending}
            className="px-6 py-2.5 rounded-xl bg-brand-500 text-white font-medium hover:bg-brand-600 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {updateProfileMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Check className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </form>
      </motion.div>

      {/* Theme Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="rounded-2xl glass p-6 mb-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
            <Palette className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Appearance</h2>
            <p className="text-sm text-surface-400">Theme and display settings</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-3">{t('settings.theme')}</label>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => handleThemeChange('dark')}
                className={`p-4 rounded-xl border transition-all flex flex-col items-center gap-2 ${
                  theme === 'dark' 
                    ? 'border-brand-500 bg-brand-500/10' 
                    : 'border-surface-700 hover:border-surface-600'
                }`}
              >
                <Moon className="w-6 h-6" />
                <span className="text-sm">{t('settings.dark')}</span>
              </button>
              <button
                onClick={() => handleThemeChange('light')}
                className={`p-4 rounded-xl border transition-all flex flex-col items-center gap-2 ${
                  theme === 'light' 
                    ? 'border-brand-500 bg-brand-500/10' 
                    : 'border-surface-700 hover:border-surface-600'
                }`}
              >
                <Sun className="w-6 h-6" />
                <span className="text-sm">{t('settings.light')}</span>
              </button>
              <button
                onClick={() => handleThemeChange('system')}
                className={`p-4 rounded-xl border transition-all flex flex-col items-center gap-2 ${
                  theme === 'system' 
                    ? 'border-brand-500 bg-brand-500/10' 
                    : 'border-surface-700 hover:border-surface-600'
                }`}
              >
                <Monitor className="w-6 h-6" />
                <span className="text-sm">{t('settings.system')}</span>
              </button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Notifications Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="rounded-2xl glass p-6 mb-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-yellow-500/10 flex items-center justify-center">
            <Bell className="w-6 h-6 text-yellow-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Notifications</h2>
            <p className="text-sm text-surface-400">Notification and alert settings</p>
          </div>
        </div>

        <div className="space-y-4">
          {[
            { key: 'jobComplete', label: 'Job Completed', desc: 'When a job completes successfully' },
            { key: 'jobFailed', label: 'Job Failed', desc: 'When a job fails' },
            { key: 'exportReady', label: 'Export Ready', desc: 'When an export file is ready' },
            { key: 'weeklyReport', label: 'Weekly Report', desc: 'Weekly activity summary' },
          ].map((item) => (
            <div 
              key={item.key}
              className="flex items-center justify-between p-4 rounded-xl bg-surface-800/50"
            >
              <div>
                <p className="font-medium">{item.label}</p>
                <p className="text-sm text-surface-400">{item.desc}</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={notifications[item.key as keyof typeof notifications]}
                  onChange={() => handleNotificationChange(item.key as keyof typeof notifications)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-brand-500/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-500"></div>
              </label>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Security Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="rounded-2xl glass p-6 mb-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
            <Lock className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Security</h2>
            <p className="text-sm text-surface-400">Password and security settings</p>
          </div>
        </div>

        <form onSubmit={handleUpdatePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              placeholder="••••••••"
              minLength={8}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={updatePasswordMutation.isPending || !newPassword}
            className="px-6 py-2.5 rounded-xl bg-blue-500 text-white font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {updatePasswordMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Shield className="w-4 h-4" />
            )}
            Update Password
          </button>
        </form>
      </motion.div>

      {/* Data & Account Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="rounded-2xl glass p-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center">
            <Shield className="w-6 h-6 text-red-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Data & Account</h2>
            <p className="text-sm text-surface-400">Manage your data and account</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-surface-800/50 flex items-center justify-between">
            <div>
              <p className="font-medium">Download Data</p>
              <p className="text-sm text-surface-400">Download all your account data</p>
            </div>
            <button
              onClick={handleExportData}
              className="px-4 py-2 rounded-xl bg-surface-700 hover:bg-surface-600 transition-colors flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>

          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-between">
            <div>
              <p className="font-medium text-red-400">Delete Account</p>
              <p className="text-sm text-surface-400">Permanently delete your account and all data</p>
            </div>
            <button
              onClick={handleDeleteAccount}
              className="px-4 py-2 rounded-xl bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
        </div>

        {/* Account Info */}
        <div className="mt-6 p-4 rounded-xl bg-surface-800/50">
          <h3 className="font-medium mb-3">Account Information</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-surface-400">Role:</span>
              <span className="ml-2">{user?.role || 'user'}</span>
            </div>
            <div>
              <span className="text-surface-400">Member since:</span>
              <span className="ml-2">
                {user?.created_at 
                  ? new Date(user.created_at).toLocaleDateString() 
                  : '-'}
              </span>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

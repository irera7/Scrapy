'use client'

import { useState } from 'react'
import { useRouter, Link } from '@/i18n/navigation'
import { motion } from 'framer-motion'
import { useAuth } from '@/hooks/useAuth'
import { Loader2, ArrowLeft, ArrowRight, Database } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslations, useLocale } from 'next-intl'
import { isRtlLocale, type Locale } from '@/i18n/config'
import { LanguageSwitcher } from '@/components/ui/language-switcher'

export default function LoginPage() {
  const router = useRouter()
  const { login } = useAuth()
  const t = useTranslations()
  const locale = useLocale() as Locale
  const isRtl = isRtlLocale(locale)
  const [isLoading, setIsLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      await login(email, password)
      toast.success(t('auth.welcomeBack'))
      router.push('/dashboard')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || t('common.error'))
    } finally {
      setIsLoading(false)
    }
  }

  const BackArrow = isRtl ? ArrowRight : ArrowLeft

  return (
    <div className="min-h-screen flex">
      {/* Language Switcher */}
      <div className="absolute top-4 end-4 z-50">
        <LanguageSwitcher />
      </div>

      {/* Left Panel (End in RTL) */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-gradient-to-br from-surface-900 to-surface-950 items-center justify-center p-12">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-50" />
        <div className="absolute top-0 start-1/4 w-96 h-96 bg-brand-500/20 rounded-full blur-3xl" />
        
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="relative text-center"
        >
          <div className="w-20 h-20 rounded-2xl bg-brand-500/20 flex items-center justify-center mx-auto mb-8">
            <Database className="w-10 h-10 text-brand-400" />
          </div>
          <h2 className="text-3xl font-bold mb-4">AI Data Collector</h2>
          <p className="text-surface-400 max-w-md">
            {t('home.description')}
          </p>
        </motion.div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-surface-400 hover:text-white mb-8 transition-colors"
          >
            <BackArrow className="w-4 h-4" />
            {t('common.back')}
          </Link>

          <h1 className="text-3xl font-bold mb-2">{t('auth.welcomeBack')}</h1>
          <p className="text-surface-400 mb-8">{t('auth.signInToContinue')}</p>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2">
                {t('auth.email')}
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                placeholder="you@example.com"
                dir="ltr"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                {t('auth.password')}
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                placeholder="••••••••"
                dir="ltr"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {t('common.loading')}
                </>
              ) : (
                t('auth.login')
              )}
            </button>
          </form>

          <p className="mt-8 text-center text-surface-400">
            {t('auth.dontHaveAccount')}{' '}
            <Link href="/auth/register" className="text-brand-400 hover:text-brand-300 font-medium">
              {t('auth.register')}
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}


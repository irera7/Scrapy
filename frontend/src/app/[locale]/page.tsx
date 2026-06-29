'use client'

import { useAuth } from '@/hooks/useAuth'
import { useRouter } from '@/i18n/navigation'
import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { Loader2, Database, Brain, Zap } from 'lucide-react'
import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import { LanguageSwitcher } from '@/components/ui/language-switcher'

export default function Home() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const t = useTranslations()

  useEffect(() => {
    if (!isLoading && user) {
      router.push('/dashboard')
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
      </div>
    )
  }

  return (
    <main className="min-h-screen">
      {/* Top Bar with Language Switcher */}
      <div className="absolute top-0 end-0 p-4 z-50">
        <LanguageSwitcher />
      </div>

      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_110%)]" />
        
        {/* Gradient Orbs */}
        <div className="absolute top-0 start-1/4 w-96 h-96 bg-brand-500/20 rounded-full blur-3xl" />
        <div className="absolute top-1/3 end-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
        
        <div className="relative max-w-7xl mx-auto px-6 pt-20 pb-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass mb-8">
              <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
              <span className="text-sm text-surface-300">{t('home.badge')}</span>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
              <span className="block">{t('home.title')}</span>
              <span className="gradient-text">{t('home.titleHighlight')}</span>
            </h1>
            
            <p className="text-xl text-surface-400 max-w-2xl mx-auto mb-10">
              {t('home.description')}
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/auth/register"
                className="px-8 py-4 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors glow"
              >
                {t('home.getStarted')}
              </Link>
              <Link
                href="/auth/login"
                className="px-8 py-4 rounded-xl glass font-semibold hover:bg-surface-800 transition-colors"
              >
                {t('home.signIn')}
              </Link>
            </div>
          </motion.div>

          {/* Features */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="grid md:grid-cols-3 gap-6 mt-24"
          >
            <FeatureCard
              icon={<Database className="w-6 h-6" />}
              title={t('home.features.multiSource.title')}
              description={t('home.features.multiSource.description')}
            />
            <FeatureCard
              icon={<Brain className="w-6 h-6" />}
              title={t('home.features.aiReady.title')}
              description={t('home.features.aiReady.description')}
            />
            <FeatureCard
              icon={<Zap className="w-6 h-6" />}
              title={t('home.features.processing.title')}
              description={t('home.features.processing.description')}
            />
          </motion.div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-surface-800 py-8">
        <div className="max-w-7xl mx-auto px-6 text-center text-surface-500">
          <p>{t('home.footer')}</p>
        </div>
      </footer>
    </main>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="p-6 rounded-2xl glass card-hover">
      <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center text-brand-400 mb-4">
        {icon}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-surface-400">{description}</p>
    </div>
  )
}


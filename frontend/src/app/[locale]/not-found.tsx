'use client'

import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import { Home, ArrowLeft, ArrowRight } from 'lucide-react'
import { useLocale } from 'next-intl'
import { isRtlLocale, type Locale } from '@/i18n/config'

export default function NotFound() {
  const t = useTranslations()
  const locale = useLocale() as Locale
  const isRtl = isRtlLocale(locale)
  const BackArrow = isRtl ? ArrowRight : ArrowLeft

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-950">
      <div className="text-center">
        <h1 className="text-9xl font-bold text-brand-500">404</h1>
        <p className="text-2xl font-semibold mt-4">Page Not Found</p>
        <p className="text-surface-400 mt-2 mb-8">
          {t('common.noResults')}
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors"
          >
            <Home className="w-5 h-5" />
            {t('common.back')}
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl glass hover:bg-surface-800 transition-colors"
          >
            <BackArrow className="w-5 h-5" />
            {t('nav.dashboard')}
          </Link>
        </div>
      </div>
    </div>
  )
}


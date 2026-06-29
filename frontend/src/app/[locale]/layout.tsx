import type { Metadata } from 'next'
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
import { NextIntlClientProvider } from 'next-intl'
import { getMessages } from 'next-intl/server'
import { notFound } from 'next/navigation'
import '../globals.css'
import { Providers } from '@/components/providers'
import { locales, getDirection, type Locale } from '@/i18n/config'

export const metadata: Metadata = {
  title: 'AI Data Collector',
  description: 'Web scraping and data collection platform for AI model training',
  keywords: ['AI', 'Data Collection', 'Web Scraping', 'Machine Learning', 'Dataset'],
  authors: [{ name: 'AI Data Collector Team' }],
}

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }))
}

interface RootLayoutProps {
  children: React.ReactNode
  params: { locale: string }
}

export default async function LocaleLayout({
  children,
  params: { locale },
}: RootLayoutProps) {
  // Validate locale
  if (!locales.includes(locale as Locale)) {
    notFound()
  }

  // Get messages for the locale
  const messages = await getMessages()

  // Determine text direction
  const dir = getDirection(locale as Locale)

  return (
    <html 
      lang={locale} 
      dir={dir} 
      className={`${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <link rel="icon" href="/favicon.ico" />
        <meta name="theme-color" content="#0a0a0f" />
        {/* Add Vazirmatn font for Persian/Arabic - using Google Fonts as reliable CDN */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link 
          href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@100;200;300;400;500;600;700;800;900&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body 
        className={`min-h-screen bg-surface-950 text-surface-50 antialiased ${
          dir === 'rtl' ? 'font-vazir' : ''
        }`}
      >
        <NextIntlClientProvider messages={messages}>
          <Providers>
            {children}
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}

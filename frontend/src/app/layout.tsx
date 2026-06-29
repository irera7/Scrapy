import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'AI Data Collector',
  description: 'Web scraping and data collection platform for AI model training',
}

// Root layout - delegates to locale-specific layouts
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}

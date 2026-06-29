'use client'

import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LoadingProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
  text?: string
}

export function Loading({ className, size = 'md', text }: LoadingProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }

  return (
    <div className={cn("flex flex-col items-center justify-center", className)}>
      <Loader2 className={cn("animate-spin text-brand-500", sizeClasses[size])} />
      {text && <p className="mt-3 text-surface-400 text-sm">{text}</p>}
    </div>
  )
}

export function PageLoading({ text = "در حال بارگذاری..." }: { text?: string }) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <Loading size="lg" text={text} />
    </div>
  )
}

export function FullPageLoading({ text = "در حال بارگذاری..." }: { text?: string }) {
  return (
    <div className="fixed inset-0 bg-surface-950/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="text-center">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-surface-700 rounded-full" />
          <div className="w-16 h-16 border-4 border-brand-500 border-t-transparent rounded-full animate-spin absolute inset-0" />
        </div>
        {text && <p className="mt-4 text-surface-300">{text}</p>}
      </div>
    </div>
  )
}

export function InlineLoading({ text = "در حال بارگذاری..." }: { text?: string }) {
  return (
    <div className="flex items-center gap-2 text-surface-400">
      <Loader2 className="w-4 h-4 animate-spin" />
      <span className="text-sm">{text}</span>
    </div>
  )
}

export function ButtonLoading() {
  return <Loader2 className="w-4 h-4 animate-spin" />
}


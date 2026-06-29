'use client'

import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-brand-500/10 text-brand-400',
        secondary: 'border-transparent bg-surface-700 text-surface-200',
        success: 'border-transparent bg-green-500/10 text-green-400',
        warning: 'border-transparent bg-yellow-500/10 text-yellow-400',
        destructive: 'border-transparent bg-red-500/10 text-red-400',
        error: 'border-transparent bg-red-500/10 text-red-400',
        outline: 'border-surface-600 text-surface-300',
        blue: 'border-transparent bg-blue-500/10 text-blue-400',
        purple: 'border-transparent bg-purple-500/10 text-purple-400',
      },
      size: {
        sm: 'px-2 py-0.5 text-xs',
        default: 'px-2.5 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean
}

function Badge({ className, variant, size, dot, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {dot && (
        <span className={cn(
          'mr-1.5 h-1.5 w-1.5 rounded-full',
          variant === 'success' && 'bg-green-400',
          variant === 'warning' && 'bg-yellow-400',
          (variant === 'destructive' || variant === 'error') && 'bg-red-400',
          variant === 'blue' && 'bg-blue-400',
          variant === 'purple' && 'bg-purple-400',
          variant === 'default' && 'bg-brand-400',
          variant === 'secondary' && 'bg-surface-400',
        )} />
      )}
      {children}
    </div>
  )
}

export { Badge, badgeVariants }


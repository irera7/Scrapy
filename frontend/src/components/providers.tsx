'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="bottom-left"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1a1a2e',
            color: '#f1f5f9',
            border: '1px solid #334155',
            borderRadius: '12px',
            padding: '12px 16px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
            direction: 'rtl',
          },
          success: {
            iconTheme: {
              primary: '#22c55e',
              secondary: '#f1f5f9',
            },
            style: {
              background: '#1a1a2e',
              border: '1px solid rgba(34, 197, 94, 0.2)',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#f1f5f9',
            },
            style: {
              background: '#1a1a2e',
              border: '1px solid rgba(239, 68, 68, 0.2)',
            },
          },
          loading: {
            iconTheme: {
              primary: '#3b82f6',
              secondary: '#f1f5f9',
            },
          },
        }}
      />
    </QueryClientProvider>
  )
}

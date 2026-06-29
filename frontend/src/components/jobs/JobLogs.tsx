'use client';

import React from 'react';
import { Card, Badge, Skeleton } from '@/components/ui';

interface JobLog {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  details?: Record<string, any>;
  created_at: string;
}

interface JobLogsProps {
  logs: JobLog[];
  isLoading?: boolean;
  maxHeight?: string;
}

const levelConfig = {
  info: { label: 'اطلاعات', variant: 'default' as const, bg: 'bg-blue-50 border-blue-200' },
  warning: { label: 'هشدار', variant: 'warning' as const, bg: 'bg-yellow-50 border-yellow-200' },
  error: { label: 'خطا', variant: 'error' as const, bg: 'bg-red-50 border-red-200' },
};

export function JobLogs({ logs, isLoading = false, maxHeight = '400px' }: JobLogsProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-md" />
        ))}
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <svg className="mx-auto w-12 h-12 mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p>هیچ لاگی وجود ندارد</p>
      </div>
    );
  }

  return (
    <div 
      className="space-y-2 overflow-y-auto pr-2"
      style={{ maxHeight }}
    >
      {logs.map((log) => {
        const config = levelConfig[log.level];
        return (
          <div
            key={log.id}
            className={`p-3 rounded-md border ${config.bg}`}
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <Badge variant={config.variant} size="sm">
                {config.label}
              </Badge>
              <span className="text-xs text-gray-500">
                {new Date(log.created_at).toLocaleString('fa-IR')}
              </span>
            </div>
            <p className="text-sm font-medium">{log.message}</p>
            {log.details && Object.keys(log.details).length > 0 && (
              <details className="mt-2">
                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                  جزئیات بیشتر
                </summary>
                <pre className="mt-2 text-xs bg-white/50 p-2 rounded overflow-x-auto">
                  {JSON.stringify(log.details, null, 2)}
                </pre>
              </details>
            )}
          </div>
        );
      })}
    </div>
  );
}


'use client';

import React, { useState } from 'react';
import { Card, Badge, Button, Progress } from '@/components/ui';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { JobLogs } from './JobLogs';

type JobStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

interface Job {
  id: string;
  name: string;
  provider: string;
  status: JobStatus;
  config: Record<string, any>;
  items_collected?: number;
  retry_count?: number;
  max_retries?: number;
  error_message?: string;
  schedule?: string;
  last_run?: string;
  created_at: string;
}

interface JobLog {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  details?: Record<string, any>;
  created_at: string;
}

interface JobDetailProps {
  job: Job;
  logs?: JobLog[];
  isLoading?: boolean;
  onRun?: () => Promise<void>;
  onRetry?: () => Promise<void>;
  onCancel?: () => Promise<void>;
  onReset?: () => Promise<void>;
  onBack?: () => void;
}

const statusConfig: Record<JobStatus, { label: string; variant: 'default' | 'success' | 'warning' | 'error'; icon: string }> = {
  pending: { label: 'در انتظار', variant: 'default', icon: '⏳' },
  queued: { label: 'در صف', variant: 'warning', icon: '📋' },
  running: { label: 'در حال اجرا', variant: 'warning', icon: '🔄' },
  completed: { label: 'موفق', variant: 'success', icon: '✅' },
  failed: { label: 'ناموفق', variant: 'error', icon: '❌' },
  cancelled: { label: 'لغو شده', variant: 'default', icon: '🚫' },
};

const providerLabels: Record<string, { name: string; icon: string }> = {
  serpapi: { name: 'SerpAPI', icon: '🔍' },
  apify: { name: 'Apify', icon: '🤖' },
  custom: { name: 'سفارشی', icon: '⚙️' },
  browserless: { name: 'Browserless', icon: '🌐' },
  twitter: { name: 'Twitter', icon: '🐦' },
  reddit: { name: 'Reddit', icon: '📰' },
  youtube: { name: 'YouTube', icon: '📺' },
  github: { name: 'GitHub', icon: '💻' },
  newsapi: { name: 'NewsAPI', icon: '📰' },
  google_news: { name: 'Google News', icon: '📰' },
  hackernews: { name: 'Hacker News', icon: '🔶' },
  arxiv: { name: 'arXiv', icon: '📄' },
  wikipedia: { name: 'Wikipedia', icon: '📚' },
  sitemap: { name: 'Sitemap', icon: '🗺️' },
  rss: { name: 'RSS', icon: '📡' },
  webcrawler: { name: 'Web Crawler', icon: '🕷️' },
  image_scraper: { name: 'Image Scraper', icon: '🖼️' },
  audio_scraper: { name: 'Audio Scraper', icon: '🎵' },
  video_scraper: { name: 'Video Scraper', icon: '🎬' },
};

export function JobDetail({
  job,
  logs = [],
  isLoading = false,
  onRun,
  onRetry,
  onCancel,
  onReset,
  onBack,
}: JobDetailProps) {
  const [activeTab, setActiveTab] = useState('overview');
  const [actionLoading, setActionLoading] = useState(false);

  const status = statusConfig[job.status];
  const provider = providerLabels[job.provider] || { name: job.provider, icon: '📡' };
  const canRetry = job.status === 'failed' && (job.retry_count || 0) < (job.max_retries || 3);
  const canReset = job.status === 'failed' && (job.retry_count || 0) >= (job.max_retries || 3);

  const handleAction = async (action: () => Promise<void>) => {
    setActionLoading(true);
    try {
      await action();
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="ghost" size="sm" onClick={onBack}>
              <svg className="w-5 h-5 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              بازگشت
            </Button>
          )}
          <div>
            <h1 className="text-2xl font-bold">{job.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="default">
                {provider.icon} {provider.name}
              </Badge>
              <Badge variant={status.variant}>
                {status.icon} {status.label}
              </Badge>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {(job.status === 'pending' || job.status === 'completed' || job.status === 'cancelled') && onRun && (
            <Button onClick={() => handleAction(onRun)} disabled={actionLoading}>
              ▶️ اجرا
            </Button>
          )}
          {canRetry && onRetry && (
            <Button variant="warning" onClick={() => handleAction(onRetry)} disabled={actionLoading}>
              🔄 تلاش مجدد
            </Button>
          )}
          {canReset && onReset && (
            <Button variant="outline" onClick={() => handleAction(onReset)} disabled={actionLoading}>
              ↩️ بازنشانی
            </Button>
          )}
          {(job.status === 'running' || job.status === 'queued') && onCancel && (
            <Button variant="error" onClick={() => handleAction(onCancel)} disabled={actionLoading}>
              ⏹️ لغو
            </Button>
          )}
        </div>
      </div>

      {/* Progress for running */}
      {job.status === 'running' && (
        <Card className="p-4">
          <div className="flex items-center gap-4">
            <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full" />
            <div className="flex-1">
              <p className="font-medium">در حال جمع‌آوری داده...</p>
              <Progress value={undefined} className="mt-2 animate-pulse" />
            </div>
          </div>
        </Card>
      )}

      {/* Error with retry info */}
      {job.status === 'failed' && (
        <Card className="p-4 bg-red-50 border-red-200">
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <h3 className="font-semibold text-red-800">خطا در اجرای جاب</h3>
              <p className="text-red-700 mt-1">{job.error_message}</p>
              {(job.retry_count || 0) > 0 && (
                <div className="mt-3">
                  <div className="flex justify-between text-sm text-red-600 mb-1">
                    <span>تلاش‌های انجام شده</span>
                    <span>{job.retry_count} از {job.max_retries}</span>
                  </div>
                  <Progress 
                    value={((job.retry_count || 0) / (job.max_retries || 3)) * 100}
                    className="h-2 bg-red-200"
                  />
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">📊 خلاصه</TabsTrigger>
          <TabsTrigger value="config">⚙️ تنظیمات</TabsTrigger>
          <TabsTrigger value="logs">📜 لاگ‌ها ({logs.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4">
              <p className="text-sm text-gray-500">آیتم‌های جمع‌آوری شده</p>
              <p className="text-2xl font-bold">{(job.items_collected || 0).toLocaleString()}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-500">تعداد تلاش</p>
              <p className="text-2xl font-bold">{job.retry_count || 0} / {job.max_retries || 3}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-500">آخرین اجرا</p>
              <p className="text-lg font-medium">
                {job.last_run 
                  ? new Date(job.last_run).toLocaleString('fa-IR')
                  : '—'
                }
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-500">زمان‌بندی</p>
              <p className="text-lg font-medium">
                {job.schedule || 'بدون زمان‌بندی'}
              </p>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="config">
          <Card className="p-4">
            <h3 className="font-semibold mb-4">تنظیمات جاب</h3>
            <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
              {JSON.stringify(job.config, null, 2)}
            </pre>
          </Card>
        </TabsContent>

        <TabsContent value="logs">
          <Card className="p-4">
            <h3 className="font-semibold mb-4">لاگ‌های اجرا</h3>
            <JobLogs logs={logs} isLoading={isLoading} maxHeight="500px" />
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}


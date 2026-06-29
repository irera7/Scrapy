'use client';

import React from 'react';
import { Card, Badge, Button, Progress, Tooltip } from '@/components/ui';

type JobStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

interface JobCardProps {
  id: string;
  name: string;
  provider: string;
  status: JobStatus;
  itemsCollected?: number;
  retryCount?: number;
  maxRetries?: number;
  errorMessage?: string;
  lastRun?: string;
  createdAt: string;
  onRun?: () => void;
  onRetry?: () => void;
  onCancel?: () => void;
  onReset?: () => void;
  onView?: () => void;
  isLoading?: boolean;
}

const statusConfig: Record<JobStatus, { label: string; variant: 'default' | 'success' | 'warning' | 'error' }> = {
  pending: { label: 'در انتظار', variant: 'default' },
  queued: { label: 'در صف', variant: 'warning' },
  running: { label: 'در حال اجرا', variant: 'warning' },
  completed: { label: 'موفق', variant: 'success' },
  failed: { label: 'ناموفق', variant: 'error' },
  cancelled: { label: 'لغو شده', variant: 'default' },
};

const providerLabels: Record<string, string> = {
  serpapi: 'SerpAPI',
  apify: 'Apify',
  custom: 'سفارشی',
  browserless: 'Browserless',
  twitter: 'Twitter',
  reddit: 'Reddit',
  youtube: 'YouTube',
  github: 'GitHub',
  newsapi: 'NewsAPI',
  google_news: 'Google News',
  hackernews: 'Hacker News',
  arxiv: 'arXiv',
  wikipedia: 'Wikipedia',
  sitemap: 'Sitemap',
  rss: 'RSS',
  webcrawler: 'Web Crawler',
  image_scraper: 'Image Scraper',
  audio_scraper: 'Audio Scraper',
  video_scraper: 'Video Scraper',
};

export function JobCard({
  id,
  name,
  provider,
  status,
  itemsCollected = 0,
  retryCount = 0,
  maxRetries = 3,
  errorMessage,
  lastRun,
  createdAt,
  onRun,
  onRetry,
  onCancel,
  onReset,
  onView,
  isLoading = false,
}: JobCardProps) {
  const config = statusConfig[status];
  const canRetry = status === 'failed' && retryCount < maxRetries;
  const canReset = status === 'failed' && retryCount >= maxRetries;

  return (
    <Card className="p-4 hover:shadow-lg transition-shadow duration-200">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-lg truncate">{name}</h3>
          <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
            <Badge variant="default" size="sm">
              {providerLabels[provider] || provider}
            </Badge>
            <span>•</span>
            <span>{itemsCollected.toLocaleString()} آیتم</span>
          </div>
        </div>
        <Badge variant={config.variant}>{config.label}</Badge>
      </div>

      {/* Progress for running jobs */}
      {status === 'running' && (
        <div className="mb-3">
          <Progress value={undefined} className="animate-pulse" />
          <p className="text-xs text-gray-500 mt-1 text-center">در حال جمع‌آوری داده...</p>
        </div>
      )}

      {/* Error message */}
      {status === 'failed' && errorMessage && (
        <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700 truncate">{errorMessage}</p>
          {retryCount > 0 && (
            <p className="text-xs text-red-500 mt-1">
              تلاش {retryCount} از {maxRetries}
            </p>
          )}
        </div>
      )}

      {/* Retry progress */}
      {status === 'failed' && retryCount > 0 && (
        <div className="mb-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>تلاش‌های انجام شده</span>
            <span>{retryCount} / {maxRetries}</span>
          </div>
          <Progress 
            value={(retryCount / maxRetries) * 100} 
            className="h-2"
          />
        </div>
      )}

      {/* Timestamps */}
      <div className="text-xs text-gray-400 mb-3 flex gap-4">
        {lastRun && (
          <span>
            آخرین اجرا: {new Date(lastRun).toLocaleDateString('fa-IR')}
          </span>
        )}
        <span>
          ایجاد: {new Date(createdAt).toLocaleDateString('fa-IR')}
        </span>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        {/* View Details */}
        <Button
          variant="outline"
          size="sm"
          onClick={onView}
          disabled={isLoading}
        >
          جزئیات
        </Button>

        {/* Run */}
        {(status === 'pending' || status === 'completed' || status === 'cancelled') && (
          <Button
            variant="default"
            size="sm"
            onClick={onRun}
            disabled={isLoading}
          >
            اجرا
          </Button>
        )}

        {/* Retry */}
        {canRetry && (
          <Tooltip content={`تلاش ${retryCount + 1} از ${maxRetries}`}>
            <Button
              variant="warning"
              size="sm"
              onClick={onRetry}
              disabled={isLoading}
            >
              تلاش مجدد
            </Button>
          </Tooltip>
        )}

        {/* Reset */}
        {canReset && (
          <Tooltip content="بازنشانی تعداد تلاش‌ها">
            <Button
              variant="outline"
              size="sm"
              onClick={onReset}
              disabled={isLoading}
            >
              بازنشانی
            </Button>
          </Tooltip>
        )}

        {/* Cancel */}
        {(status === 'running' || status === 'queued') && (
          <Button
            variant="error"
            size="sm"
            onClick={onCancel}
            disabled={isLoading}
          >
            لغو
          </Button>
        )}
      </div>
    </Card>
  );
}


'use client';

import React, { useState } from 'react';
import { JobCard } from './JobCard';
import { Skeleton, EmptyState, Pagination, Badge } from '@/components/ui';
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select';
import { Monitor } from 'lucide-react';

type JobStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

interface Job {
  id: string;
  name: string;
  provider: string;
  status: JobStatus;
  items_collected?: number;
  retry_count?: number;
  max_retries?: number;
  error_message?: string;
  last_run?: string;
  created_at: string;
}

interface JobListProps {
  jobs: Job[];
  isLoading?: boolean;
  totalCount?: number;
  currentPage?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onStatusFilter?: (status: string) => void;
  statusFilter?: string;
  onRunJob?: (jobId: string) => Promise<void>;
  onRetryJob?: (jobId: string) => Promise<void>;
  onCancelJob?: (jobId: string) => Promise<void>;
  onResetJob?: (jobId: string) => Promise<void>;
  onViewJob?: (jobId: string) => void;
}

const statusOptions = [
  { value: '', label: 'همه وضعیت‌ها' },
  { value: 'pending', label: 'در انتظار' },
  { value: 'queued', label: 'در صف' },
  { value: 'running', label: 'در حال اجرا' },
  { value: 'completed', label: 'موفق' },
  { value: 'failed', label: 'ناموفق' },
  { value: 'cancelled', label: 'لغو شده' },
];

export function JobList({
  jobs,
  isLoading = false,
  totalCount = 0,
  currentPage = 1,
  pageSize = 10,
  onPageChange,
  onStatusFilter,
  statusFilter = '',
  onRunJob,
  onRetryJob,
  onCancelJob,
  onResetJob,
  onViewJob,
}: JobListProps) {
  const [loadingJobId, setLoadingJobId] = useState<string | null>(null);

  const handleAction = async (action: (jobId: string) => Promise<void>, jobId: string) => {
    setLoadingJobId(jobId);
    try {
      await action(jobId);
    } finally {
      setLoadingJobId(null);
    }
  };

  // Count by status
  const statusCounts = jobs.reduce((acc, job) => {
    acc[job.status] = (acc[job.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Filter skeleton */}
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-48" />
        </div>
        {/* Job cards skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <EmptyState
        title="هیچ جاب اسکرپینگی وجود ندارد"
        description="یک جاب جدید ایجاد کنید تا شروع به جمع‌آوری داده کنید."
        action={{
          label: "ایجاد جاب جدید",
          href: "/dashboard/jobs/new"
        }}
        icon={Monitor}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters and Stats */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Status Filter */}
        <div className="flex items-center gap-3 w-48">
          <Select
            value={statusFilter}
            onValueChange={(value) => onStatusFilter?.(value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="همه وضعیت‌ها" />
            </SelectTrigger>
            <SelectContent>
              {statusOptions.map(opt => (
                <SelectItem key={opt.value || 'all'} value={opt.value || 'all'}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Stats Badges */}
        <div className="flex flex-wrap gap-2">
          {statusCounts.running && statusCounts.running > 0 && (
            <Badge variant="warning">
              {statusCounts.running} در حال اجرا
            </Badge>
          )}
          {statusCounts.failed && statusCounts.failed > 0 && (
            <Badge variant="error">
              {statusCounts.failed} ناموفق
            </Badge>
          )}
          {statusCounts.completed && statusCounts.completed > 0 && (
            <Badge variant="success">
              {statusCounts.completed} موفق
            </Badge>
          )}
          <Badge variant="default">
            {totalCount} کل جاب‌ها
          </Badge>
        </div>
      </div>

      {/* Job Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {jobs.map((job) => (
          <JobCard
            key={job.id}
            id={job.id}
            name={job.name}
            provider={job.provider}
            status={job.status}
            itemsCollected={job.items_collected}
            retryCount={job.retry_count}
            maxRetries={job.max_retries}
            errorMessage={job.error_message}
            lastRun={job.last_run}
            createdAt={job.created_at}
            isLoading={loadingJobId === job.id}
            onRun={onRunJob ? () => handleAction(onRunJob, job.id) : undefined}
            onRetry={onRetryJob ? () => handleAction(onRetryJob, job.id) : undefined}
            onCancel={onCancelJob ? () => handleAction(onCancelJob, job.id) : undefined}
            onReset={onResetJob ? () => handleAction(onResetJob, job.id) : undefined}
            onView={onViewJob ? () => onViewJob(job.id) : undefined}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalCount > pageSize && onPageChange && (
        <Pagination
          currentPage={currentPage}
          totalPages={Math.ceil(totalCount / pageSize)}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
}


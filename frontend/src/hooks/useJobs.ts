'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';

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
  project_id: string;
}

interface JobLog {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  details?: Record<string, any>;
  created_at: string;
}

interface CreateJobData {
  project_id: string;
  name: string;
  provider: string;
  config: Record<string, any>;
  schedule?: string;
  priority?: number;
  max_retries?: number;
}

interface UseJobsOptions {
  projectId?: string;
  statusFilter?: string;
  page?: number;
  pageSize?: number;
}

export function useJobs(options: UseJobsOptions = {}) {
  const { projectId, statusFilter, page = 1, pageSize = 10 } = options;
  const queryClient = useQueryClient();

  const skip = (page - 1) * pageSize;

  // Fetch jobs
  const jobsQuery = useQuery({
    queryKey: ['jobs', { projectId, statusFilter, skip, limit: pageSize }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);
      if (statusFilter) params.append('status_filter', statusFilter);
      params.append('skip', skip.toString());
      params.append('limit', pageSize.toString());

      const response = await api.get(`/api/v1/jobs?${params}`);
      return response.data as Job[];
    },
    staleTime: 30000, // 30 seconds
  });

  // Run job mutation
  const runJobMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const response = await api.post(`/api/v1/jobs/${jobId}/run`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  // Retry job mutation
  const retryJobMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const response = await api.post(`/api/v1/jobs/${jobId}/retry`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  // Cancel job mutation
  const cancelJobMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const response = await api.post(`/api/v1/jobs/${jobId}/cancel`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  // Reset job mutation
  const resetJobMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const response = await api.post(`/api/v1/jobs/${jobId}/reset`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  // Create job mutation
  const createJobMutation = useMutation({
    mutationFn: async (data: CreateJobData) => {
      const response = await api.post('/api/v1/jobs', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  // Delete job mutation
  const deleteJobMutation = useMutation({
    mutationFn: async (jobId: string) => {
      await api.delete(`/api/v1/jobs/${jobId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  return {
    jobs: jobsQuery.data || [],
    isLoading: jobsQuery.isLoading,
    error: jobsQuery.error,
    refetch: jobsQuery.refetch,

    runJob: runJobMutation.mutateAsync,
    retryJob: retryJobMutation.mutateAsync,
    cancelJob: cancelJobMutation.mutateAsync,
    resetJob: resetJobMutation.mutateAsync,
    createJob: createJobMutation.mutateAsync,
    deleteJob: deleteJobMutation.mutateAsync,

    isRunning: runJobMutation.isPending,
    isRetrying: retryJobMutation.isPending,
    isCancelling: cancelJobMutation.isPending,
    isResetting: resetJobMutation.isPending,
  };
}

export function useJob(jobId: string | null) {
  const queryClient = useQueryClient();

  // Fetch single job
  const jobQuery = useQuery({
    queryKey: ['job', jobId],
    queryFn: async () => {
      if (!jobId) return null;
      const response = await api.get(`/api/v1/jobs/${jobId}`);
      return response.data as Job;
    },
    enabled: !!jobId,
    staleTime: 10000,
  });

  // Fetch job logs
  const logsQuery = useQuery({
    queryKey: ['job-logs', jobId],
    queryFn: async () => {
      if (!jobId) return [];
      const response = await api.get(`/api/v1/jobs/${jobId}/logs`);
      return response.data as JobLog[];
    },
    enabled: !!jobId,
    staleTime: 5000,
  });

  return {
    job: jobQuery.data,
    logs: logsQuery.data || [],
    isLoading: jobQuery.isLoading || logsQuery.isLoading,
    error: jobQuery.error || logsQuery.error,
    refetch: () => {
      jobQuery.refetch();
      logsQuery.refetch();
    },
  };
}

export function useJobPolling(jobId: string | null, enabled: boolean = true) {
  const queryClient = useQueryClient();
  const [isPolling, setIsPolling] = useState(false);

  // Poll job status when running
  const jobQuery = useQuery({
    queryKey: ['job-polling', jobId],
    queryFn: async () => {
      if (!jobId) return null;
      const response = await api.get(`/api/v1/jobs/${jobId}`);
      return response.data as Job;
    },
    enabled: enabled && !!jobId,
    refetchInterval: (data) => {
      // Poll every 2 seconds if job is running or queued
      if (data?.state?.data?.status === 'running' || data?.state?.data?.status === 'queued') {
        setIsPolling(true);
        return 2000;
      }
      setIsPolling(false);
      return false;
    },
  });

  return {
    job: jobQuery.data,
    isPolling,
    isLoading: jobQuery.isLoading,
  };
}


'use client'

import { useState, useEffect, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { jobsApi } from '@/lib/api'
import toast from 'react-hot-toast'

export interface Notification {
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  title: string
  message: string
  timestamp: Date
  read: boolean
  link?: string
  data?: any
}

const STORAGE_KEY = 'ai-data-collector-notifications'
const MAX_NOTIFICATIONS = 50

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [previousJobs, setPreviousJobs] = useState<Map<string, string>>(new Map())
  const queryClient = useQueryClient()

  // Load notifications from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        setNotifications(parsed.map((n: any) => ({
          ...n,
          timestamp: new Date(n.timestamp)
        })))
      } catch (e) {
        console.error('Failed to parse notifications', e)
      }
    }
  }, [])

  // Save notifications to localStorage
  useEffect(() => {
    if (notifications.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications.slice(0, MAX_NOTIFICATIONS)))
    }
  }, [notifications])

  // Poll jobs for status changes
  const { data: jobs } = useQuery({
    queryKey: ['jobs-notifications'],
    queryFn: () => jobsApi.list({ limit: 50 }),
    refetchInterval: 5000,
  })

  // Detect job status changes
  useEffect(() => {
    if (!jobs) return

    jobs.forEach((job: any) => {
      const prevStatus = previousJobs.get(job.id)
      
      if (prevStatus && prevStatus !== job.status) {
        // Status changed!
        if (job.status === 'completed' && prevStatus === 'running') {
          addNotification({
            type: 'success',
            title: 'جاب تکمیل شد',
            message: `جاب "${job.name}" با موفقیت ${job.items_collected || 0} آیتم جمع‌آوری کرد`,
            link: `/dashboard/jobs/${job.id}`,
            data: { jobId: job.id }
          })
          
          toast.success(`جاب "${job.name}" تکمیل شد!`, {
            duration: 5000,
            icon: '✅',
          })
        } else if (job.status === 'failed' && prevStatus === 'running') {
          addNotification({
            type: 'error',
            title: 'جاب ناموفق',
            message: `جاب "${job.name}" با خطا مواجه شد: ${job.error_message || 'خطای نامشخص'}`,
            link: `/dashboard/jobs/${job.id}`,
            data: { jobId: job.id }
          })
          
          toast.error(`جاب "${job.name}" ناموفق بود`, {
            duration: 5000,
            icon: '❌',
          })
        }
      }
    })

    // Update previous jobs map
    const newMap = new Map()
    jobs.forEach((job: any) => {
      newMap.set(job.id, job.status)
    })
    setPreviousJobs(newMap)
  }, [jobs])

  const addNotification = useCallback((notif: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      read: false,
      ...notif
    }

    setNotifications(prev => [newNotification, ...prev].slice(0, MAX_NOTIFICATIONS))
  }, [])

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    )
  }, [])

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }, [])

  const clearNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }, [])

  const clearAll = useCallback(() => {
    setNotifications([])
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  const unreadCount = notifications.filter(n => !n.read).length

  return {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    markAllAsRead,
    clearNotification,
    clearAll,
  }
}


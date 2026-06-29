import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBytes(bytes: number, decimals = 2) {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

export function formatNumber(num: number) {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

export function formatDate(date: string | Date) {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(date: string | Date) {
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function getStatusColor(status: string) {
  switch (status) {
    case 'completed':
      return 'text-green-400 bg-green-400/10'
    case 'running':
    case 'processing':
      return 'text-blue-400 bg-blue-400/10'
    case 'pending':
    case 'queued':
      return 'text-yellow-400 bg-yellow-400/10'
    case 'failed':
      return 'text-red-400 bg-red-400/10'
    case 'cancelled':
      return 'text-gray-400 bg-gray-400/10'
    default:
      return 'text-gray-400 bg-gray-400/10'
  }
}

export function getDataTypeIcon(type: string) {
  switch (type) {
    case 'text':
      return '📝'
    case 'image':
      return '🖼️'
    case 'audio':
      return '🎵'
    case 'video':
      return '🎬'
    case 'structured':
      return '📊'
    default:
      return '📄'
  }
}


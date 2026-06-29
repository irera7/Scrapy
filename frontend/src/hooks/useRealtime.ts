'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

const WEBSOCKET_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8099'

interface WebSocketMessage {
  type: string
  payload: any
}

interface UseRealtimeOptions {
  enabled?: boolean
  onConnect?: () => void
  onDisconnect?: () => void
  onMessage?: (message: WebSocketMessage) => void
}

export function useRealtime(options: UseRealtimeOptions = {}) {
  const { enabled = true, onConnect, onDisconnect, onMessage } = options
  
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttempts = useRef(0)
  const queryClient = useQueryClient()

  const connect = useCallback(() => {
    if (!enabled || wsRef.current?.readyState === WebSocket.OPEN) return

    const token = localStorage.getItem('access_token')
    if (!token) return

    try {
      // Connect to the updates endpoint with token
      const ws = new WebSocket(`${WEBSOCKET_URL}/ws/updates?token=${encodeURIComponent(token)}`)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        reconnectAttempts.current = 0
        onConnect?.()
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason)
        setIsConnected(false)
        wsRef.current = null
        onDisconnect?.()
        
        // Don't reconnect if token was invalid
        if (event.code === 4001) {
          console.log('Invalid token, not reconnecting')
          return
        }
        
        // Attempt reconnection with exponential backoff
        if (enabled && reconnectAttempts.current < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          console.log(`Reconnecting in ${delay}ms...`)
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++
            connect()
          }, delay)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          onMessage?.(message)

          // Invalidate queries based on message type
          switch (message.type) {
            case 'job_started':
            case 'job_running':
            case 'job_completed':
            case 'job_failed':
            case 'job_progress':
              queryClient.invalidateQueries({ queryKey: ['jobs'] })
              queryClient.invalidateQueries({ queryKey: ['jobs-status'] })
              queryClient.invalidateQueries({ queryKey: ['jobs-notifications'] })
              break
            
            case 'data_collected':
              queryClient.invalidateQueries({ queryKey: ['data'] })
              queryClient.invalidateQueries({ queryKey: ['projects'] })
              break
            
            case 'export_completed':
            case 'export_failed':
            case 'export_processing':
              queryClient.invalidateQueries({ queryKey: ['exports'] })
              break
            
            case 'subscribed':
            case 'unsubscribed':
            case 'pong':
              // Acknowledgement messages, no action needed
              break
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      wsRef.current = ws
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
    }
  }, [enabled, onConnect, onDisconnect, onMessage, queryClient])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  const watchJob = useCallback((jobId: string) => {
    sendMessage({ action: 'watch_job', job_id: jobId })
  }, [sendMessage])

  const unwatchJob = useCallback((jobId: string) => {
    sendMessage({ action: 'unwatch_job', job_id: jobId })
  }, [sendMessage])

  const ping = useCallback(() => {
    sendMessage({ action: 'ping' })
  }, [sendMessage])

  // Connect on mount
  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  // Reconnect when enabled changes
  useEffect(() => {
    if (enabled) {
      connect()
    } else {
      disconnect()
    }
  }, [enabled, connect, disconnect])

  // Ping every 30 seconds to keep connection alive
  useEffect(() => {
    if (!isConnected) return
    
    const interval = setInterval(ping, 30000)
    return () => clearInterval(interval)
  }, [isConnected, ping])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    watchJob,
    unwatchJob,
    ping,
  }
}

// Hook for subscribing to specific job updates
export function useJobUpdates(jobId: string | null) {
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState<string | null>(null)
  const [itemsCollected, setItemsCollected] = useState(0)

  const { lastMessage, isConnected, watchJob, unwatchJob } = useRealtime({
    enabled: !!jobId,
    onMessage: (message) => {
      if (message.payload?.job_id === jobId) {
        switch (message.type) {
          case 'job_progress':
            setProgress(message.payload.progress || 0)
            setItemsCollected(message.payload.items_collected || 0)
            break
          case 'job_completed':
            setStatus('completed')
            setProgress(100)
            setItemsCollected(message.payload.items_collected || itemsCollected)
            break
          case 'job_failed':
            setStatus('failed')
            break
          case 'job_started':
          case 'job_running':
            setStatus('running')
            break
        }
      }
    }
  })

  // Watch job when component mounts
  useEffect(() => {
    if (jobId && isConnected) {
      watchJob(jobId)
    }
    
    return () => {
      if (jobId) {
        unwatchJob(jobId)
      }
    }
  }, [jobId, isConnected, watchJob, unwatchJob])

  return {
    isConnected,
    progress,
    status,
    itemsCollected,
  }
}

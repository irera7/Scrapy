import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from './useAuth'

interface WebSocketMessage {
  type: string
  [key: string]: any
}

export function useWebSocket() {
  const { user } = useAuth()
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const messageHandlersRef = useRef<Map<string, (data: any) => void>>(new Map())

  const connect = useCallback(() => {
    if (!user?.id) return

    const wsUrl = `${process.env.NEXT_PUBLIC_API_URL?.replace('http', 'ws') || 'ws://localhost:8099'}/ws/${user.id}`
    
    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        
        // Start ping interval
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'ping' }))
          }
        }, 30000)

        ws.onclose = () => {
          clearInterval(pingInterval)
        }
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          setLastMessage(message)
          
          // Call registered handler for this message type
          const handler = messageHandlersRef.current.get(message.type)
          if (handler) {
            handler(message)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        
        // Reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, 5000)
      }

      wsRef.current = ws
    } catch (e) {
      console.error('Failed to connect WebSocket:', e)
    }
  }, [user?.id])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  const watchJob = useCallback((jobId: string) => {
    send({ action: 'watch_job', job_id: jobId })
  }, [send])

  const unwatchJob = useCallback((jobId: string) => {
    send({ action: 'unwatch_job', job_id: jobId })
  }, [send])

  const onMessage = useCallback((type: string, handler: (data: any) => void) => {
    messageHandlersRef.current.set(type, handler)
    
    return () => {
      messageHandlersRef.current.delete(type)
    }
  }, [])

  return {
    isConnected,
    lastMessage,
    send,
    watchJob,
    unwatchJob,
    onMessage,
  }
}


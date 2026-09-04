import ReconnectingWebSocket from 'reconnecting-websocket'
import { useEffect, useRef } from 'react'

export default function useWebSocket(url = '/ws/events') {
  const wsRef = useRef<any>(null)

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const full = `${protocol}://${host}${url}`
    const rws = new ReconnectingWebSocket(full)
    wsRef.current = rws

    rws.addEventListener('open', () => {
      console.debug('WS connected', full)
    })
    rws.addEventListener('message', (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data)
        // dispatch notification events for certain messages
        if (data.type === 'notification') {
          window.dispatchEvent(new CustomEvent('notify', { detail: { type: data.level || 'info', message: data.message } }))
        }
        // other events can be handled by app state or custom events
        window.dispatchEvent(new CustomEvent('ws:event', { detail: data }))
      } catch (e) {
        console.debug('WS message parse error', e)
      }
    })

    rws.addEventListener('close', () => console.debug('WS closed'))
    return () => {
      rws.close()
    }
  }, [url])

  return wsRef
}

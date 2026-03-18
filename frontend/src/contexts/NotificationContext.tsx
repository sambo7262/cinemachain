import { createContext, useContext, useState, useCallback, useRef } from "react"

interface NotificationContextValue {
  radarrMessage: string | null
  showRadarr: (msg: string) => void
  dismissRadarr: () => void
}

const NotificationContext = createContext<NotificationContextValue | null>(null)

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [radarrMessage, setRadarrMessage] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showRadarr = useCallback((msg: string) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setRadarrMessage(msg)
    timerRef.current = setTimeout(() => setRadarrMessage(null), 5000)
  }, [])

  const dismissRadarr = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = null
    setRadarrMessage(null)
  }, [])

  return (
    <NotificationContext.Provider value={{ radarrMessage, showRadarr, dismissRadarr }}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotification(): NotificationContextValue {
  const ctx = useContext(NotificationContext)
  if (!ctx) throw new Error("useNotification must be used within NotificationProvider")
  return ctx
}

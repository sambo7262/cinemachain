import { X } from "lucide-react"
import { useNotification } from "@/contexts/NotificationContext"

export function RadarrNotificationBanner() {
  const { radarrMessage, dismissRadarr } = useNotification()

  if (!radarrMessage) return null

  return (
    <div className="w-full bg-blue-600 text-white py-3 px-4 flex items-center justify-between">
      <span className="text-sm font-medium">{radarrMessage}</span>
      <button
        onClick={dismissRadarr}
        className="flex-shrink-0 ml-4 text-white/80 hover:text-white transition-colors"
        aria-label="Dismiss notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

import { Link, useLocation } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Film } from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"

export function NavBar() {
  const location = useLocation()
  const { data: activeSession } = useQuery({
    queryKey: ["activeSession"],
    queryFn: api.getActiveSession,
    staleTime: 0,
    refetchInterval: 10000,
  })

  const sessionHref = activeSession?.id ? `/game/${activeSession.id}` : "/"
  // The Sessions link is "active" when we are on GameLobby (/) OR on the active session page
  const isSessionsActive =
    location.pathname === "/" ||
    (activeSession?.id != null && location.pathname === `/game/${activeSession.id}`)

  return (
    <nav className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
      <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo / wordmark */}
        <Link
          to="/"
          className="flex items-center gap-2 font-bold text-lg tracking-tight hover:text-primary transition-colors"
        >
          <Film className="w-5 h-5" />
          CinemaChain
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          <Link
            to={sessionHref}
            className={cn(
              "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              isSessionsActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
            )}
          >
            Sessions
          </Link>
        </div>
      </div>
    </nav>
  )
}

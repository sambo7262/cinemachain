import { Link, useLocation } from "react-router-dom"
import { Film } from "lucide-react"
import { cn } from "@/lib/utils"

export function NavBar() {
  const location = useLocation()

  const isSessionsActive = location.pathname === "/" || location.pathname.startsWith("/game/")
  const isArchivedActive = location.pathname === "/archived"

  return (
    <nav className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
      <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center justify-between">
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
            to="/"
            className={cn(
              "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              isSessionsActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
            )}
          >
            Sessions
          </Link>
          <Link
            to="/archived"
            className={cn(
              "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              isArchivedActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
            )}
          >
            Archived
          </Link>
        </div>
      </div>
    </nav>
  )
}

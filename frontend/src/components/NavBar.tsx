import { Link, useLocation } from "react-router-dom"
import { Film, Settings as SettingsIcon } from "lucide-react"
import { cn } from "@/lib/utils"

export function NavBar() {
  const location = useLocation()

  const isGameModeActive = location.pathname === "/game" || location.pathname.startsWith("/game/")
  const isSearchActive = location.pathname === "/search"
  const isWatchHistoryActive = location.pathname === "/watched"

  return (
    <nav className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
      <div className="max-w-[1400px] mx-auto px-2 sm:px-3 h-14 flex items-center justify-between">
        {/* Logo / wordmark — hidden on very small screens to free space */}
        <Link
          to="/game"
          className="hidden sm:flex items-center gap-2 font-bold text-lg tracking-tight hover:text-primary transition-colors"
        >
          <Film className="w-5 h-5" />
          CinemaChain
        </Link>
        {/* Icon-only logo on small screens */}
        <Link to="/game" className="sm:hidden flex items-center text-foreground hover:text-primary transition-colors">
          <Film className="w-5 h-5" />
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-0.5 sm:gap-1">
          <Link
            to="/game"
            className={cn(
              "px-2 py-1 rounded-md text-xs sm:px-3 sm:py-1.5 sm:text-sm font-medium transition-colors",
              isGameModeActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
            )}
          >
            Game Mode
          </Link>
          <Link
            to="/search"
            className={cn(
              "px-2 py-1 rounded-md text-xs sm:px-3 sm:py-1.5 sm:text-sm font-medium transition-colors",
              isSearchActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
            )}
          >
            Search
          </Link>
          <Link
            to="/watched"
            className={cn(
              "px-2 py-1 rounded-md text-xs sm:px-3 sm:py-1.5 sm:text-sm font-medium transition-colors",
              isWatchHistoryActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
            )}
          >
            Watch History
          </Link>
          <Link
            to="/settings"
            aria-label="Settings"
            className="min-w-[44px] min-h-[44px] flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
          >
            <SettingsIcon className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </nav>
  )
}

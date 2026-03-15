import { Link, useLocation } from "react-router-dom"
import { Film } from "lucide-react"
import { cn } from "@/lib/utils"

export function NavBar() {
  const location = useLocation()

  const links = [
    { to: "/", label: "Sessions" },
  ]

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
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={cn(
                "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                location.pathname === link.to
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
              )}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  )
}

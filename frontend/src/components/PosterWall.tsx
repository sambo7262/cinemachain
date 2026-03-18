import type { PosterWallItem } from "@/lib/api"
import { cn } from "@/lib/utils"

interface PosterWallProps {
  posters: PosterWallItem[]
}

/** Returns the display URL for a poster item, or null when both paths are absent.
 * poster_local_path is stored as "/static/posters/{id}.jpg" on the backend.
 * nginx proxies /api/ to backend:8000/ so the frontend accesses it as "/api/static/posters/{id}.jpg".
 */
function posterUrl(item: PosterWallItem): string | null {
  if (item.poster_local_path) {
    return `/api${item.poster_local_path}`
  }
  if (item.poster_path) {
    return `https://image.tmdb.org/t/p/w185${item.poster_path}`
  }
  return null  // Both paths absent — skip this poster
}

/** Distributes an array round-robin into `count` columns. */
function distributeColumns<T>(items: T[], count: number): T[][] {
  const cols: T[][] = Array.from({ length: count }, () => [])
  items.forEach((item, i) => cols[i % count].push(item))
  return cols
}

export function PosterWall({ posters }: PosterWallProps) {
  // Filter to only posters with renderable URLs before any layout logic
  const renderablePosters = posters.filter((p) => p.poster_local_path || p.poster_path)

  // Fallback: fewer than 5 renderable posters → render nothing; caller keeps bg-background
  if (renderablePosters.length < 5) return null

  // Responsive column counts: 4 on lg+, 3 on md, 2 on sm
  // Use CSS grid/flex — column count per breakpoint handled via Tailwind classes on children
  // Simple approach: always build 4 columns; hide col 3+4 on smaller viewports via CSS
  const allColumns = distributeColumns(renderablePosters, 4)

  return (
    <div className="fixed inset-0 z-[1] overflow-hidden" aria-hidden="true">
      {/* Dark overlay — must be above poster columns */}
      <div className="absolute inset-0 bg-black/80 z-10" />

      {/* Poster columns container */}
      <div className="flex h-full">
        {allColumns.map((col, i) => {
          if (col.length === 0) return null
          const isUp = i % 2 === 0  // columns 0, 2 scroll up; columns 1, 3 scroll down
          const duplicated = [...col, ...col]  // duplicate for seamless loop

          return (
            <div
              key={i}
              className={cn(
                // Responsive visibility: show 2 cols on sm, 3 on md, 4 on lg
                i === 0 ? "flex" : i === 1 ? "flex" : i === 2 ? "hidden md:flex" : "hidden lg:flex",
                "flex-1 flex-col",
                isUp ? "animate-poster-up" : "animate-poster-down",
                // Apply blur to the column container — NOT individual images (NAS GPU optimization)
                "blur-[20px]",
              )}
              style={{ willChange: "transform" }}
            >
              {duplicated.map((poster, j) => {
                const url = posterUrl(poster)
                if (!url) return null
                return (
                  <img
                    key={j}
                    src={url}
                    alt=""
                    className="w-full object-cover bg-muted"
                    loading="lazy"
                    onError={(e) => {
                      // Hide broken images rather than showing broken image icon
                      ;(e.target as HTMLImageElement).style.display = "none"
                    }}
                  />
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}

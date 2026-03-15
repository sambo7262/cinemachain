import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Star } from "lucide-react"
import { cn } from "@/lib/utils"

interface MovieCardProps {
  tmdb_id: number
  title: string
  year: number | null
  poster_path: string | null
  vote_average?: number | null
  genres?: string | null
  runtime?: number | null
  watched?: boolean
  selectable?: boolean
  via_actor_name?: string | null
  onClick?: () => void
}

const TMDB_IMG = "https://image.tmdb.org/t/p/w342"

export function MovieCard({
  title,
  year,
  poster_path,
  vote_average,
  genres,
  runtime,
  watched,
  selectable,
  via_actor_name,
  onClick,
}: MovieCardProps) {
  const poster = poster_path ? `${TMDB_IMG}${poster_path}` : null
  const genreList: string[] = genres
    ? (() => {
        try {
          return JSON.parse(genres) as string[]
        } catch {
          return []
        }
      })()
    : []
  const isClickable = selectable !== false && !!onClick

  return (
    <Card
      className={cn(
        "flex gap-3 p-3 transition-colors",
        isClickable && "cursor-pointer hover:bg-accent",
        !isClickable && "opacity-50 cursor-not-allowed",
      )}
      onClick={isClickable ? onClick : undefined}
    >
      {poster ? (
        <img
          src={poster}
          alt={title}
          className="w-16 h-24 rounded object-cover flex-shrink-0"
        />
      ) : (
        <div className="w-16 h-24 rounded bg-muted flex-shrink-0" />
      )}
      <CardContent className="p-0 flex flex-col gap-1">
        <p className="text-lg font-semibold leading-tight">{title}</p>
        <p className="text-sm text-muted-foreground">
          {year ?? ""}
          {runtime ? ` · ${runtime}m` : ""}
        </p>
        {vote_average != null && (
          <span className="flex items-center gap-1 text-sm text-amber-400">
            <Star className="w-3 h-3 fill-current" /> {vote_average.toFixed(1)}
          </span>
        )}
        <div className="flex flex-wrap gap-1 mt-1">
          {genreList.slice(0, 3).map((g) => (
            <Badge key={g} variant="secondary" className="text-xs">
              {g}
            </Badge>
          ))}
          {watched && (
            <Badge
              variant="outline"
              className="text-xs text-green-400 border-green-400"
            >
              Watched
            </Badge>
          )}
        </div>
        {via_actor_name && (
          <p className="text-xs text-muted-foreground italic mt-1">
            via {via_actor_name}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

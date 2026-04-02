import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Star, LayoutList, LayoutGrid } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { api, WatchedMovieDTO } from "@/lib/api"
import { RatingsBadge } from "@/components/RatingsBadge"
import { RatingSlider } from "@/components/RatingSlider"

// ---- Helpers ------------------------------------------------------------------

function formatWatchedAt(iso: string): string {
  if (!iso) return "Unknown"
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  } catch {
    return iso
  }
}

function parseGenres(genres: string | null): string[] {
  if (!genres) return []
  try {
    return JSON.parse(genres)
  } catch {
    return []
  }
}

// ---- Constants ----------------------------------------------------------------

const SORT_OPTIONS = [
  { value: "title:asc",            label: "Title A\u2192Z" },
  { value: "title:desc",           label: "Title Z\u2192A" },
  { value: "year:desc",            label: "Year (newest)" },
  { value: "year:asc",             label: "Year (oldest)" },
  { value: "runtime:desc",         label: "Runtime (longest)" },
  { value: "runtime:asc",          label: "Runtime (shortest)" },
  { value: "rating:desc",          label: "TMDB Rating (highest)" },
  { value: "rt:desc",              label: "RT Score (highest)" },
  { value: "watched_at:desc",      label: "Watched Date (newest)" },
  { value: "watched_at:asc",       label: "Watched Date (oldest)" },
  { value: "personal_rating:desc", label: "Personal Rating (highest)" },
]

// ---- Component ----------------------------------------------------------------

export default function WatchHistoryPage() {
  const [view, setView] = useState<"list" | "tile">("list")
  const [searchInput, setSearchInput] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [sortCol, setSortCol] = useState("title")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [page, setPage] = useState(1)
  const [splashMovie, setSplashMovie] = useState<WatchedMovieDTO | null>(null)
  const [splashOpen, setSplashOpen] = useState(false)
  const [localSaved, setLocalSaved] = useState(false)
  const queryClient = useQueryClient()

  // --- Debounce 300ms ---
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(t)
  }, [searchInput])

  // --- Reset page on search/sort changes ---
  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, sortCol, sortDir])

  // --- Reset localSaved when splash opens ---
  useEffect(() => {
    setLocalSaved(false)
  }, [splashMovie])

  // --- Data query ---
  const { data, isLoading, isError } = useQuery({
    queryKey: ["watchedHistory", { sort: sortCol, sort_dir: sortDir, search: debouncedSearch, page }],
    queryFn: () =>
      api.getWatchedHistory({
        sort: sortCol,
        sort_dir: sortDir,
        search: debouncedSearch,
        page,
        page_size: 24,
      }),
  })

  // --- Rating mutation ---
  const ratingMutation = useMutation({
    mutationFn: ({ tmdbId, rating }: { tmdbId: number; rating: number }) =>
      api.setMovieRating(tmdbId, rating),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchedHistory"] })
    },
  })

  // --- Save/unsave mutation ---
  const saveMutation = useMutation({
    mutationFn: ({ tmdbId, saved }: { tmdbId: number; saved: boolean }) =>
      saved ? api.saveMovieGlobal(tmdbId) : api.unsaveMovieGlobal(tmdbId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchedHistory"] }),
  })

  // --- Sort helpers ---
  const currentSortValue = `${sortCol}:${sortDir}`

  function handleSortChange(value: string) {
    const [col, dir] = value.split(":")
    setSortCol(col)
    setSortDir(dir as "asc" | "desc")
  }

  // ---- Render ------------------------------------------------------------------

  return (
    <div className="py-4 sm:py-6 space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <Input
          placeholder="Search by title..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="max-w-xs"
        />
        <Select value={currentSortValue} onValueChange={handleSortChange}>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Sort by..." />
          </SelectTrigger>
          <SelectContent>
            {SORT_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-1">
          <Button
            variant={view === "list" ? "default" : "outline"}
            size="sm"
            aria-label="List view"
            onClick={() => setView("list")}
          >
            <LayoutList className="w-4 h-4" />
          </Button>
          <Button
            variant={view === "tile" ? "default" : "outline"}
            size="sm"
            aria-label="Tile view"
            onClick={() => setView("tile")}
          >
            <LayoutGrid className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Content area */}
      {isLoading && (
        <p className="text-muted-foreground">Loading...</p>
      )}

      {isError && (
        <p className="text-destructive">Failed to load watch history.</p>
      )}

      {!isLoading && !isError && data && data.total === 0 && (
        <p className="text-muted-foreground">No watched movies yet.</p>
      )}

      {!isLoading && !isError && data && data.total > 0 && (
        <>
          {/* List view */}
          {view === "list" && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/50 text-muted-foreground">
                    <th className="w-12 p-2" scope="col"></th>
                    <th className="p-2 text-left" scope="col">Title</th>
                    <th className="p-2 text-left" scope="col">Year</th>
                    <th className="p-2 text-left" scope="col">Runtime</th>
                    <th className="hidden sm:table-cell p-2 text-left" scope="col">Genres</th>
                    <th className="p-2 text-left" scope="col">Ratings</th>
                    <th className="p-2 text-left" scope="col">Watched</th>
                    <th className="p-2 text-left" scope="col">Your Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((m) => (
                    <tr
                      key={m.tmdb_id}
                      className="border-b border-border hover:bg-accent/30 cursor-pointer"
                      onClick={() => {
                        setSplashMovie(m)
                        setSplashOpen(true)
                      }}
                    >
                      <td className="p-2 w-12">
                        {m.poster_path ? (
                          <img
                            src={`https://image.tmdb.org/t/p/w92${m.poster_path}`}
                            alt={m.title}
                            className="w-10 h-[3.75rem] object-cover rounded"
                          />
                        ) : (
                          <div className="w-10 h-[3.75rem] bg-muted rounded flex items-center justify-center text-xs text-muted-foreground">
                            —
                          </div>
                        )}
                      </td>
                      <td className="p-2 font-medium">{m.title}</td>
                      <td className="p-2">{m.year ?? "—"}</td>
                      <td className="p-2">{m.runtime ? `${m.runtime}m` : "—"}</td>
                      <td className="hidden sm:table-cell p-2 text-muted-foreground">
                        {parseGenres(m.genres).join(" · ") || "—"}
                      </td>
                      <td className="p-2">
                        <RatingsBadge variant="card" ratings={m} />
                      </td>
                      <td className="p-2 text-muted-foreground">
                        {formatWatchedAt(m.watched_at)}
                      </td>
                      <td className="p-2">
                        {m.personal_rating != null ? (
                          <span
                            className="inline-flex items-center gap-0.5 text-xs"
                            aria-label={`Personal rating: ${m.personal_rating}/10`}
                          >
                            <Star className="w-3 h-3 fill-current text-amber-400" />
                            <span>{m.personal_rating}/10</span>
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Tile view */}
          {view === "tile" && (
            <div className="grid grid-cols-3 gap-3">
              {data.items.map((m) => (
                <div
                  key={m.tmdb_id}
                  className="cursor-pointer rounded-lg overflow-hidden border hover:border-primary transition-colors"
                  onClick={() => {
                    setSplashMovie(m)
                    setSplashOpen(true)
                  }}
                >
                  {m.poster_path ? (
                    <img
                      src={`https://image.tmdb.org/t/p/w342${m.poster_path}`}
                      alt={m.title}
                      className="w-full aspect-[2/3] object-cover"
                    />
                  ) : (
                    <div className="w-full aspect-[2/3] bg-muted flex items-center justify-center text-xs text-muted-foreground">
                      No poster
                    </div>
                  )}
                  <div className="p-2 space-y-1">
                    <p className="font-medium text-sm line-clamp-1">{m.title}</p>
                    <p className="text-xs text-muted-foreground">{m.year ?? "—"}</p>
                    <RatingsBadge variant="tile" ratings={m} />
                    <p className="text-xs text-muted-foreground">
                      {formatWatchedAt(m.watched_at)}
                    </p>
                    {m.personal_rating != null && (
                      <span
                        className="inline-flex items-center gap-0.5 text-xs"
                        aria-label={`Personal rating: ${m.personal_rating}/10`}
                      >
                        <Star className="w-3 h-3 fill-current text-amber-400" />
                        <span>{m.personal_rating}/10</span>
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          <div className="flex items-center gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {data.page} of {Math.max(1, Math.ceil(data.total / 24))}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={!data.has_more}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </>
      )}

      {/* Splash dialog */}
      <Dialog open={splashOpen} onOpenChange={setSplashOpen}>
        <DialogContent className="max-w-2xl">
          {splashMovie && (
            <>
              <DialogHeader>
                <DialogTitle>{splashMovie.title}</DialogTitle>
                <DialogDescription>{splashMovie.year ?? ""}</DialogDescription>
              </DialogHeader>
              <div className="flex gap-4">
                {splashMovie.poster_path ? (
                  <img
                    src={`https://image.tmdb.org/t/p/w185${splashMovie.poster_path}`}
                    alt={splashMovie.title}
                    className="w-32 rounded object-cover shrink-0"
                  />
                ) : (
                  <div className="w-32 h-48 bg-muted rounded flex items-center justify-center text-xs text-muted-foreground shrink-0">
                    No poster
                  </div>
                )}
                <div className="flex-1 space-y-3 min-w-0">
                  <p className="text-sm text-muted-foreground line-clamp-4">
                    {splashMovie.overview ?? "No overview available."}
                  </p>
                  <RatingsBadge variant="splash" ratings={splashMovie} />
                  {splashMovie.personal_rating != null && (
                    <span
                      className="inline-flex items-center gap-0.5 text-xs"
                      aria-label={`Personal rating: ${splashMovie.personal_rating}/10`}
                    >
                      <Star className="w-3 h-3 fill-current text-amber-400" />
                      <span>{splashMovie.personal_rating}/10</span>
                    </span>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Watched: {formatWatchedAt(splashMovie.watched_at)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {splashMovie.runtime ? `${splashMovie.runtime} min` : ""}
                    {splashMovie.mpaa_rating ? ` ${splashMovie.mpaa_rating}` : ""}
                  </p>
                </div>
              </div>
              <RatingSlider
                movieTitle={splashMovie.title}
                posterPath={splashMovie.poster_path}
                currentRating={splashMovie.personal_rating ?? null}
                onSave={(rating) => ratingMutation.mutate({ tmdbId: splashMovie.tmdb_id, rating })}
                onSkip={() => setSplashOpen(false)}
                isPending={ratingMutation.isPending}
              />
              <DialogFooter className="pt-0">
                <Button
                  size="sm"
                  variant={localSaved ? "default" : "outline"}
                  onClick={() => {
                    const newSaved = !localSaved
                    setLocalSaved(newSaved)
                    saveMutation.mutate({ tmdbId: splashMovie!.tmdb_id, saved: newSaved })
                  }}
                >
                  <Star className={cn("w-4 h-4 mr-1", localSaved ? "fill-current" : "")} />
                  {localSaved ? "Saved" : "Save"}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

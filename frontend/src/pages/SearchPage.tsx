import { useState, useEffect, useMemo } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { X } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { api, EligibleMovieDTO } from "@/lib/api"
import { RatingsBadge } from "@/components/RatingsBadge"
import { RatingSlider } from "@/components/RatingSlider"
import { MovieFilterSidebar, FilterState, DEFAULT_FILTER_STATE } from "@/components/MovieFilterSidebar"

// ---- Constants ----------------------------------------------------------------

const GENRE_CHIPS = [
  { label: "Action",           id: 28    },
  { label: "Adventure",        id: 12    },
  { label: "Animation",        id: 16    },
  { label: "Comedy",           id: 35    },
  { label: "Crime",            id: 80    },
  { label: "Documentary",      id: 99    },
  { label: "Drama",            id: 18    },
  { label: "Fantasy",          id: 14    },
  { label: "Horror",           id: 27    },
  { label: "Romance",          id: 10749 },
  { label: "Science Fiction",  id: 878   },
  { label: "Thriller",         id: 53    },
  { label: "History",          id: 36    },
  { label: "Music",            id: 10402 },
] as const

// ---- Helpers ------------------------------------------------------------------

function parseGenres(genres: string | null): string[] {
  if (!genres) return []
  try { return JSON.parse(genres) } catch { return [] }
}

function parseSearchMode(input: string): { mode: "title" | "person"; query: string } {
  if (input.startsWith("a:") || input.startsWith("d:")) {
    return { mode: "person", query: input.slice(2).trim() }
  }
  if (input.startsWith("m:")) {
    return { mode: "title", query: input.slice(2).trim() }
  }
  return { mode: "title", query: input.trim() }
}

// ---- Component ----------------------------------------------------------------

export default function SearchPage() {
  // --- Search input state ---
  const [searchInput, setSearchInput]         = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")

  // --- Genre browse state ---
  const [activeGenreId, setActiveGenreId]       = useState<number | null>(null)
  const [activeGenreLabel, setActiveGenreLabel] = useState<string | null>(null)

  // --- Sort state ---
  const [sortCol, setSortCol] = useState<"rating" | "year" | "runtime" | "rt">("rating")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")

  // --- Toggle: all vs unwatched ---
  const [allMovies, setAllMovies] = useState(true)

  // --- Pagination ---
  const [page, setPage] = useState(1)
  const PAGE_SIZE       = 20

  // --- Sidebar filters ---
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTER_STATE)

  // --- Splash dialog ---
  const [splashMovie, setSplashMovie]       = useState<EligibleMovieDTO | null>(null)
  const [splashOpen, setSplashOpen]         = useState(false)
  const [radarrStatus, setRadarrStatus]       = useState<string | null>(null)
  const [radarrLoading, setRadarrLoading]     = useState(false)
  const [watchedLoading, setWatchedLoading]   = useState(false)

  // --- Rating dialog ---
  const [ratingDialogOpen, setRatingDialogOpen] = useState(false)
  const [ratingTmdbId, setRatingTmdbId]         = useState<number | null>(null)

  // --- Debounce effect (300ms) ---
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(t)
  }, [searchInput])

  // --- Derive search mode and query ---
  const { mode: searchMode, query: searchQuery } = useMemo(
    () => parseSearchMode(debouncedSearch),
    [debouncedSearch]
  )

  // --- Sort helpers (ported from GameSession) ---
  const handleSortClick = (col: "rating" | "year" | "runtime" | "rt") => {
    if (col === sortCol) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortCol(col)
      setSortDir("desc")
    }
  }

  const sortIndicator = (col: "rating" | "year" | "runtime" | "rt") =>
    sortCol === col ? (sortDir === "asc" ? " ↑" : " ↓") : ""

  // --- Data queries ---
  const { data: titleResults = [], isFetching: titleFetching } = useQuery({
    queryKey: ["searchMovies", searchQuery],
    queryFn:  () => api.searchMovies(searchQuery),
    enabled:  searchMode === "title" && searchQuery.length >= 2,
    staleTime: 30_000,
  })

  const { data: actorResults = [], isFetching: actorFetching } = useQuery({
    queryKey: ["searchActors", searchQuery],
    queryFn:  () => api.searchActors(searchQuery),
    enabled:  searchMode === "person" && searchQuery.length >= 2,
    staleTime: 30_000,
  })

  const { data: genreResults = [], isFetching: genreFetching } = useQuery({
    queryKey: ["popularByGenre", activeGenreId],
    queryFn:  () => api.getPopularByGenre(activeGenreId!),
    enabled:  !!activeGenreId && debouncedSearch.length === 0,
    staleTime: 60_000,
  })

  // --- Unified raw results ---
  const rawResults: EligibleMovieDTO[] = useMemo(() => {
    if (activeGenreId !== null && debouncedSearch.length === 0) return genreResults
    if (searchMode === "person") return actorResults
    return titleResults
  }, [activeGenreId, debouncedSearch, searchMode, titleResults, actorResults, genreResults])

  const isLoading = titleFetching || actorFetching || genreFetching

  // --- Derive available genres from results (for sidebar) ---
  const availableGenres = useMemo(() => {
    const genreSet = new Set<string>()
    rawResults.forEach((m) => parseGenres(m.genres).forEach((g) => genreSet.add(g)))
    return Array.from(genreSet).sort()
  }, [rawResults])

  // --- Filter + sort + paginate pipeline ---
  const sortedAndFiltered = useMemo(() => {
    // 1. Watched filter
    const watched = allMovies
      ? rawResults
      : rawResults.filter((m) => !m.watched)

    // 2. Genre filter
    const genreFiltered =
      filters.genres.length > 0
        ? watched.filter((m) =>
            parseGenres(m.genres).some((g) => filters.genres.includes(g))
          )
        : watched

    // 3. MPAA filter
    const mpaaFiltered =
      filters.mpaaRatings.length > 0
        ? genreFiltered.filter((m) =>
            filters.mpaaRatings.includes(m.mpaa_rating ?? "NR")
          )
        : genreFiltered

    // 4. Runtime filter
    const runtimeFiltered = mpaaFiltered.filter(
      (m) =>
        m.runtime == null ||
        (m.runtime >= filters.runtimeRange[0] && m.runtime <= filters.runtimeRange[1])
    )

    // 5. Null-stable two-pass sort (ported exactly from GameSession.tsx)
    const sorted = [...runtimeFiltered].sort((a, b) => {
      const getVal = (m: EligibleMovieDTO) => {
        if (sortCol === "rating")  return m.vote_average
        if (sortCol === "year")    return m.year
        if (sortCol === "runtime") return m.runtime
        if (sortCol === "rt")      return m.rt_score
        return null
      }
      const aVal = getVal(a)
      const bVal = getVal(b)
      // Nulls always last regardless of direction
      if (aVal == null && bVal == null) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1
      return sortDir === "asc" ? aVal - bVal : bVal - aVal
    })

    return sorted
  }, [rawResults, allMovies, filters, sortCol, sortDir])

  const totalPages = Math.max(1, Math.ceil(sortedAndFiltered.length / PAGE_SIZE))
  const paginated  = sortedAndFiltered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // --- Reset page on filter/sort change ---
  useEffect(() => {
    setPage(1)
  }, [sortCol, sortDir, allMovies, filters, activeGenreId, debouncedSearch])

  const ratingMutation = useMutation({
    mutationFn: ({ tmdbId, rating }: { tmdbId: number; rating: number }) =>
      api.setMovieRating(tmdbId, rating),
    onSuccess: () => {
      setRatingDialogOpen(false)
      setRatingTmdbId(null)
    },
  })

  const handleMarkWatched = async () => {
    if (!splashMovie) return
    setWatchedLoading(true)
    try {
      await api.markWatchedOnline(splashMovie.tmdb_id)
      setRadarrStatus("watched")
      // Open rating dialog after marking watched
      setRatingTmdbId(splashMovie.tmdb_id)
      setRatingDialogOpen(true)
    } catch {
      setRadarrStatus("error")
    } finally {
      setWatchedLoading(false)
    }
  }

  // ---- Render ------------------------------------------------------------------

  const showResults = activeGenreId !== null || debouncedSearch.length >= 2

  return (
    <>
      <div className="py-4 sm:py-6">
        {/* Search input row */}
        <div className="relative">
          <Input
            aria-label="Search movies, actors, or directors"
            placeholder='Search movies... or "a: Tom Hanks" for filmography'
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value)
              setActiveGenreId(null)
              setActiveGenreLabel(null)
            }}
            className="pr-8"
          />
          {searchInput && (
            <button
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
              onClick={() => {
                setSearchInput("")
                setDebouncedSearch("")
              }}
            >
              <X size={14} />
            </button>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          m: title &nbsp;&middot;&nbsp; a: actor &nbsp;&middot;&nbsp; d: director
        </p>

        {/* Landing state: genre chips */}
        {!activeGenreId && debouncedSearch.length === 0 && (
          <div className="mt-6">
            <h2 className="text-base font-semibold mb-3">Browse by Genre</h2>
            <div className="flex flex-wrap gap-2">
              {GENRE_CHIPS.map((g) => (
                <Button
                  key={g.id}
                  variant="outline"
                  size="sm"
                  aria-label={`${g.label} movies`}
                  onClick={() => {
                    setSearchInput("")
                    setDebouncedSearch("")
                    setActiveGenreId(g.id)
                    setActiveGenreLabel(g.label)
                    setPage(1)
                  }}
                >
                  {g.label}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Results area */}
        {showResults && (
          <div className="mt-6 flex gap-4">
            {/* Filter sidebar (desktop only) */}
            <div className="w-[200px] shrink-0 hidden lg:block">
              <MovieFilterSidebar
                genres={availableGenres}
                filters={filters}
                onChange={setFilters}
              />
            </div>

            {/* Results table column */}
            <div className="flex-1 min-w-0">
              {/* Header row: active genre chip + result count + watched toggle */}
              <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
                <div className="flex items-center gap-2">
                  {activeGenreId && (
                    <Button
                      variant="default"
                      size="sm"
                      className={genreFetching ? "animate-pulse" : ""}
                      onClick={() => {
                        setActiveGenreId(null)
                        setActiveGenreLabel(null)
                      }}
                    >
                      {activeGenreLabel} &times;
                    </Button>
                  )}
                  <span className="text-sm text-muted-foreground">
                    {sortedAndFiltered.length} result{sortedAndFiltered.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant={allMovies ? "default" : "outline"}
                    size="sm"
                    aria-pressed={allMovies}
                    onClick={() => setAllMovies(true)}
                  >
                    All
                  </Button>
                  <Button
                    variant={!allMovies ? "default" : "outline"}
                    size="sm"
                    aria-pressed={!allMovies}
                    onClick={() => setAllMovies(false)}
                  >
                    Unwatched Only
                  </Button>
                </div>
              </div>

              {/* Loading skeleton */}
              {isLoading && (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-[72px] rounded bg-muted animate-pulse" />
                  ))}
                </div>
              )}

              {/* Results table */}
              {!isLoading && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-muted/50 text-muted-foreground">
                        <th className="w-12 p-2" scope="col"></th>
                        <th className="p-2 text-left" scope="col">Title</th>
                        <th
                          className="p-2 text-left cursor-pointer select-none"
                          scope="col"
                          aria-sort={
                            sortCol === "year"
                              ? sortDir === "asc" ? "ascending" : "descending"
                              : "none"
                          }
                          onClick={() => handleSortClick("year")}
                        >
                          Year{sortIndicator("year")}
                        </th>
                        <th className="p-2 text-left" scope="col">Ratings</th>
                        <th className="p-2 text-left" scope="col">MPAA</th>
                        <th
                          className="p-2 text-left cursor-pointer select-none"
                          scope="col"
                          aria-sort={
                            sortCol === "runtime"
                              ? sortDir === "asc" ? "ascending" : "descending"
                              : "none"
                          }
                          onClick={() => handleSortClick("runtime")}
                        >
                          Runtime{sortIndicator("runtime")}
                        </th>
                        <th className="p-2 text-left" scope="col">Genres</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginated.length === 0 && (
                        <tr>
                          <td colSpan={8} className="py-8 text-center text-sm text-muted-foreground">
                            {activeGenreId
                              ? "No popular movies found for this genre right now."
                              : searchMode === "person"
                              ? `No person found for "${searchQuery}". Check the spelling and try again.`
                              : `No movies found for "${searchQuery}". Try a different title or name.`}
                          </td>
                        </tr>
                      )}
                      {paginated.map((movie) => (
                        <tr
                          key={movie.tmdb_id}
                          className="border-b border-border hover:bg-accent/50 cursor-pointer"
                          onClick={() => {
                            setSplashMovie(movie)
                            setSplashOpen(true)
                            setRadarrStatus(null)
                          }}
                        >
                          <td className="p-2 w-12">
                            {movie.poster_path ? (
                              <img
                                src={`https://image.tmdb.org/t/p/w92${movie.poster_path}`}
                                alt={movie.title}
                                className="w-12 h-[4.5rem] object-cover rounded"
                              />
                            ) : (
                              <div className="w-12 h-[4.5rem] bg-muted rounded flex items-center justify-center text-xs text-muted-foreground">
                                No poster
                              </div>
                            )}
                          </td>
                          <td className="p-2">
                            <span className="font-medium">{movie.title}</span>
                            {movie.watched && (
                              <Badge
                                variant="outline"
                                className="ml-2 text-green-400 border-green-400 text-xs"
                              >
                                Watched
                              </Badge>
                            )}
                          </td>
                          <td className="p-2">{movie.year ?? "—"}</td>
                          <td className="p-2">
                            <RatingsBadge variant="card" ratings={movie} />
                          </td>
                          <td className="p-2">{movie.mpaa_rating ?? "—"}</td>
                          <td className="p-2">
                            {movie.runtime != null ? `${movie.runtime}m` : "—"}
                          </td>
                          <td className="p-2 text-muted-foreground">
                            {parseGenres(movie.genres).join(" · ") || "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Movie splash dialog */}
      <Dialog
        open={splashOpen}
        onOpenChange={(open) => {
          setSplashOpen(open)
          if (!open) {
            setRadarrStatus(null)
            setRadarrLoading(false)
            setWatchedLoading(false)
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          {splashMovie && (
            <>
              <DialogHeader>
                <DialogTitle>{splashMovie.title}</DialogTitle>
                <DialogDescription>
                  {splashMovie.year ?? "Unknown year"}
                  {splashMovie.mpaa_rating ? ` · ${splashMovie.mpaa_rating}` : ""}
                </DialogDescription>
              </DialogHeader>
              <div className="flex gap-4">
                {splashMovie.poster_path ? (
                  <img
                    src={`https://image.tmdb.org/t/p/w185${splashMovie.poster_path}`}
                    alt={splashMovie.title}
                    className="w-32 rounded-md object-cover shrink-0"
                  />
                ) : (
                  <div className="w-32 h-48 bg-muted rounded-md flex items-center justify-center text-xs text-muted-foreground shrink-0">
                    No poster
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap gap-2 mb-3">
                    <RatingsBadge variant="splash" ratings={splashMovie} />
                    {splashMovie.mpaa_rating && (
                      <Badge variant="outline">{splashMovie.mpaa_rating}</Badge>
                    )}
                    {splashMovie.runtime != null && (
                      <Badge variant="outline">{splashMovie.runtime}m</Badge>
                    )}
                    {splashMovie.year && (
                      <Badge variant="outline">{splashMovie.year}</Badge>
                    )}
                  </div>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {splashMovie.overview ?? "No overview available."}
                  </p>
                  {splashMovie.tmdb_id && (
                    <a
                      href={splashMovie.imdb_id ? `https://www.imdb.com/title/${splashMovie.imdb_id}` : `https://www.themoviedb.org/movie/${splashMovie.tmdb_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-muted-foreground underline mt-2 inline-block"
                      aria-label={splashMovie.imdb_id ? `View ${splashMovie.title} on IMDB (opens in new tab)` : `View ${splashMovie.title} on TMDB (opens in new tab)`}
                    >
                      {splashMovie.imdb_id ? "View on IMDB" : "View on TMDB"}
                    </a>
                  )}
                </div>
              </div>
              <DialogFooter className="flex gap-2 flex-wrap">
                {radarrStatus === "error" && (
                  <p className="text-sm text-destructive w-full">
                    Request failed. Try again or check Radarr.
                  </p>
                )}
                <Button
                  variant="default"
                  disabled={radarrLoading || watchedLoading}
                  onClick={async () => {
                    setRadarrLoading(true)
                    try {
                      const result = await api.requestMovieStandalone(splashMovie.tmdb_id)
                      if (result.status === "queued") {
                        setRadarrStatus("queued")
                        setTimeout(() => setRadarrStatus(null), 2000)
                      } else if (result.status === "already_in_radarr") {
                        setRadarrStatus("already_in_radarr")
                        // NO setTimeout — stays until dialog is closed
                      } else {
                        setRadarrStatus("error")
                      }
                    } catch {
                      setRadarrStatus("error")
                    } finally {
                      setRadarrLoading(false)
                    }
                  }}
                >
                  {radarrLoading
                    ? "Requesting..."
                    : radarrStatus === "queued"
                    ? "Added to Radarr"
                    : radarrStatus === "already_in_radarr"
                    ? "Already in Radarr"
                    : "Download via Radarr"}
                </Button>
                <Button
                  variant="outline"
                  disabled={radarrLoading || watchedLoading}
                  onClick={handleMarkWatched}
                >
                  {watchedLoading
                    ? "Saving..."
                    : radarrStatus === "watched"
                    ? "Marked as Watched"
                    : "Watch Online"}
                </Button>
                <Button variant="outline" onClick={() => setSplashOpen(false)}>
                  Close
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Rating Dialog — appears after Watch Online (Mark as Watched) */}
      <Dialog open={ratingDialogOpen} onOpenChange={setRatingDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Rate this movie</DialogTitle>
          </DialogHeader>
          <RatingSlider
            movieTitle={splashMovie?.title ?? ""}
            posterPath={splashMovie?.poster_path ?? null}
            currentRating={null}
            onSave={(rating) => ratingMutation.mutate({ tmdbId: ratingTmdbId!, rating })}
            onSkip={() => {
              setRatingDialogOpen(false)
              setRatingTmdbId(null)
            }}
            isPending={ratingMutation.isPending}
          />
        </DialogContent>
      </Dialog>

    </>
  )
}

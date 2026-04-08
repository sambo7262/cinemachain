import { useState, useEffect, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useQueryClient, useMutation, keepPreviousData } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { EligibleActorDTO, EligibleMovieDTO, PaginatedMoviesDTO, PosterWallItem } from "@/lib/api"
import { ChainHistory } from "@/components/ChainHistory"
import { RatingsBadge } from "@/components/RatingsBadge"
import { RatingSlider } from "@/components/RatingSlider"
import { MovieFilterSidebar, FilterState, DEFAULT_FILTER_STATE } from "@/components/MovieFilterSidebar"
import { SessionCounters } from "@/components/SessionCounters"
import { PosterWall } from "@/components/PosterWall"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { X, Clock, MoreHorizontal, Shuffle, Star, ExternalLink, ListCheck, Trash2, Loader2 } from "lucide-react"
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import { useLoadingMessages } from "@/hooks/useLoadingMessages"
import { useNotification } from "@/contexts/NotificationContext"

const parseGenres = (s: string | null): string[] => {
  try { return JSON.parse(s ?? "[]") ?? [] } catch { return [] }
}

function ExpandableOverview({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="text-sm text-muted-foreground">
      <p className={expanded ? "" : "line-clamp-3"}>{text}</p>
      {text.length > 150 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-primary hover:underline mt-1"
        >
          {expanded ? "Show less" : "Read more"}
        </button>
      )}
    </div>
  )
}

export default function GameSession() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const sid = Number(sessionId)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Tab + selection state
  const [activeTab, setActiveTab] = useState<"actors" | "movies">("actors")
  const [selectedActor, setSelectedActor] = useState<EligibleActorDTO | null>(null)
  const [sortCol, setSortCol] = useState<"rating" | "year" | "runtime" | "mpaa" | "rt" | "rt_audience" | "imdb" | "metacritic" | "letterboxd" | "mdb_avg">("rating")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")
  const [allMovies, setAllMovies] = useState(false)
  const [showSavedOnly, setShowSavedOnly] = useState(false)
  const [showShortlistOnly, setShowShortlistOnly] = useState(false)
  const [showSuggestedOnly, setShowSuggestedOnly] = useState(false)
  const [moviesPage, setMoviesPage] = useState(1)
  const moviesListRef = useRef<HTMLDivElement>(null)
  const [movieRequestError, setMovieRequestError] = useState<string | null>(null)
  const [showMobileFilters, setShowMobileFilters] = useState(false)
  const [view, setView] = useState<"home" | "tabs">("home")
  const { showRadarr } = useNotification()
  const [deleteStepOpen, setDeleteStepOpen] = useState(false)

  // Rating dialog state
  const [ratingDialogOpen, setRatingDialogOpen] = useState(false)
  const [ratingMovieTmdbId, setRatingMovieTmdbId] = useState<number | null>(null)

  // Archive + rename state
  const [archiveConfirmOpen, setArchiveConfirmOpen] = useState(false)
  const [editNameOpen, setEditNameOpen] = useState(false)
  const [editNameValue, setEditNameValue] = useState("")
  const [editNameError, setEditNameError] = useState("")

  // Random pick state
  const [randomPickOpen, setRandomPickOpen] = useState(false)
  const [randomPickMovie, setRandomPickMovie] = useState<EligibleMovieDTO | null>(null)
  const [randomPickError, setRandomPickError] = useState<string | null>(null)

  // Movie selection splash dialog state
  const [splashOpen, setSplashOpen] = useState(false)
  const [splashMovie, setSplashMovie] = useState<EligibleMovieDTO | null>(null)
  const [radarrChecked, setRadarrChecked] = useState(true)

  // BUG-1: Disambiguation dialog state
  const [disambigOpen, setDisambigOpen] = useState(false)
  const [disambigCandidates, setDisambigCandidates] = useState<Array<{tmdb_id: number; name: string}>>([])
  const [disambigPendingMovie, setDisambigPendingMovie] = useState<EligibleMovieDTO | null>(null)

  // Filter and search state — Eligible Movies
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTER_STATE)
  const [searchQuery, setSearchQuery] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [excludeNR, setExcludeNR] = useState(false)

  // Session polling — stops when awaiting_continue
  const { data: session } = useQuery({
    queryKey: ["session", sid],
    queryFn: () => api.getSession(sid),    // fetch by ID, not active session
    refetchInterval: (query) =>
      query.state.data?.status === "awaiting_continue" ? false : 5000,
    refetchOnMount: "always",
    staleTime: 0,
    placeholderData: keepPreviousData,
    enabled: !!sid,
  })

  // Poster wall query — staleTime 5 minutes (posters change infrequently)
  const { data: posterWallData = [] } = useQuery<PosterWallItem[]>({
    queryKey: ["posterWall"],
    queryFn: api.getPosterWall,
    staleTime: 5 * 60 * 1000,
  })

  // Derive watched state from session
  const isWatched: boolean = session?.current_movie_watched ?? false

  // Safety reset: if session reloads while in tab view and status is awaiting_continue,
  // return to home hub (home hub shows the Continue the chain button).
  useEffect(() => {
    if (session && view === "tabs" && session.status === "awaiting_continue") {
      setView("home")
    }
  }, [session?.status])

  // Debounce search query by 200ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery), 200)
    return () => clearTimeout(t)
  }, [searchQuery])

  // Reset page when actor, sort, filter, or search changes
  useEffect(() => {
    setMoviesPage(1)
  }, [selectedActor?.tmdb_id, sortCol, sortDir, allMovies, debouncedSearch])

  // Reset all filters, search, sort, and selected actor on step advance (new movie)
  useEffect(() => {
    setShowSuggestedOnly(false)
    setShowSavedOnly(false)
    setShowShortlistOnly(false)
    setSearchQuery("")
    setDebouncedSearch("")
    setFilters(DEFAULT_FILTER_STATE)
    setSortCol("rating")
    setSortDir("desc")
    setMoviesPage(1)
    setSelectedActor(null)
    setExcludeNR(false)
  }, [session?.current_movie_tmdb_id])

  // Scroll movies list to top on page navigation
  useEffect(() => {
    moviesListRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [moviesPage])

  // Eligible actors for the current movie
  const { data: eligibleActorsData = [], isFetching: eligibleActorsFetching } = useQuery({
    queryKey: ["eligibleActors", sid, session?.current_movie_tmdb_id],
    queryFn: () => api.getEligibleActors(sid, true),  // always fetch ineligible too
    enabled: !!sid && session?.status === "active" && isWatched,
  })
  // Eligible actors: only those with is_eligible !== false (or undefined = eligible)
  const eligibleActors = eligibleActorsData.filter((a) => a.is_eligible !== false)

  // Dead-end condition: watched, not loading, no eligible actors, but ineligible actors exist
  const hasIneligibleActors = eligibleActorsData.filter((a) => a.is_eligible === false).length > 0
  const isDeadEnd = isWatched && !eligibleActorsFetching && eligibleActors.length === 0 && hasIneligibleActors

  // Eligible movies — scoped to selected actor + sort/filter params
  // enabled without selectedActor: no actor = combined-view (all eligible movies)
  // When a save/shortlist filter is active, or search/sidebar filters are active, fetch all results
  const hasActiveFilters = filters.genres.length > 0 || filters.mpaaRatings.length > 0 || filters.runtimeRange[0] !== 0 || filters.runtimeRange[1] !== 300
  const filteringByMark = showSavedOnly || showShortlistOnly || showSuggestedOnly
  const needsAllResults = filteringByMark || !!debouncedSearch || hasActiveFilters
  const effectivePage = needsAllResults ? 1 : moviesPage
  const effectivePageSize = needsAllResults ? 9999 : 20
  const { data: eligibleMoviesData, isFetching: eligibleMoviesFetching } = useQuery<PaginatedMoviesDTO>({
    queryKey: ["eligibleMovies", sid, selectedActor?.tmdb_id ?? null, sortCol, sortDir, allMovies, debouncedSearch, effectivePage, needsAllResults, excludeNR],
    queryFn: () =>
      api.getEligibleMovies(sid, {
        actor_id: selectedActor?.tmdb_id,  // undefined when no actor selected = combined view
        sort: sortCol,
        sort_dir: sortDir,
        all_movies: allMovies,
        search: debouncedSearch || undefined,
        page: effectivePage,
        page_size: effectivePageSize,
        exclude_nr: excludeNR,
      }),
    enabled: !!sid && !!session && isWatched,
  })
  const allEligibleMovies = eligibleMoviesData?.items ?? []
  const eligibleMoviesHasMore = eligibleMoviesData?.has_more ?? false
  const eligibleMoviesTotalPages = eligibleMoviesData?.total
    ? Math.ceil(eligibleMoviesData.total / 20)
    : moviesPage

  // TMDB suggestions — keyed on current_movie_tmdb_id to refetch on each step advance
  const { data: suggestionsData } = useQuery({
    queryKey: ["suggestions", sid, session?.current_movie_tmdb_id],
    queryFn: () => api.getSessionSuggestions(sid),
    enabled: !!sid && isWatched,
    staleTime: 0,
  })
  const suggestionIds = new Set(suggestionsData?.suggestion_tmdb_ids ?? [])

  // Concession-themed loading messages for actors and movies
  const actorsLoadingMessage = useLoadingMessages(eligibleActorsFetching)
  const moviesLoadingMessage = useLoadingMessages(eligibleMoviesFetching)

  // Client-side filtering: sidebar filters applied (search is now handled by backend)
  const filteredMovies = allEligibleMovies
    .filter((m) => filters.genres.length === 0 || parseGenres(m.genres).some((g) => filters.genres.includes(g)))
    .filter((m) => filters.mpaaRatings.length === 0 || filters.mpaaRatings.includes(m.mpaa_rating ?? "NR"))
    .filter((m) => {
      if (m.runtime == null) return true  // include movies with unknown runtime
      return m.runtime >= filters.runtimeRange[0] && m.runtime <= filters.runtimeRange[1]
    })
    .filter((m) => !showSavedOnly || m.saved)
    .filter((m) => !showShortlistOnly || m.shortlisted)
    .filter((m) => !showSuggestedOnly || suggestionIds.has(m.tmdb_id))

  const availableGenres = [...new Set(allEligibleMovies.flatMap((m) => parseGenres(m.genres)))].sort()

  // Actor selection switches to Eligible Movies tab
  const handleActorSelect = (actor: EligibleActorDTO) => {
    setSelectedActor(actor)
    setMoviesPage(1)
    setActiveTab("movies")
  }

  // Random pick handler — selects from filteredMovies (respects active filters)
  const handleRandomPick = () => {
    if (filteredMovies.length === 0) return
    const idx = Math.floor(Math.random() * filteredMovies.length)
    setRandomPickMovie(filteredMovies[idx])
    setRandomPickError(null)
    setRandomPickOpen(true)
  }

  // Movie selection: open splash dialog (replaces window.confirm)
  const handleMovieConfirm = (movie: EligibleMovieDTO) => {
    setSplashMovie(movie)
    setRadarrChecked(true)
    setSplashOpen(true)
  }

  // Splash confirm: pick-actor -> request-movie with skip_radarr support
  const handleSplashConfirm = async () => {
    if (!splashMovie) return
    setSplashOpen(false)
    const movie = splashMovie

    setMovieRequestError(null)
    try {
      if (selectedActor) {
        await api.pickActor(sid, {
          actor_tmdb_id: selectedActor.tmdb_id,
          actor_name: selectedActor.name,
        })
      }
      const requestResult = await api.requestMovie(sid, {
        movie_tmdb_id: movie.tmdb_id,
        movie_title: movie.title,
        skip_radarr: !radarrChecked,
      })
      if (requestResult?.status === "disambiguation_required") {
        // Multiple actors connect this pick — show disambiguation dialog.
        // Session is NOT advanced yet. Store pending movie for re-submission after user picks.
        setDisambigCandidates(requestResult.candidates ?? [])
        setDisambigPendingMovie(movie)
        setDisambigOpen(true)
        queryClient.setQueryData(["session", sid], requestResult.session)
        return  // do not advance view or show Radarr notification yet
      }
      if (!radarrChecked) {
        // Radarr skipped — no notification needed
      } else if (requestResult?.status === "already_in_radarr") {
        showRadarr("Already in Radarr")
      } else if (requestResult?.status === "queued") {
        showRadarr("Movie Queued for Download")
      } else if (requestResult?.status === "not_found_in_radarr") {
        showRadarr("Movie not found in Radarr — add it manually")
      } else if (requestResult?.status === "error") {
        showRadarr("Radarr unavailable — movie saved to session")
      }
      setView("home")
      setShowShortlistOnly(false)
      queryClient.setQueryData(["session", sid], requestResult.session)
      queryClient.invalidateQueries({ queryKey: ["session", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
      setMoviesPage(1)
      setSelectedActor(null)
    } catch (err: unknown) {
      // If pick-actor succeeded but request-movie failed, show targeted error.
      // Do NOT re-pick the actor — that step is already recorded on the server.
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to request movie. Try selecting the movie again."
      setMovieRequestError(msg)
    }
  }

  // BUG-1: Handle actor pick from disambiguation dialog
  const handleDisambigActorPick = async (candidate: {tmdb_id: number; name: string}) => {
    if (!disambigPendingMovie) return
    setDisambigOpen(false)
    setMovieRequestError(null)
    try {
      await api.pickActor(sid, {
        actor_tmdb_id: candidate.tmdb_id,
        actor_name: candidate.name,
      })
      const requestResult = await api.requestMovie(sid, {
        movie_tmdb_id: disambigPendingMovie.tmdb_id,
        movie_title: disambigPendingMovie.title,
      })
      if (requestResult?.status === "already_in_radarr") {
        showRadarr("Already in Radarr")
      } else if (requestResult?.status === "queued") {
        showRadarr("Movie Queued for Download")
      } else if (requestResult?.status === "not_found_in_radarr") {
        showRadarr("Movie not found in Radarr — add it manually")
      } else if (requestResult?.status === "error") {
        showRadarr("Radarr unavailable — movie saved to session")
      }
      setView("home")
      queryClient.setQueryData(["session", sid], requestResult.session)
      queryClient.invalidateQueries({ queryKey: ["session", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
      setMoviesPage(1)
      setSelectedActor(null)
      setDisambigPendingMovie(null)
      setDisambigCandidates([])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to request movie."
      setMovieRequestError(msg)
    }
  }

  // BUG-1: Handle skip from disambiguation dialog — passes skip_actor: true to backend
  const handleDisambigSkip = async () => {
    if (!disambigPendingMovie) return
    setDisambigOpen(false)
    setMovieRequestError(null)
    try {
      const requestResult = await api.requestMovie(sid, {
        movie_tmdb_id: disambigPendingMovie.tmdb_id,
        movie_title: disambigPendingMovie.title,
        skip_actor: true,  // tells backend: skip auto-resolve, proceed without actor step
      })
      if (requestResult?.status === "already_in_radarr") showRadarr("Already in Radarr")
      else if (requestResult?.status === "queued") showRadarr("Movie Queued for Download")
      else if (requestResult?.status === "not_found_in_radarr") showRadarr("Movie not found in Radarr — add it manually")
      else if (requestResult?.status === "error") showRadarr("Radarr unavailable — movie saved to session")
      setView("home")
      queryClient.setQueryData(["session", sid], requestResult.session)
      queryClient.invalidateQueries({ queryKey: ["session", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
      setMoviesPage(1)
      setSelectedActor(null)
      setDisambigPendingMovie(null)
      setDisambigCandidates([])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to request movie."
      setMovieRequestError(msg)
    }
  }

  // Mark current movie as watched (manual fallback)
  const markWatchedMutation = useMutation({
    mutationFn: () => api.markCurrentWatched(sid),
    onSuccess: (updatedSession) => {
      queryClient.setQueryData(["session", sid], updatedSession)
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] })
      setMoviesPage(1)
      // Open rating dialog for the movie that was just marked watched
      const tmdbId = updatedSession.current_movie_tmdb_id ?? session?.current_movie_tmdb_id ?? null
      setRatingMovieTmdbId(tmdbId)
      setRatingDialogOpen(true)
    },
  })

  // Rating mutation — PATCH /movies/{tmdbId}/rating
  const ratingMutation = useMutation({
    mutationFn: ({ tmdbId, rating }: { tmdbId: number; rating: number }) =>
      api.setMovieRating(tmdbId, rating),
    onSuccess: () => {
      setRatingDialogOpen(false)
      setRatingMovieTmdbId(null)
    },
  })

  // Delete last step mutation
  const deleteLastStepMutation = useMutation({
    mutationFn: () => api.deleteLastStep(sid),
    onSuccess: (data) => {
      queryClient.setQueryData(["session", sid], data)
      queryClient.invalidateQueries({ queryKey: ["session", sid] })
      setDeleteStepOpen(false)
    },
    onError: () => {
      // Error is displayed inline in the dialog
    },
  })

  // Save / shortlist mutations
  const saveMovieMutation = useMutation({
    mutationFn: (tmdbId: number) => api.saveMovie(sid, tmdbId),
    onMutate: async (tmdbId) => {
      await queryClient.cancelQueries({ queryKey: ["eligibleMovies", sid] })
      queryClient.setQueriesData<PaginatedMoviesDTO>(
        { queryKey: ["eligibleMovies", sid] },
        (old) => old ? { ...old, items: old.items.map(m => m.tmdb_id === tmdbId ? { ...m, saved: true } : m) } : old
      )
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] }),
  })

  const unsaveMovieMutation = useMutation({
    mutationFn: (tmdbId: number) => api.unsaveMovie(sid, tmdbId),
    onMutate: async (tmdbId) => {
      await queryClient.cancelQueries({ queryKey: ["eligibleMovies", sid] })
      queryClient.setQueriesData<PaginatedMoviesDTO>(
        { queryKey: ["eligibleMovies", sid] },
        (old) => old ? { ...old, items: old.items.map(m => m.tmdb_id === tmdbId ? { ...m, saved: false } : m) } : old
      )
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] }),
  })

  const addToShortlistMutation = useMutation({
    mutationFn: (tmdbId: number) => api.addToShortlist(sid, tmdbId),
    onMutate: async (tmdbId) => {
      await queryClient.cancelQueries({ queryKey: ["eligibleMovies", sid] })
      queryClient.setQueriesData<PaginatedMoviesDTO>(
        { queryKey: ["eligibleMovies", sid] },
        (old) => old ? { ...old, items: old.items.map(m => m.tmdb_id === tmdbId ? { ...m, shortlisted: true } : m) } : old
      )
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] }),
  })

  const removeFromShortlistMutation = useMutation({
    mutationFn: (tmdbId: number) => api.removeFromShortlist(sid, tmdbId),
    onMutate: async (tmdbId) => {
      await queryClient.cancelQueries({ queryKey: ["eligibleMovies", sid] })
      queryClient.setQueriesData<PaginatedMoviesDTO>(
        { queryKey: ["eligibleMovies", sid] },
        (old) => old ? { ...old, items: old.items.map(m => m.tmdb_id === tmdbId ? { ...m, shortlisted: false } : m) } : old
      )
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] }),
  })

  const clearShortlistMutation = useMutation({
    mutationFn: () => api.clearShortlist(sid),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] }),
  })

  // Archive session mutation
  const archiveMutation = useMutation({
    mutationFn: () => api.archiveSession(sid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activeSessions"] })
      navigate("/game")
    },
  })

  // Rename session mutation
  const renameMutation = useMutation({
    mutationFn: (name: string) => api.renameSession(sid, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["session", sid] })
      queryClient.invalidateQueries({ queryKey: ["activeSessions"] })
      setEditNameOpen(false)
    },
    onError: () => {
      setEditNameError("A session with that name already exists")
    },
  })

  // Save / shortlist toggle helpers
  const toggleSave = (movie: EligibleMovieDTO) => {
    if (movie.saved) {
      unsaveMovieMutation.mutate(movie.tmdb_id)
    } else {
      saveMovieMutation.mutate(movie.tmdb_id)
    }
  }

  const toggleShortlist = (movie: EligibleMovieDTO) => {
    if (movie.shortlisted) {
      removeFromShortlistMutation.mutate(movie.tmdb_id)
    } else {
      addToShortlistMutation.mutate(movie.tmdb_id)
    }
  }

  const shortlistedCount = allEligibleMovies.filter((m) => m.shortlisted).length

  // Continue the chain after watched confirmation.
  // CRITICAL: must call continueChain (not resumeSession) — continueChain preserves
  // current_movie_watched=True so eligible tabs remain unlocked.
  const handleContinue = () => {
    api.continueChain(sid).then((updatedSession) => {
      queryClient.setQueryData(["session", sid], updatedSession)
      setSelectedActor(null)
      setView("tabs")
      setActiveTab("actors")
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] })
    })
  }

  // Derive rating movie data from session steps for the rating dialog
  const ratingMovieStep = session?.steps.find(
    (s) => s.movie_tmdb_id === ratingMovieTmdbId
  )
  const ratingMovieTitle = ratingMovieStep?.movie_title ?? session?.current_movie_title ?? "(untitled)"
  const ratingMoviePoster = ratingMovieStep?.poster_path ?? null

  // Current movie title — prefer backend-resolved title, fall back to step derivation
  const currentMovieTitle =
    session?.current_movie_title           // prefer backend-resolved title (BUG-1 fix)
    ?? session?.steps.find(
      (s) => s.movie_tmdb_id === session.current_movie_tmdb_id
    )?.movie_title
    ?? session?.steps[session.steps.length - 1]?.movie_title
    ?? "(untitled)"


  return (
    <div className="min-h-screen flex flex-col">
      <PosterWall posters={posterWallData} />
      {/* Content wrapper — z-[2] ensures content sits above PosterWall (z-[1]) */}
      <div className="relative z-[2] flex flex-col flex-1">
      {/* Header */}
      <header className="border-b border-border bg-background px-4 sm:px-6 py-3 flex items-center justify-between">
        <div className="flex flex-col gap-1">
          {session?.name && (
            <p className="text-base font-semibold text-foreground">{session.name}</p>
          )}
          <p className="text-sm text-muted-foreground">
            Now playing: <span className="font-medium text-foreground">{currentMovieTitle}</span>
          </p>
          {session && (
            <SessionCounters
              watchedCount={session.watched_count ?? 0}
              watchedRuntimeMinutes={session.watched_runtime_minutes ?? 0}
              createdAt={session.created_at ?? ""}
            />
          )}
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Session actions"
              >
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => {
                  api.exportCsv(sid, session?.name ?? String(sid))
                }}
              >
                Export CSV
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => {
                setEditNameValue(session?.name ?? "")
                setEditNameOpen(true)
              }}>
                Edit Session Name
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                disabled={!session || session.steps.length <= 1}
                onClick={() => setDeleteStepOpen(true)}
              >
                Delete Last Step
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => setArchiveConfirmOpen(true)}
                className="text-destructive focus:text-destructive"
              >
                Archive Session
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <div className="flex-1 flex flex-col gap-4 py-4 w-full">

        {/* Session home page — permanent hub, shown when view === "home" */}
        {view === "home" && session && (() => {
          const sortedSteps = [...session.steps].sort((a, b) => b.step_order - a.step_order)
          const currentStep = sortedSteps[0]
          const previousStep = sortedSteps.find(s => s.movie_title && s !== currentStep)
          return (
            <div className="rounded-lg border border-border bg-card px-6 py-5 flex flex-col gap-5">
              <h2 className="text-base font-semibold text-foreground">Now playing</h2>

              {/* Current movie */}
              <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4">
                {(() => {
                  const posterUrl = currentStep?.poster_path
                    ? `https://image.tmdb.org/t/p/w185${currentStep.poster_path}`
                    : null
                  return posterUrl
                    ? <img src={posterUrl} alt="" className="w-[120px] h-[180px] rounded-md object-cover flex-shrink-0" />
                    : <div className="w-[120px] h-[180px] rounded-md bg-muted flex-shrink-0" />
                })()}
                <div className="flex flex-col gap-1 min-w-0 w-full">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">Now in queue</p>
                  <p className="text-lg font-bold text-foreground break-words">
                    {currentStep?.movie_title ?? "(untitled)"}
                  </p>
                  {(() => {
                    const detail = session.current_movie_detail
                    if (!detail) return null
                    return (
                      <>
                        {/* Metadata row: MPAA, year, runtime */}
                        <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                          {detail.mpaa_rating && (
                            <Badge variant="outline" className="text-xs">{detail.mpaa_rating}</Badge>
                          )}
                          {detail.year && <span>{detail.year}</span>}
                          {detail.runtime && (
                            <span>{Math.floor(detail.runtime / 60)}h {detail.runtime % 60}m</span>
                          )}
                        </div>
                        {/* Ratings row */}
                        <RatingsBadge variant="card" ratings={detail} />
                        {/* Overview — expandable */}
                        {detail.overview && <ExpandableOverview text={detail.overview} />}
                      </>
                    )
                  })()}
                  {!isWatched && (
                    <p className="text-sm text-muted-foreground">
                      Watch this movie, then mark it as watched to continue the chain.
                    </p>
                  )}
                </div>
              </div>

              {/* Previous movie (shown only when chain has 2+ movies) */}
              {previousStep && (
                <div className="flex flex-col gap-1 border-t border-border pt-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">Previous movie</p>
                  <p className="text-base font-semibold text-muted-foreground">{previousStep.movie_title}</p>
                </div>
              )}

              {/* Continue the chain CTA — shown when:
                  (a) awaiting_continue: normal post-watched flow, calls backend then navigates to tabs
                  (b) active + isWatched: continueChain was already called but user navigated away;
                      backend state is already active, just navigate to tabs directly */}
              {(session.status === "awaiting_continue" || (session.status === "active" && isWatched)) && (
                <Button
                  onClick={() => {
                    if (session.status === "awaiting_continue") {
                      handleContinue()
                    } else {
                      // active + isWatched: continueChain already called, session is active.
                      // Skip the backend call — just navigate to actor selection tab.
                      setView("tabs")
                      setActiveTab("actors")
                    }
                  }}
                  className="w-full bg-green-700 hover:bg-green-600"
                >
                  Continue the chain
                </Button>
              )}

              {/* Mark as Watched CTA */}
              {session.status === "active" && !isWatched && (
                <Button
                  onClick={() => markWatchedMutation.mutate()}
                  disabled={markWatchedMutation.isPending}
                  className="w-full"
                >
                  {markWatchedMutation.isPending ? "Marking…" : "Mark as Watched"}
                </Button>
              )}
            </div>
          )
        })()}

        {/* Movie request error — dismissible inline alert */}
        {movieRequestError && (
          <div className="flex items-center gap-2 rounded-lg border border-red-700 bg-red-950/40 px-4 py-3 text-red-400">
            <span className="flex-1 text-sm">{movieRequestError}</span>
            <button
              onClick={() => setMovieRequestError(null)}
              className="flex-shrink-0 text-red-400 hover:text-red-300"
              aria-label="Dismiss error"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Back button — returns to Session Home Page hub */}
        {view === "tabs" && (
          <div className="flex items-center gap-2 mb-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-foreground pl-0"
              onClick={() => setView("home")}
            >
              ← Back to session
            </Button>
          </div>
        )}

        {/* Three-tab panel — only shown when in tabs view */}
        {view === "tabs" && <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as "actors" | "movies")}
          className="flex-1"
        >
          <TabsList className="w-full">
            <TabsTrigger value="actors" className="flex-1">
              Eligible Actors
            </TabsTrigger>
            <TabsTrigger value="movies" className="flex-1 overflow-hidden">
              Eligible Movies
              {selectedActor && (
                <span className="ml-2 text-xs text-muted-foreground max-w-[160px] truncate inline-block align-middle">
                  via {selectedActor.name}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          {/* Eligible Actors tab */}
          <TabsContent value="actors" className="mt-3 rounded-lg bg-card p-4">
            {!isWatched ? (
              <div className="flex flex-col items-center gap-3 py-12 text-center">
                <Clock className="w-8 h-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Watch <span className="font-semibold text-foreground">{currentMovieTitle}</span> to unlock eligible actors.
                </p>
              </div>
            ) : isDeadEnd ? (
              <div className="flex flex-col items-center gap-4 py-12 text-center">
                <p className="text-lg font-semibold text-foreground">Chain dead end</p>
                <p className="text-sm text-muted-foreground max-w-sm">
                  All actors from this movie have been used in this session.
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setDeleteStepOpen(true)}
                  >
                    Delete Last Step
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => {
                      api.archiveSession(sid).then(() => navigate("/game"))
                    }}
                  >
                    End Session
                  </Button>
                </div>
              </div>
            ) : (
              <div className="relative">
                {eligibleActorsFetching && (
                  <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-card/80 backdrop-blur-sm rounded-md min-h-[80px]">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                    <p className="text-xs text-muted-foreground">{actorsLoadingMessage}</p>
                  </div>
                )}
                {eligibleActors.length === 0 && !hasIneligibleActors ? (
                  <p className="text-sm text-muted-foreground py-8 text-center">No eligible actors found.</p>
                ) : (
                  <div className="rounded-md border border-border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground w-10"></th>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground">Actor</th>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground hidden sm:table-cell">Character</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {eligibleActors.map((actor) => (
                          <tr
                            key={actor.tmdb_id}
                            onClick={() => handleActorSelect(actor)}
                            className="cursor-pointer hover:bg-accent/50 transition-colors"
                          >
                            <td className="px-4 py-2">
                              {actor.profile_path ? (
                                <img
                                  src={`https://image.tmdb.org/t/p/w92${actor.profile_path}`}
                                  alt={actor.name}
                                  className="w-8 h-8 rounded-full object-cover"
                                />
                              ) : (
                                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-bold">
                                  {actor.name.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase()}
                                </div>
                              )}
                            </td>
                            <td className="px-4 py-2 font-medium">{actor.name}</td>
                            <td className="px-4 py-2 text-muted-foreground italic hidden sm:table-cell">{actor.character}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Ineligible actors section — always visible when there are ineligible actors */}
                {(() => {
                  const ineligible = eligibleActorsData.filter((a) => a.is_eligible === false)
                  if (ineligible.length === 0) return null
                  return (
                    <>
                      <Separator className="my-3" />
                      <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Already picked</p>
                      {ineligible.map((actor) => (
                        <div
                          key={actor.tmdb_id}
                          className="flex items-center gap-3 py-2 opacity-50 cursor-default"
                          aria-disabled="true"
                        >
                          <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground" aria-hidden="true">
                            {actor.name.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase()}
                          </div>
                          <span className="text-sm">{actor.name}</span>
                          <Badge variant="secondary" className="ml-auto text-xs">Already picked</Badge>
                        </div>
                      ))}
                    </>
                  )
                })()}
              </div>
            )}
          </TabsContent>

          {/* Eligible Movies tab */}
          <TabsContent value="movies" ref={moviesListRef} className="mt-3 rounded-lg bg-card p-4">
            {!isWatched ? (
              <div className="flex flex-col items-center gap-3 py-12 text-center">
                <Clock className="w-8 h-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Watch <span className="font-semibold text-foreground">{currentMovieTitle}</span> to unlock eligible movies.
                </p>
              </div>
            ) : (
              <>
                {/* Sort + filter controls */}
                <div className="flex gap-2 mb-3">
                  {/* Left: game controls — wraps on narrow viewports */}
                  <div className="flex flex-wrap items-center gap-2 flex-1">
                    <Button
                      variant={allMovies ? "default" : "outline"}
                      size="sm"
                      onClick={() => setAllMovies((a) => !a)}
                    >
                      {allMovies ? "All Movies" : "Unwatched Only"}
                    </Button>
                    {selectedActor && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => { setSelectedActor(null); setMoviesPage(1) }}
                        className="text-muted-foreground"
                      >
                        Show all eligible movies
                      </Button>
                    )}
                    <Select
                      value={sortCol}
                      onValueChange={(v) => {
                        setSortCol(v as typeof sortCol)
                        setSortDir("desc")
                        setMoviesPage(1)
                      }}
                    >
                      <SelectTrigger className="h-8 w-[110px] text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="rating">TMDB</SelectItem>
                        <SelectItem value="rt">RT Score</SelectItem>
                        <SelectItem value="rt_audience">RT Audience</SelectItem>
                        <SelectItem value="imdb">IMDb</SelectItem>
                        <SelectItem value="metacritic">Metacritic</SelectItem>
                        <SelectItem value="letterboxd">Letterboxd</SelectItem>
                        <SelectItem value="mdb_avg">MDB Avg</SelectItem>
                        <SelectItem value="year">Year</SelectItem>
                        <SelectItem value="runtime">Runtime</SelectItem>
                        <SelectItem value="mpaa">MPAA</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      variant={sortDir === "asc" ? "default" : "outline"}
                      size="sm"
                      className="h-8 px-2 text-xs"
                      onClick={() => { setSortDir("asc"); setMoviesPage(1) }}
                    >
                      Asc
                    </Button>
                    <Button
                      variant={sortDir === "desc" ? "default" : "outline"}
                      size="sm"
                      className="h-8 px-2 text-xs"
                      onClick={() => { setSortDir("desc"); setMoviesPage(1) }}
                    >
                      Desc
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className={cn(filteredMovies.length === 0 ? "opacity-50 pointer-events-none" : "")}
                      onClick={handleRandomPick}
                      aria-label="Random pick"
                    >
                      <Shuffle className="w-4 h-4 mr-1" />
                      Random
                    </Button>
                  </div>
                  {/* Right: mark filters — stacked vertically */}
                  <div className="flex flex-col gap-1 shrink-0">
                    <Button
                      variant={showSavedOnly ? "default" : "outline"}
                      size="sm"
                      onClick={() => setShowSavedOnly((v) => !v)}
                    >
                      Saved ★
                    </Button>
                    <Button
                      variant={showShortlistOnly ? "default" : "outline"}
                      size="sm"
                      onClick={() => setShowShortlistOnly((v) => !v)}
                    >
                      <ListCheck className="w-3.5 h-3.5 mr-1" />
                      Shortlist
                    </Button>
                    {suggestionIds.size > 0 && (
                      <Button
                        variant={showSuggestedOnly ? "default" : "outline"}
                        size="sm"
                        onClick={() => setShowSuggestedOnly((v) => !v)}
                      >
                        ✦ Suggested
                      </Button>
                    )}
                    <Button
                      variant={excludeNR ? "default" : "outline"}
                      size="sm"
                      onClick={() => setExcludeNR((v) => !v)}
                    >
                      Hide NR
                    </Button>
                    {shortlistedCount > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => clearShortlistMutation.mutate()}
                      >
                        <Trash2 className="w-3.5 h-3.5 mr-1" />
                        Clear Shortlist
                      </Button>
                    )}
                  </div>
                </div>

                {/* Search input — full width above the movie panel */}
                <Input
                  placeholder="Search movies..."
                  aria-label="Search eligible movies"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="mb-3"
                />

                {/* Mobile: Filters toggle button */}
                <div className="lg:hidden mb-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowMobileFilters(!showMobileFilters)}
                  >
                    Filters
                  </Button>
                </div>

                {/* Filter sidebar + movie list flex row */}
                <div className="flex flex-col lg:flex-row gap-6">
                  {/* Sidebar: always visible on lg+, toggle-visible on mobile */}
                  <aside className={cn("w-full lg:w-[200px] lg:flex-shrink-0", showMobileFilters ? "block" : "hidden lg:block")}>
                    <MovieFilterSidebar
                      genres={availableGenres}
                      filters={filters}
                      onChange={setFilters}
                    />
                  </aside>

                  <div className="flex-1 min-w-0 relative">
                    {eligibleMoviesFetching && (
                      <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-card/80 backdrop-blur-sm rounded-md min-h-[80px]">
                        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                        <p className="text-xs text-muted-foreground">{moviesLoadingMessage}</p>
                      </div>
                    )}

                    {/* Empty state messages */}
                    {filteredMovies.length === 0 && allEligibleMovies.length > 0 && (
                      (showSavedOnly || showShortlistOnly) ? (
                        <div className="flex flex-col items-center gap-2 py-8 text-center">
                          <p className="text-sm font-medium text-muted-foreground">
                            {showSavedOnly && showShortlistOnly
                              ? "No movies match"
                              : showSavedOnly
                              ? "No saved movies"
                              : showShortlistOnly
                              ? "Shortlist is empty"
                              : "No movies match your filters."}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {showSavedOnly && showShortlistOnly
                              ? "No movies are both saved and shortlisted. Adjust your filters to see eligible movies."
                              : showSavedOnly
                              ? "Save movies using the ★ icon on any poster. Clear the Saved filter to see all eligible movies."
                              : showShortlistOnly
                              ? "Add movies using the ✓ icon on any poster. Clear the Shortlist filter to see all eligible movies."
                              : "Try adjusting your filters."}
                          </p>
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground py-4">
                          {debouncedSearch && (filters.genres.length > 0 || filters.mpaaRatings.length > 0 || filters.runtimeRange[0] !== 0 || filters.runtimeRange[1] !== 300)
                            ? "No movies match your search and filters."
                            : debouncedSearch
                            ? "No movies match your search."
                            : "No movies match your filters. Try adjusting the filters."}
                        </p>
                      )
                    )}

                    {/* Movies list — compact table */}
                    {filteredMovies.length === 0 && allEligibleMovies.length === 0 && !eligibleMoviesFetching ? (
                      <p className="text-sm text-muted-foreground py-8 text-center">
                        {selectedActor
                          ? `No eligible movies via ${selectedActor.name}.`
                          : "No eligible movies found for this session."}
                      </p>
                    ) : filteredMovies.length > 0 ? (
                      <div className="space-y-1.5">
                        {filteredMovies.map((movie) => (
                          <div
                            key={movie.tmdb_id}
                            onClick={movie.selectable ? () => handleMovieConfirm(movie) : undefined}
                            className={cn(
                              "flex gap-3 rounded-md border border-border transition-colors",
                              movie.selectable
                                ? "cursor-pointer hover:bg-accent/50"
                                : "opacity-40 cursor-not-allowed",
                              movie.saved && "bg-amber-500/10",
                              movie.shortlisted && "bg-blue-500/10",
                            )}
                          >
                            {/* Left zone — poster only */}
                            <div className="relative flex-shrink-0 w-16">
                              {movie.poster_path ? (
                                <img
                                  src={`https://image.tmdb.org/t/p/w92${movie.poster_path}`}
                                  alt={movie.title}
                                  className="w-16 h-24 rounded-l-md object-cover"
                                />
                              ) : (
                                <div className="w-16 h-24 rounded-l-md bg-muted" />
                              )}
                            </div>

                            {/* Middle zone — content */}
                            <div className="flex flex-col justify-start flex-1 pt-2 pb-1 gap-0.5 min-w-0 overflow-hidden">
                              {/* Row 1: Title — full width */}
                              <span className="font-medium text-sm truncate">{movie.title}</span>
                              {/* Row 2: Via actor */}
                              <div className="text-xs text-muted-foreground italic truncate">
                                {movie.via_actor_name ?? (selectedActor?.name ?? "—")}
                              </div>
                              {/* Row 3: Metadata — year · runtime · MPAA */}
                              <div className="flex items-center flex-wrap gap-1 text-xs text-muted-foreground">
                                {movie.year && <span>{movie.year}</span>}
                                {movie.runtime != null && <span>· {movie.runtime}m</span>}
                                {movie.mpaa_rating && <span>· {movie.mpaa_rating}</span>}
                              </div>
                              {/* Row 4: Ratings */}
                              <RatingsBadge variant="card" ratings={movie} />
                            </div>

                            {/* Right zone — ExternalLink, Star, ListCheck vertical stack */}
                            <div className="flex flex-col items-center justify-center gap-1 pr-2 flex-shrink-0">
                              <a
                                href={movie.imdb_id ? `https://www.imdb.com/title/${movie.imdb_id}` : `https://www.themoviedb.org/movie/${movie.tmdb_id}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                aria-label={movie.imdb_id ? "View on IMDB" : "View on TMDB"}
                                className="p-1.5 rounded hover:bg-accent/50 transition-colors text-muted-foreground hover:text-foreground"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <ExternalLink className="w-4 h-4" />
                              </a>
                              <button
                                className={cn("p-1.5 rounded hover:bg-accent/50 transition-colors")}
                                onClick={(e) => { e.stopPropagation(); toggleSave(movie) }}
                                aria-label={movie.saved ? "Remove from saved" : "Save movie"}
                              >
                                <Star className={cn("w-4 h-4", movie.saved ? "fill-amber-400 text-amber-400" : "text-muted-foreground")} />
                              </button>
                              <button
                                className={cn(
                                  "p-1.5 rounded hover:bg-accent/50 transition-colors",
                                  shortlistedCount >= 6 && !movie.shortlisted && "opacity-40 pointer-events-none"
                                )}
                                onClick={(e) => { e.stopPropagation(); toggleShortlist(movie) }}
                                aria-label={movie.shortlisted ? "Remove from shortlist" : "Add to shortlist"}
                              >
                                <ListCheck className={cn("w-4 h-4", movie.shortlisted ? "fill-blue-400 text-blue-400" : "text-muted-foreground")} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {/* Pagination controls — hidden during search or when save/shortlist filter is active */}
                    {!needsAllResults && eligibleMoviesTotalPages > 1 && (
                      <div className="flex items-center justify-center gap-3 mt-4">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setMoviesPage((p) => p - 1)}
                          disabled={moviesPage <= 1 || eligibleMoviesFetching}
                        >
                          ← Prev
                        </Button>
                        <span className="text-xs text-muted-foreground">
                          Page {moviesPage} of {eligibleMoviesTotalPages}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setMoviesPage((p) => p + 1)}
                          disabled={!eligibleMoviesHasMore || eligibleMoviesFetching}
                        >
                          Next →
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </TabsContent>

        </Tabs>}

        {/* Chain History — bottom of page */}
        {session && session.steps.length > 0 && (
          <ChainHistory steps={session.steps} />
        )}
      </div>

      {/* Movie Selection Splash Dialog */}
      <Dialog open={splashOpen} onOpenChange={setSplashOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <div className="flex items-center gap-2">
              {splashMovie && (
                <button
                  onClick={() => toggleSave(splashMovie)}
                  aria-label={splashMovie.saved ? "Remove from saved" : "Save movie"}
                  className="p-1 shrink-0"
                >
                  <Star className={cn("w-4 h-4", splashMovie.saved ? "fill-amber-400 text-amber-400" : "text-muted-foreground hover:text-foreground")} />
                </button>
              )}
              <DialogTitle className="text-base font-semibold">
                {splashMovie?.title}
              </DialogTitle>
            </div>
          </DialogHeader>

          {/* Top row — poster + stats */}
          <div className="flex gap-4 items-start">
            <div className="shrink-0">
              {splashMovie?.poster_path ? (
                <img
                  src={`https://image.tmdb.org/t/p/w185${splashMovie.poster_path}`}
                  alt={splashMovie.title}
                  className="w-28 rounded-md object-cover"
                />
              ) : (
                <div className="w-28 h-40 rounded-md bg-secondary flex items-center justify-center text-muted-foreground text-xs">
                  No poster
                </div>
              )}
            </div>
            <div className="flex-1 flex flex-col gap-2">
              {/* Stats row */}
              <div className="flex items-center gap-2 flex-wrap">
                {splashMovie && <RatingsBadge variant="splash" ratings={splashMovie} />}
                <Badge variant="outline" className="text-xs">
                  {splashMovie?.mpaa_rating || "NR"}
                </Badge>
                {splashMovie?.runtime && (
                  <Badge variant="outline" className="text-xs">
                    {Math.floor(splashMovie.runtime / 60)}h {splashMovie.runtime % 60}m
                  </Badge>
                )}
                {splashMovie?.year && (
                  <Badge variant="outline" className="text-xs">
                    {splashMovie.year}
                  </Badge>
                )}
              </div>
              {/* IMDB / TMDB link */}
              {splashMovie?.tmdb_id && (
                <a
                  href={splashMovie.imdb_id ? `https://www.imdb.com/title/${splashMovie.imdb_id}` : `https://www.themoviedb.org/movie/${splashMovie.tmdb_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={splashMovie.imdb_id ? `View ${splashMovie.title} on IMDB (opens in new tab)` : `View ${splashMovie.title} on TMDB (opens in new tab)`}
                  className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  {splashMovie.imdb_id ? "View on IMDB" : "View on TMDB"}
                </a>
              )}
            </div>
          </div>

          {/* Overview — full width below poster row */}
          <p className="text-sm leading-relaxed">
            {splashMovie?.overview || "No overview available."}
          </p>

          {/* Radarr checkbox */}
          <div className="flex items-start gap-3 pt-2">
            <Checkbox
              id="radarr-checkbox"
              checked={radarrChecked}
              onCheckedChange={(checked) => setRadarrChecked(checked === true)}
            />
            <div>
              <label htmlFor="radarr-checkbox" className="text-sm font-medium cursor-pointer">
                Request download via Radarr
              </label>
              <p className="text-xs text-muted-foreground">
                Adds this movie to your Radarr download queue.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSplashOpen(false)}>
              Keep Browsing
            </Button>
            <Button onClick={handleSplashConfirm}>
              Add to Session
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Last Step Dialog */}
      <Dialog open={deleteStepOpen} onOpenChange={setDeleteStepOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Last Step</DialogTitle>
            <DialogDescription>
              This will remove the most recent step and revert the session to the previous movie. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteLastStepMutation.isError && (
            <p className="text-sm text-destructive">Could not delete step. Try again.</p>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteStepOpen(false)}
              disabled={deleteLastStepMutation.isPending}
            >
              Keep Step
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteLastStepMutation.mutate()}
              disabled={deleteLastStepMutation.isPending}
            >
              {deleteLastStepMutation.isPending ? "Deleting..." : "Delete Step"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* BUG-1: Actor disambiguation dialog */}
      <Dialog open={disambigOpen} onOpenChange={setDisambigOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Who are you following?</DialogTitle>
            <DialogDescription>
              Multiple actors connect this pick. Choose which one to record in your chain.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2 py-2">
            {disambigCandidates.map((candidate) => (
              <Button
                key={candidate.tmdb_id}
                variant="outline"
                className="w-full justify-start"
                onClick={() => handleDisambigActorPick(candidate)}
              >
                {candidate.name}
              </Button>
            ))}
          </div>
          <DialogFooter>
            <Button variant="ghost" className="w-full" onClick={handleDisambigSkip}>
              Skip (leave actor unrecorded)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Random Pick Dialog */}
      <Dialog open={randomPickOpen} onOpenChange={setRandomPickOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Random Pick</DialogTitle>
          </DialogHeader>
          {randomPickMovie && (
            <div className="flex items-start gap-4 py-2">
              {randomPickMovie.poster_path ? (
                <img
                  src={`https://image.tmdb.org/t/p/w185${randomPickMovie.poster_path}`}
                  alt={randomPickMovie.title}
                  className="w-16 h-24 rounded object-cover flex-shrink-0"
                />
              ) : (
                <div className="w-16 h-24 rounded bg-muted flex-shrink-0" />
              )}
              <div className="flex flex-col gap-1">
                <p className="text-lg font-semibold text-foreground">{randomPickMovie.title}</p>
                <p className="text-sm text-muted-foreground">
                  {[randomPickMovie.year, randomPickMovie.runtime != null ? `${randomPickMovie.runtime}m` : null]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
            </div>
          )}
          {randomPickError && (
            <p className="text-sm text-destructive">{randomPickError}</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRandomPickOpen(false)}>
              Keep Browsing
            </Button>
            <Button
              variant="default"
              onClick={() => {
                if (!randomPickMovie) return
                setRandomPickOpen(false)
                handleMovieConfirm(randomPickMovie)
              }}
            >
              Request This Movie
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Archive Confirmation Dialog */}
      <Dialog open={archiveConfirmOpen} onOpenChange={setArchiveConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Archive this session?</DialogTitle>
            <DialogDescription>
              This session will be moved to the archive and no longer appear on the home page. You can still view it in archived sessions.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setArchiveConfirmOpen(false)}>
              Keep Session
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                archiveMutation.mutate()
                setArchiveConfirmOpen(false)
              }}
              disabled={archiveMutation.isPending}
            >
              Archive Session
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Session Name Dialog */}
      <Dialog open={editNameOpen} onOpenChange={(open) => {
        setEditNameOpen(open)
        if (!open) { setEditNameError("") }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Session Name</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <Input
              placeholder="Enter a session name"
              value={editNameValue}
              onChange={(e) => {
                setEditNameValue(e.target.value)
                setEditNameError("")
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && editNameValue.trim()) {
                  renameMutation.mutate(editNameValue.trim())
                }
              }}
            />
            {editNameError && (
              <p className="text-red-500 text-xs">{editNameError}</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditNameOpen(false)}>
              Discard Changes
            </Button>
            <Button
              onClick={() => {
                if (!editNameValue.trim()) {
                  setEditNameError("This field is required.")
                  return
                }
                renameMutation.mutate(editNameValue.trim())
              }}
              disabled={renameMutation.isPending}
            >
              Save Name
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      </div>{/* end content wrapper */}

      {/* Rating Dialog — appears after Mark as Watched */}
      <Dialog open={ratingDialogOpen} onOpenChange={setRatingDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Rate this movie</DialogTitle>
          </DialogHeader>
          <RatingSlider
            movieTitle={ratingMovieTitle}
            posterPath={ratingMoviePoster}
            currentRating={null}
            onSave={(rating) => ratingMutation.mutate({ tmdbId: ratingMovieTmdbId!, rating })}
            onSkip={() => {
              setRatingDialogOpen(false)
              setRatingMovieTmdbId(null)
            }}
            isPending={ratingMutation.isPending}
          />
        </DialogContent>
      </Dialog>

    </div>
  )
}

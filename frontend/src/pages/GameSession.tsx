import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { EligibleActorDTO, EligibleMovieDTO, PaginatedMoviesDTO, PosterWallItem } from "@/lib/api"
import { ChainHistory } from "@/components/ChainHistory"
import { MovieCard } from "@/components/MovieCard"
import { MovieFilterSidebar, FilterState, DEFAULT_FILTER_STATE } from "@/components/MovieFilterSidebar"
import { SessionCounters } from "@/components/SessionCounters"
import { PosterWall } from "@/components/PosterWall"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { X, Clock, MoreHorizontal, Shuffle } from "lucide-react"
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
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

export default function GameSession() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const sid = Number(sessionId)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Tab + selection state
  const [activeTab, setActiveTab] = useState<"actors" | "movies" | "suggested">("actors")
  const [selectedActor, setSelectedActor] = useState<EligibleActorDTO | null>(null)
  const [sort, setSort] = useState<"rating" | "runtime" | "genre">("rating")
  const [allMovies, setAllMovies] = useState(false)
  const [moviesPage, setMoviesPage] = useState(1)
  const [movieRequestError, setMovieRequestError] = useState<string | null>(null)
  const [showMobileFilters, setShowMobileFilters] = useState(false)
  const [view, setView] = useState<"home" | "tabs">("home")
  const { showRadarr } = useNotification()
  const [deleteStepOpen, setDeleteStepOpen] = useState(false)

  // Random pick state
  const [randomPickOpen, setRandomPickOpen] = useState(false)
  const [randomPickMovie, setRandomPickMovie] = useState<EligibleMovieDTO | null>(null)
  const [randomPickError, setRandomPickError] = useState<string | null>(null)

  // Filter and search state — Eligible Movies
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTER_STATE)
  const [searchQuery, setSearchQuery] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")

  // Session polling — stops when awaiting_continue
  const { data: session } = useQuery({
    queryKey: ["session", sid],
    queryFn: () => api.getSession(sid),    // fetch by ID, not active session
    refetchInterval: (query) =>
      query.state.data?.status === "awaiting_continue" ? false : 5000,
    refetchOnMount: "always",
    staleTime: 0,
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
  const { data: eligibleMoviesData, isFetching: eligibleMoviesFetching } = useQuery<PaginatedMoviesDTO>({
    queryKey: ["eligibleMovies", sid, selectedActor?.tmdb_id ?? null, sort, allMovies, moviesPage],
    queryFn: () =>
      api.getEligibleMovies(sid, {
        actor_id: selectedActor?.tmdb_id,  // undefined when no actor selected = combined view
        sort,
        all_movies: allMovies,
        page: moviesPage,
        page_size: 20,
      }),
    enabled: !!sid && !!session && isWatched,
  })
  const allEligibleMovies = eligibleMoviesData?.items ?? []
  const eligibleMoviesHasMore = eligibleMoviesData?.has_more ?? false

  // Suggestions query — only fires when Suggested tab is active
  const { data: suggestions = [], isLoading: suggestionsLoading } = useQuery({
    queryKey: ["suggestions", sid],
    queryFn: () => api.getSuggestions(sid),
    enabled: !!sid && !!session && view === "tabs" && activeTab === "suggested",
    staleTime: 30000,
  })

  // Concession-themed loading messages for actors and movies
  const actorsLoadingMessage = useLoadingMessages(eligibleActorsFetching)
  const moviesLoadingMessage = useLoadingMessages(eligibleMoviesFetching)

  // Client-side filtering: search + sidebar filters applied simultaneously (AND relationship)
  const filteredMovies = allEligibleMovies
    .filter((m) => debouncedSearch === "" || m.title.toLowerCase().includes(debouncedSearch.toLowerCase()))
    .filter((m) => filters.genres.length === 0 || parseGenres(m.genres).some((g) => filters.genres.includes(g)))
    .filter((m) => filters.mpaaRatings.length === 0 || filters.mpaaRatings.includes(m.mpaa_rating ?? "NR"))
    .filter((m) => {
      if (m.runtime == null) return true  // include movies with unknown runtime
      return m.runtime >= filters.runtimeRange[0] && m.runtime <= filters.runtimeRange[1]
    })

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

  // Movie selection: confirm -> pick-actor -> request-movie with error recovery
  const handleMovieConfirm = async (movie: EligibleMovieDTO) => {
    const confirmed = window.confirm(
      `Select "${movie.title}" as your next movie?`
    )
    if (!confirmed) return

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

  // Mark current movie as watched (manual fallback)
  const markWatchedMutation = useMutation({
    mutationFn: () => api.markCurrentWatched(sid),
    onSuccess: (updatedSession) => {
      queryClient.setQueryData(["session", sid], updatedSession)
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] })
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

  // Current movie title — prefer backend-resolved title, fall back to step derivation
  const currentMovieTitle =
    session?.current_movie_title           // prefer backend-resolved title (BUG-1 fix)
    ?? session?.steps.find(
      (s) => s.movie_tmdb_id === session.current_movie_tmdb_id
    )?.movie_title
    ?? session?.steps[session.steps.length - 1]?.movie_title
    ?? "(untitled)"

  // Derive UI state from session.status + steps shape
  const lastStep = session?.steps.length
    ? session.steps.reduce((a, b) => a.step_order > b.step_order ? a : b)
    : null
  // "movie_selected_unwatched": active session, last step has a movie but no actor
  // (the movie was just requested, waiting to be watched)
  const isMovieSelected = session?.status === "active"
    && lastStep !== null
    && lastStep.actor_tmdb_id === null
    && session.steps.length > 1

  // "starting_movie": session just created, first step exists, no actor picked yet.
  // The user must watch the starting movie before picking an actor.
  const isStartingMovie =
    session?.status === "active" &&
    session.steps.length === 1 &&
    lastStep?.actor_tmdb_id === null

  return (
    <div className={cn("min-h-screen flex flex-col", posterWallData.length < 5 ? "bg-background" : "")}>
      <PosterWall posters={posterWallData} />
      {/* Header */}
      <header className="border-b border-border px-6 py-3 flex items-center justify-between">
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
              stepCount={session.step_count ?? 0}
              uniqueActorCount={session.unique_actor_count ?? 0}
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
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                disabled={!session || session.steps.length <= 1}
                onClick={() => setDeleteStepOpen(true)}
              >
                Delete Last Step
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <div className="flex-1 flex flex-col gap-4 px-6 py-4 max-w-5xl w-full mx-auto">
        {/* Session state panel — shows context-appropriate guidance */}
        {session && (
          <div className="rounded-lg border border-border px-4 py-3 text-sm">
            {isStartingMovie && !isWatched && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Clock className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <p className="text-muted-foreground">
                    Watch <span className="font-semibold text-foreground">{currentMovieTitle}</span>,
                    then come back and pick an actor to begin the chain.
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => markWatchedMutation.mutate()}
                  disabled={markWatchedMutation.isPending}
                  className="flex-shrink-0 ml-4"
                >
                  {markWatchedMutation.isPending ? "Marking…" : "Mark as Watched"}
                </Button>
              </div>
            )}

            {session.status === "active" && isMovieSelected && !isWatched && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Clock className="w-4 h-4 text-amber-400 flex-shrink-0" />
                  <p className="text-muted-foreground">
                    <span className="font-semibold text-foreground">{currentMovieTitle}</span> added to Radarr.
                    Mark it as watched when you're done, then continue the chain.
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => markWatchedMutation.mutate()}
                  disabled={markWatchedMutation.isPending}
                  className="flex-shrink-0 ml-4"
                >
                  {markWatchedMutation.isPending ? "Marking…" : "Mark as Watched"}
                </Button>
              </div>
            )}

            {session.status === "active" && !isMovieSelected && session.steps.length > 1 && (
              <p className="text-muted-foreground">
                Pick your next actor from the Eligible Actors tab to continue the chain.
              </p>
            )}

          </div>
        )}

        {/* Session home page — permanent hub, shown when view === "home" */}
        {view === "home" && session && (() => {
          const sortedSteps = [...session.steps].sort((a, b) => b.step_order - a.step_order)
          const currentStep = sortedSteps[0]
          const previousStep = sortedSteps.find(s => s.movie_title && s !== currentStep)
          return (
            <div className="rounded-lg border border-border bg-card px-6 py-5 flex flex-col gap-5">
              <h2 className="text-base font-semibold text-foreground">Now playing</h2>

              {/* Current movie */}
              <div className="flex items-start gap-4">
                {(() => {
                  const posterUrl = currentStep?.poster_path
                    ? `https://image.tmdb.org/t/p/w185${currentStep.poster_path}`
                    : null
                  return posterUrl
                    ? <img src={posterUrl} alt="" className="w-[120px] h-[180px] rounded-md object-cover flex-shrink-0" />
                    : <div className="w-[120px] h-[180px] rounded-md bg-muted flex-shrink-0" />
                })()}
                <div className="flex flex-col gap-1">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">Now in queue</p>
                  <p className="text-lg font-bold text-foreground">
                    {currentStep?.movie_title ?? "(untitled)"}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {isStartingMovie
                      ? "Watch this movie, then mark it as watched to start the chain."
                      : "Added to Radarr. Watch it, then mark as watched to continue the chain."}
                  </p>
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
                  onClick={() => {
                    markWatchedMutation.mutate()
                  }}
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
          onValueChange={(v) => setActiveTab(v as "actors" | "movies" | "suggested")}
          className="flex-1"
        >
          <TabsList className="w-full">
            <TabsTrigger value="actors" className="flex-1">
              Eligible Actors
            </TabsTrigger>
            <TabsTrigger value="movies" className="flex-1">
              Eligible Movies
              {selectedActor && (
                <span className="ml-2 text-xs text-muted-foreground">
                  via {selectedActor.name}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="suggested" className="flex-1">
              Suggested
            </TabsTrigger>
          </TabsList>

          {/* Eligible Actors tab */}
          <TabsContent value="actors" className="mt-3">
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
                      api.archiveSession(sid).then(() => navigate("/"))
                    }}
                  >
                    End Session
                  </Button>
                </div>
              </div>
            ) : (
              <>
                {actorsLoadingMessage && (
                  <p className="text-sm text-muted-foreground text-center py-4 animate-pulse">
                    {actorsLoadingMessage}
                  </p>
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
              </>
            )}
          </TabsContent>

          {/* Eligible Movies tab */}
          <TabsContent value="movies" className="mt-3">
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
                <div className="flex items-center gap-2 mb-3">
                  <Select
                    value={sort}
                    onValueChange={(v) => setSort(v as "rating" | "runtime" | "genre")}
                  >
                    <SelectTrigger className="w-36">
                      <SelectValue placeholder="Sort by" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="rating">By Rating</SelectItem>
                      <SelectItem value="runtime">By Runtime</SelectItem>
                      <SelectItem value="genre">By Genre</SelectItem>
                    </SelectContent>
                  </Select>
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
                  <Button
                    variant="ghost"
                    size="sm"
                    className={cn(
                      "ml-auto",
                      (filteredMovies.length === 0 || !selectedActor) ? "opacity-50 pointer-events-none" : ""
                    )}
                    onClick={handleRandomPick}
                    aria-label="Random pick"
                  >
                    <Shuffle className="w-4 h-4 mr-1" />
                    Random
                  </Button>
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

                  <div className="flex-1 min-w-0">
                    {/* Concession-themed loading message */}
                    {moviesLoadingMessage && eligibleMoviesFetching && (
                      <p className="text-sm text-muted-foreground text-center py-4 animate-pulse">
                        {moviesLoadingMessage}
                      </p>
                    )}

                    {/* Empty state messages */}
                    {filteredMovies.length === 0 && allEligibleMovies.length > 0 && (
                      <p className="text-sm text-muted-foreground py-4">
                        {debouncedSearch && (filters.genres.length > 0 || filters.mpaaRatings.length > 0 || filters.runtimeRange[0] !== 0 || filters.runtimeRange[1] !== 300)
                          ? "No movies match your search and filters."
                          : debouncedSearch
                          ? "No movies match your search."
                          : "No movies match your filters. Try adjusting the filters."}
                      </p>
                    )}

                    {/* Movies list — compact table */}
                    {filteredMovies.length === 0 && allEligibleMovies.length === 0 && !eligibleMoviesFetching ? (
                      <p className="text-sm text-muted-foreground py-8 text-center">
                        {selectedActor
                          ? `No eligible movies via ${selectedActor.name}.`
                          : "No eligible movies found for this session."}
                      </p>
                    ) : filteredMovies.length > 0 ? (
                      <div className="rounded-md border border-border overflow-hidden">
                        <table className="w-full text-sm">
                          <thead className="bg-muted/50">
                            <tr>
                              <th className="text-left px-4 py-2 font-medium text-muted-foreground w-14"></th>
                              <th className="text-left px-4 py-2 font-medium text-muted-foreground">Title</th>
                              <th className="text-left px-4 py-2 font-medium text-muted-foreground hidden sm:table-cell">Via</th>
                              <th className="text-right px-4 py-2 font-medium text-muted-foreground hidden lg:table-cell">Rating</th>
                              <th className="text-right px-4 py-2 font-medium text-muted-foreground hidden lg:table-cell">Year</th>
                              <th className="text-right px-4 py-2 font-medium text-muted-foreground hidden xl:table-cell">Runtime</th>
                              <th className="text-right px-4 py-2 font-medium text-muted-foreground hidden xl:table-cell">Rated</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {filteredMovies.map((movie) => (
                              <tr
                                key={movie.tmdb_id}
                                onClick={movie.selectable ? () => handleMovieConfirm(movie) : undefined}
                                className={cn(
                                  "transition-colors",
                                  movie.selectable
                                    ? "cursor-pointer hover:bg-accent/50"
                                    : "opacity-40 cursor-not-allowed"
                                )}
                              >
                                <td className="px-4 py-2">
                                  {movie.poster_path ? (
                                    <img
                                      src={`https://image.tmdb.org/t/p/w92${movie.poster_path}`}
                                      alt={movie.title}
                                      className="w-12 h-[4.5rem] rounded object-cover"
                                    />
                                  ) : (
                                    <div className="w-12 h-[4.5rem] rounded bg-muted" />
                                  )}
                                </td>
                                <td className="px-4 py-2">
                                  <span className="font-medium">{movie.title}</span>
                                  {movie.watched && (
                                    <span className="ml-2 text-xs text-green-400 border border-green-400 rounded px-1">Watched</span>
                                  )}
                                </td>
                                <td className="px-4 py-2 text-muted-foreground italic hidden sm:table-cell">
                                  {movie.via_actor_name ?? (selectedActor?.name ?? "—")}
                                </td>
                                <td className="px-4 py-2 text-right text-amber-400 hidden lg:table-cell">
                                  {movie.vote_average != null ? `★ ${movie.vote_average.toFixed(1)}` : "—"}
                                </td>
                                <td className="px-4 py-2 text-right text-muted-foreground hidden lg:table-cell">
                                  {movie.year ?? "—"}
                                </td>
                                <td className="px-4 py-2 text-right text-muted-foreground hidden xl:table-cell">
                                  {movie.runtime != null ? `${movie.runtime}m` : "—"}
                                </td>
                                <td className="px-4 py-2 text-right text-muted-foreground hidden xl:table-cell">
                                  {movie.mpaa_rating ?? "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : null}

                    {/* Load More pagination — always based on full list, not filtered */}
                    {eligibleMoviesHasMore && (
                      <div className="flex justify-center mt-4">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setMoviesPage((p) => p + 1)}
                        >
                          Load more
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </TabsContent>

          {/* Suggested tab */}
          <TabsContent value="suggested" className="mt-4">
            {suggestionsLoading && (
              <p className="text-muted-foreground text-sm text-center py-8">
                Loading suggestions...
              </p>
            )}
            {!suggestionsLoading && suggestions.length === 0 && (
              <div className="text-center py-12">
                <p className="font-medium text-foreground">No suggestions yet</p>
                <p className="text-sm text-muted-foreground mt-1">Continue the chain to unlock suggestions.</p>
              </div>
            )}
            <div className="flex flex-col gap-2">
              {suggestions.map((movie) => (
                <MovieCard
                  key={movie.tmdb_id}
                  {...movie}
                  selectable={!movie.watched}
                  onClick={!movie.watched ? () => handleMovieConfirm(movie) : undefined}
                />
              ))}
            </div>
          </TabsContent>
        </Tabs>}

        {/* Chain History — bottom of page */}
        {session && session.steps.length > 0 && (
          <ChainHistory steps={session.steps} />
        )}
      </div>

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
              onClick={async () => {
                if (!randomPickMovie) return
                setRandomPickError(null)
                try {
                  await handleMovieConfirm(randomPickMovie)
                  setRandomPickOpen(false)
                } catch {
                  setRandomPickError("Failed to request movie. Try again.")
                }
              }}
            >
              Request This Movie
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

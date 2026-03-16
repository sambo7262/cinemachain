import { useState, useRef, useEffect } from "react"
import { useParams, useNavigate, useLocation } from "react-router-dom"
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { EligibleActorDTO, EligibleMovieDTO, PaginatedMoviesDTO } from "@/lib/api"
import { ChainHistory } from "@/components/ChainHistory"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { X, Clock } from "lucide-react"
import { cn } from "@/lib/utils"

export default function GameSession() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const sid = Number(sessionId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const location = useLocation()

  // Tab + selection state
  const [activeTab, setActiveTab] = useState<"actors" | "movies">("actors")
  const [selectedActor, setSelectedActor] = useState<EligibleActorDTO | null>(null)
  const [sort, setSort] = useState<"rating" | "runtime" | "genre">("rating")
  const [allMovies, setAllMovies] = useState(false)
  const [moviesPage, setMoviesPage] = useState(1)
  const [movieRequestError, setMovieRequestError] = useState<string | null>(null)
  const [radarrStatus, setRadarrStatus] = useState<string | null>(
    (location.state as { radarr_status?: string } | null)?.radarr_status ?? null
  )
  const [view, setView] = useState<"home" | "tabs">("home")
  const radarrFallbackFiredRef = useRef(false)

  // Session polling — stops when awaiting_continue
  const { data: session } = useQuery({
    queryKey: ["session", sid],
    queryFn: api.getActiveSession,
    refetchInterval: (query) =>
      query.state.data?.status === "awaiting_continue" ? false : 5000,
    enabled: !!sid,
  })

  // Derive watched state from session
  const isWatched: boolean = session?.current_movie_watched ?? false

  // Radarr start notification fallback: if location.state failed to deliver the status
  // (confirmed unreliable on NAS hardware), read it from the first successful session poll.
  // Fires at most once per mount (radarrFallbackFiredRef prevents repeat).
  useEffect(() => {
    if (
      session?.radarr_status &&
      !radarrStatus &&
      !radarrFallbackFiredRef.current
    ) {
      radarrFallbackFiredRef.current = true
      setRadarrStatus(
        session.radarr_status === "already_in_radarr"
          ? "Already in your library — waiting for watched event."
          : session.radarr_status === "queued"
          ? "Added to Radarr queue."
          : session.radarr_status
      )
    }
  }, [session?.radarr_status])

  // Safety reset: if session reloads while in tab view and status is awaiting_continue,
  // return to home hub (home hub shows the Continue the chain button).
  useEffect(() => {
    if (session && view === "tabs" && session.status === "awaiting_continue") {
      setView("home")
    }
  }, [session?.status])

  // Eligible actors for the current movie
  const { data: eligibleActors = [] } = useQuery({
    queryKey: ["eligibleActors", sid, session?.current_movie_tmdb_id],
    queryFn: () => api.getEligibleActors(sid),
    enabled: !!sid && session?.status === "active" && isWatched,
  })

  // Eligible movies — scoped to selected actor + sort/filter params
  const { data: eligibleMoviesData } = useQuery<PaginatedMoviesDTO>({
    queryKey: ["eligibleMovies", sid, selectedActor?.tmdb_id, sort, allMovies, moviesPage],
    queryFn: () =>
      api.getEligibleMovies(sid, {
        actor_id: selectedActor?.tmdb_id,
        sort,
        all_movies: allMovies,
        page: moviesPage,
        page_size: 20,
      }),
    enabled: !!sid && !!session && isWatched,
  })
  const eligibleMovies = eligibleMoviesData?.items ?? []
  const eligibleMoviesHasMore = eligibleMoviesData?.has_more ?? false

  // Actor selection switches to Eligible Movies tab
  const handleActorSelect = (actor: EligibleActorDTO) => {
    setSelectedActor(actor)
    setMoviesPage(1)
    setActiveTab("movies")
  }

  // Movie selection: confirm -> pick-actor -> request-movie with error recovery
  const handleMovieConfirm = async (movie: EligibleMovieDTO) => {
    const confirmed = window.confirm(
      `Select "${movie.title}" as your next movie?`
    )
    if (!confirmed) return

    setMovieRequestError(null)
    setRadarrStatus(null)
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
        setRadarrStatus("Already in your library — waiting for watched event.")
      } else if (requestResult?.status === "queued") {
        setRadarrStatus("Added to Radarr queue.")
      }
      setView("home")
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

  // Pause session
  const pauseMutation = useMutation({
    mutationFn: () => api.pauseSession(sid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["session", sid] })
    },
  })

  // Resume session from header (distinct from handleContinue which handles awaiting_continue)
  const resumeMutation = useMutation({
    mutationFn: () => api.resumeSession(sid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["session", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
    },
  })

  // Mark current movie as watched (manual fallback)
  const markWatchedMutation = useMutation({
    mutationFn: () => api.markCurrentWatched(sid),
    onSuccess: (updatedSession) => {
      queryClient.setQueryData(["session", sid], updatedSession)
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] })
    },
  })

  // End session
  const endMutation = useMutation({
    mutationFn: () => api.endSession(sid),
    onSuccess: () => navigate("/"),
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

  // Current movie title from steps
  const currentMovieTitle =
    session?.steps.find(
      (s) => s.movie_tmdb_id === session.current_movie_tmdb_id
    )?.movie_title ?? `Movie ${session?.current_movie_tmdb_id ?? ""}`

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
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-border px-6 py-3 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Now playing: <span className="font-semibold text-foreground">{currentMovieTitle}</span>
        </p>
        <div className="flex items-center gap-2">
          {session?.status === "paused" ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
            >
              {resumeMutation.isPending ? "Resuming..." : "Resume"}
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending || session?.status !== "active"}
            >
              {pauseMutation.isPending ? "Pausing..." : "Pause"}
            </Button>
          )}
          <Button
            variant="destructive"
            size="sm"
            onClick={() => endMutation.mutate()}
            disabled={endMutation.isPending}
          >
            End Session
          </Button>
        </div>
      </header>

      <div className="flex-1 flex flex-col gap-4 px-6 py-4 max-w-3xl w-full mx-auto">
        {/* Chain History */}
        {session && session.steps.length > 0 && (
          <ChainHistory steps={session.steps} />
        )}

        {/* Session state panel — shows context-appropriate guidance */}
        {session && (
          <div className="rounded-lg border border-border px-4 py-3 text-sm">
            {session.status === "paused" && (
              <div className="flex items-center justify-between">
                <p className="text-muted-foreground">
                  Session paused. Resume when you're ready to continue the chain.
                </p>
                <Button size="sm" onClick={() => resumeMutation.mutate()} disabled={resumeMutation.isPending}>
                  {resumeMutation.isPending ? "Resuming..." : "Resume"}
                </Button>
              </div>
            )}

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
              <div className="flex flex-col gap-1">
                <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">Now in queue</p>
                <p className="text-lg font-bold text-foreground">
                  {currentStep?.movie_title ?? `Movie ${session.current_movie_tmdb_id}`}
                </p>
                <p className="text-sm text-muted-foreground">
                  {isStartingMovie
                    ? "Watch this movie, then mark it as watched to start the chain."
                    : "Added to Radarr. Watch it, then mark as watched to continue the chain."}
                </p>
              </div>

              {/* Previous movie (shown only when chain has 2+ movies) */}
              {previousStep && (
                <div className="flex flex-col gap-1 border-t border-border pt-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">Previous movie</p>
                  <p className="text-base font-semibold text-muted-foreground">{previousStep.movie_title}</p>
                </div>
              )}

              {/* Continue the chain CTA — shown when movie has been watched */}
              {session.status === "awaiting_continue" && (
                <Button
                  onClick={() => {
                    handleContinue()
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

        {/* Radarr status notification — auto-displayed after movie selection */}
        {radarrStatus && (
          <div className="flex items-center gap-2 rounded-lg border border-blue-700 bg-blue-950/40 px-4 py-3 text-blue-300">
            <span className="flex-1 text-sm">{radarrStatus}</span>
            <button
              onClick={() => setRadarrStatus(null)}
              className="flex-shrink-0 text-blue-400 hover:text-blue-300"
              aria-label="Dismiss"
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

        {/* Two-tab panel — only shown when in tabs view */}
        {view === "tabs" && <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as "actors" | "movies")}
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
            ) : eligibleActors.length === 0 ? (
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
                      className="ml-auto text-muted-foreground"
                    >
                      Show all eligible movies
                    </Button>
                  )}
                </div>

                {/* Movies list — compact table */}
                {eligibleMovies.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-8 text-center">
                    {selectedActor
                      ? `No eligible movies via ${selectedActor.name}.`
                      : "No eligible movies found."}
                  </p>
                ) : (
                  <div className="rounded-md border border-border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground w-14"></th>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground">Title</th>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground hidden sm:table-cell">Via</th>
                          <th className="text-right px-4 py-2 font-medium text-muted-foreground hidden md:table-cell">Rating</th>
                          <th className="text-right px-4 py-2 font-medium text-muted-foreground hidden md:table-cell">Year</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {eligibleMovies.map((movie) => (
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
                            <td className="px-4 py-2 text-right text-amber-400 hidden md:table-cell">
                              {movie.vote_average != null ? `★ ${movie.vote_average.toFixed(1)}` : "—"}
                            </td>
                            <td className="px-4 py-2 text-right text-muted-foreground hidden md:table-cell">
                              {movie.year ?? "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Load More pagination */}
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
              </>
            )}
          </TabsContent>
        </Tabs>}
      </div>
    </div>
  )
}

import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { EligibleActorDTO, EligibleMovieDTO } from "@/lib/api"
import { ActorCard } from "@/components/ActorCard"
import { MovieCard } from "@/components/MovieCard"
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
import { X } from "lucide-react"

export default function GameSession() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const sid = Number(sessionId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Tab + selection state
  const [activeTab, setActiveTab] = useState<"actors" | "movies">("actors")
  const [selectedActor, setSelectedActor] = useState<EligibleActorDTO | null>(null)
  const [sort, setSort] = useState<"rating" | "runtime" | "genre">("rating")
  const [allMovies, setAllMovies] = useState(false)
  const [movieRequestError, setMovieRequestError] = useState<string | null>(null)

  // Session polling — stops when awaiting_continue
  const { data: session } = useQuery({
    queryKey: ["session", sid],
    queryFn: api.getActiveSession,
    refetchInterval: (query) =>
      query.state.data?.status === "awaiting_continue" ? false : 5000,
    enabled: !!sid,
  })

  // Eligible actors for the current movie
  const { data: eligibleActors = [] } = useQuery({
    queryKey: ["eligibleActors", sid, session?.current_movie_tmdb_id],
    queryFn: () => api.getEligibleActors(sid),
    enabled: !!sid && session?.status === "active",
  })

  // Eligible movies — scoped to selected actor + sort/filter params
  const { data: eligibleMovies = [] } = useQuery({
    queryKey: ["eligibleMovies", sid, selectedActor?.tmdb_id, sort, allMovies],
    queryFn: () =>
      api.getEligibleMovies(sid, {
        actor_id: selectedActor?.tmdb_id,
        sort,
        all_movies: allMovies,
      }),
    enabled: !!sid && activeTab === "movies",
  })

  // Actor selection switches to Eligible Movies tab
  const handleActorSelect = (actor: EligibleActorDTO) => {
    setSelectedActor(actor)
    setActiveTab("movies")
  }

  // Movie selection: confirm -> pick-actor -> request-movie with error recovery
  const handleMovieConfirm = async (movie: EligibleMovieDTO) => {
    const confirmed = window.confirm(
      `Request "${movie.title}"? This will add it to Radarr and wait for you to watch it.`
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
      await api.requestMovie(sid, {
        movie_tmdb_id: movie.tmdb_id,
        movie_title: movie.title,
      })
      queryClient.invalidateQueries({ queryKey: ["session", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
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

  // End session
  const endMutation = useMutation({
    mutationFn: () => api.endSession(sid),
    onSuccess: () => navigate("/"),
  })

  // Continue the chain after watched confirmation
  const handleContinue = () => {
    api.resumeSession(sid).then(() => {
      setSelectedActor(null)
      setActiveTab("actors")
      queryClient.invalidateQueries({ queryKey: ["session", sid] })
      queryClient.invalidateQueries({ queryKey: ["eligibleActors", sid] })
    })
  }

  // Current movie title from steps
  const currentMovieTitle =
    session?.steps.find(
      (s) => s.movie_tmdb_id === session.current_movie_tmdb_id
    )?.movie_title ?? `Movie ${session?.current_movie_tmdb_id ?? ""}`

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold tracking-tight">CinemaChain</h1>
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

        {/* Current movie indicator */}
        {session && (
          <p className="text-sm text-muted-foreground">
            Now:{" "}
            <span className="font-semibold text-foreground">
              {currentMovieTitle}
            </span>
          </p>
        )}

        {/* Session advance banner — shown when Plex marks movie watched */}
        {session?.status === "awaiting_continue" && (
          <div className="bg-green-950 border border-green-700 rounded-lg p-4 flex items-center justify-between">
            <p className="text-green-300">
              <span className="font-semibold">{currentMovieTitle}</span> marked
              as watched —
            </p>
            <Button
              onClick={handleContinue}
              className="bg-green-700 hover:bg-green-600"
            >
              Continue the chain
            </Button>
          </div>
        )}

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

        {/* Two-tab panel */}
        <Tabs
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
            <div className="flex flex-col gap-2">
              {eligibleActors.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  No eligible actors found.
                </p>
              ) : (
                eligibleActors.map((actor) => (
                  <ActorCard
                    key={actor.tmdb_id}
                    {...actor}
                    onClick={() => handleActorSelect(actor)}
                  />
                ))
              )}
            </div>
          </TabsContent>

          {/* Eligible Movies tab */}
          <TabsContent value="movies" className="mt-3">
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
                  onClick={() => setSelectedActor(null)}
                  className="ml-auto text-muted-foreground"
                >
                  Clear actor filter
                </Button>
              )}
            </div>

            {/* Movies list */}
            <div className="flex flex-col gap-2">
              {eligibleMovies.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  {selectedActor
                    ? `No eligible movies via ${selectedActor.name}.`
                    : "No eligible movies found."}
                </p>
              ) : (
                eligibleMovies.map((movie) => (
                  <div
                    key={movie.tmdb_id}
                    className={movie.watched ? "opacity-50" : undefined}
                  >
                    <MovieCard
                      {...movie}
                      onClick={
                        movie.selectable
                          ? () => handleMovieConfirm(movie)
                          : undefined
                      }
                    />
                  </div>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

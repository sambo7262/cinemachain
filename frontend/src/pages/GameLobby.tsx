import { useState, useEffect, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { MovieCard } from "@/components/MovieCard"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

function toast(message: string) {
  alert(message)
}

export default function GameLobby() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Active session detection
  const { data: activeSession } = useQuery({
    queryKey: ["activeSession"],
    queryFn: api.getActiveSession,
    staleTime: 0,
  })

  // Watched movies
  const { data: watchedMovies, isLoading: watchedLoading } = useQuery({
    queryKey: ["watchedMovies"],
    queryFn: api.getWatchedMovies,
  })

  // Search state
  const [searchInput, setSearchInput] = useState("")
  const [debouncedQuery, setDebouncedQuery] = useState("")

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchInput.trim())
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ["movieSearch", debouncedQuery],
    queryFn: () => api.searchMovies(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  })

  // CSV state
  const [csvRows, setCsvRows] = useState<
    Array<{ movieName: string; actorName: string; order: number }>
  >([])
  const [csvFileName, setCsvFileName] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const parseCSV = useCallback((text: string) => {
    const lines = text.trim().split("\n").slice(1)
    return lines
      .map((line) => {
        const [movieName, actorName, order] = line
          .split(",")
          .map((s) => s.trim().replace(/^"|"$/g, ""))
        return {
          movieName: movieName ?? "",
          actorName: actorName ?? "",
          order: parseInt(order ?? "0") || 0,
        }
      })
      .filter((r) => r.movieName)
  }, [])

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      setCsvFileName(file.name)
      const reader = new FileReader()
      reader.onload = (ev) => {
        const text = ev.target?.result as string
        setCsvRows(parseCSV(text))
      }
      reader.readAsText(file)
    },
    [parseCSV],
  )

  // Create session mutation
  const createMutation = useMutation({
    mutationFn: (tmdb_id: number) =>
      api.createSession({ start_movie_tmdb_id: tmdb_id }),
    onSuccess: (session) => navigate(`/game/${session.id}`),
    onError: (err: Error & { status?: number }) => {
      if (err.status === 409)
        toast("A session is already in progress — resume or end it first.")
      else toast("Failed to start session.")
    },
  })

  // Import CSV mutation
  const importMutation = useMutation({
    mutationFn: () => api.importCsv(csvRows),
    onSuccess: (session) => navigate(`/game/${session.id}`),
    onError: () => toast("Failed to import CSV chain."),
  })

  // End session mutation
  const endMutation = useMutation({
    mutationFn: (sessionId: number) => api.endSession(sessionId),
    onSuccess: () => {
      // Synchronously clear the cache so the banner disappears on this render cycle.
      // Do NOT use refetchQueries or async onSuccess — those are subject to timing
      // races with staleTime and React batch updates on NAS hardware.
      queryClient.setQueryData(["activeSession"], null)
      queryClient.invalidateQueries({ queryKey: ["activeSession"] })
    },
    onError: () => toast("Failed to end session."),
  })

  const isSessionActive =
    activeSession !== null &&
    activeSession !== undefined &&
    ["active", "paused", "awaiting_continue"].includes(activeSession.status)

  const currentMovieTitle =
    activeSession?.steps?.[0]?.movie_title ?? "Unknown movie"

  return (
    <div className="min-h-screen flex flex-col items-center justify-start p-6 gap-8">
      {/* Header */}
      <div className="text-center mt-8">
        <h1 className="text-3xl font-bold tracking-tight">CinemaChain</h1>
        <p className="text-muted-foreground mt-1">
          Navigate cinema through shared actors
        </p>
      </div>

      <div className="w-full max-w-2xl">
        {/* Active session banner */}
        {isSessionActive ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Session in progress</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <p className="text-muted-foreground">
                Current movie:{" "}
                <span className="text-foreground font-medium">
                  {currentMovieTitle}
                </span>
              </p>
              <div className="flex gap-3">
                <Button onClick={() => navigate(`/game/${activeSession.id}`)}>
                  Continue
                </Button>
                <Button
                  variant="outline"
                  disabled={endMutation.isPending}
                  onClick={() => endMutation.mutate(activeSession.id)}
                >
                  {endMutation.isPending ? "Ending..." : "End Session"}
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          /* Three-tab start panel */
          <Tabs defaultValue="watched">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="watched">Watch History</TabsTrigger>
              <TabsTrigger value="search">Search Title</TabsTrigger>
              <TabsTrigger value="csv">Import Chain</TabsTrigger>
            </TabsList>

            {/* Tab: Watch History */}
            <TabsContent value="watched" className="mt-4">
              {watchedLoading && (
                <p className="text-muted-foreground text-sm text-center py-8">
                  Loading watch history...
                </p>
              )}
              {!watchedLoading && (!watchedMovies || watchedMovies.length === 0) && (
                <p className="text-muted-foreground text-sm text-center py-8">
                  No watched movies found. Watch something in Plex first, or
                  mark movies as watched.
                </p>
              )}
              <div className="flex flex-col gap-2">
                {watchedMovies?.map((movie) => (
                  <MovieCard
                    key={movie.tmdb_id}
                    {...movie}
                    watched
                    onClick={() => createMutation.mutate(movie.tmdb_id)}
                    selectable={!createMutation.isPending}
                  />
                ))}
              </div>
              {createMutation.isPending && (
                <p className="text-muted-foreground text-sm text-center mt-4">
                  Starting session...
                </p>
              )}
            </TabsContent>

            {/* Tab: Search Title */}
            <TabsContent value="search" className="mt-4">
              <Input
                placeholder="Search for a movie title..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="mb-4"
              />
              {searchLoading && (
                <p className="text-muted-foreground text-sm text-center py-4">
                  Searching...
                </p>
              )}
              {debouncedQuery.length >= 2 &&
                !searchLoading &&
                (!searchResults || searchResults.length === 0) && (
                  <p className="text-muted-foreground text-sm text-center py-4">
                    No movies found for "{debouncedQuery}".
                  </p>
                )}
              <div className="flex flex-col gap-2">
                {searchResults?.map((movie) => (
                  <MovieCard
                    key={movie.tmdb_id}
                    {...movie}
                    onClick={() => createMutation.mutate(movie.tmdb_id)}
                    selectable={!createMutation.isPending}
                  />
                ))}
              </div>
              {createMutation.isPending && (
                <p className="text-muted-foreground text-sm text-center mt-4">
                  Starting session...
                </p>
              )}
            </TabsContent>

            {/* Tab: Import Chain */}
            <TabsContent value="csv" className="mt-4">
              <div className="flex flex-col gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    Upload a CSV with columns: Movie Name, Actor Name, Order
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {csvFileName ?? "Choose CSV file"}
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </div>

                {csvRows.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">
                      Parsed {csvRows.length} row
                      {csvRows.length !== 1 ? "s" : ""}:
                    </p>
                    <div className="max-h-48 overflow-y-auto flex flex-col gap-1">
                      {csvRows.map((row, i) => (
                        <div
                          key={i}
                          className="text-xs text-muted-foreground bg-muted rounded px-2 py-1"
                        >
                          <span className="text-foreground font-medium">
                            {row.movieName}
                          </span>
                          {row.actorName && ` — via ${row.actorName}`}
                          {row.order > 0 && ` (#${row.order})`}
                        </div>
                      ))}
                    </div>
                    <Button
                      className="mt-4 w-full"
                      disabled={importMutation.isPending}
                      onClick={() => importMutation.mutate()}
                    >
                      {importMutation.isPending
                        ? "Importing..."
                        : "Import Chain"}
                    </Button>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  )
}

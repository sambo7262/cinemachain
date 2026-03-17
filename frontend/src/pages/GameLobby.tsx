import { useState, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, type GameSessionDTO, type CsvValidationResponse, type CsvOverride } from "@/lib/api"
import { MovieCard } from "@/components/MovieCard"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { useLoadingMessages } from "@/hooks/useLoadingMessages"

function toast(message: string) {
  alert(message)
}

interface ParsedRow {
  order: number
  movieName: string
  actorName: string
  isValid: boolean
}

function parseCSV(text: string): ParsedRow[] {
  const lines = text.trim().split("\n")
  const headers = lines[0].split(",").map(h => h.trim().toLowerCase().replace(/^"|"$/g, ""))
  const orderIdx = headers.indexOf("order")
  const movieIdx = headers.findIndex(h => h.includes("movie"))
  const actorIdx = headers.findIndex(h => h.includes("actor"))
  // Each row has order, movie_name, actor_name on the same line.
  // Validation: every row must have a movie name.
  return lines.slice(1)
    .map((line, i) => {
      const cols = line.split(",").map(c => c.trim().replace(/^"|"$/g, ""))
      const movieName = movieIdx >= 0 ? (cols[movieIdx] ?? "") : ""
      const actorName = actorIdx >= 0 ? (cols[actorIdx] ?? "") : ""
      return {
        order: orderIdx >= 0 ? (parseInt(cols[orderIdx] ?? "") || i + 1) : i + 1,
        movieName,
        actorName,
        isValid: movieName.length > 0,
      }
    })
    .filter(r => r.movieName || r.actorName)
}

function currentMovieForSession(session: GameSessionDTO): string {
  const step = session.steps.find(s => s.movie_tmdb_id === session.current_movie_tmdb_id)
  return step?.movie_title ?? session.steps[0]?.movie_title ?? "(untitled)"
}

export default function GameLobby() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Session grid query — MUST be "activeSessions" (plural)
  const { data: activeSessions = [] } = useQuery({
    queryKey: ["activeSessions"],
    queryFn: api.listSessions,
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

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const handleSearchInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchInput(e.target.value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setDebouncedQuery(e.target.value.trim())
    }, 300)
  }, [])

  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ["movieSearch", debouncedQuery],
    queryFn: () => api.searchMovies(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  })

  // View state: "grid" shows session grid; "form" shows new-session form
  const [view, setView] = useState<"grid" | "form">("grid")
  const [defaultTab, setDefaultTab] = useState<"watched" | "search" | "csv">("watched")

  // Session name state
  const [sessionName, setSessionName] = useState("")

  const isNameTaken = activeSessions.some(
    s => s.name.toLowerCase() === sessionName.trim().toLowerCase()
  )
  const isNameValid = sessionName.trim().length > 0 && !isNameTaken

  // CSV state
  const [csvRows, setCsvRows] = useState<ParsedRow[]>([])
  const [csvFileName, setCsvFileName] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [validationResult, setValidationResult] = useState<CsvValidationResponse | null>(null)
  const [overrides, setOverrides] = useState<CsvOverride[]>([])

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      setCsvFileName(file.name)
      const reader = new FileReader()
      reader.onload = (ev) => {
        const text = ev.target?.result as string
        setCsvRows(parseCSV(text))
        setValidationResult(null)
        setOverrides([])
      }
      reader.readAsText(file)
    },
    [],
  )

  // Create session mutation
  const createMutation = useMutation({
    mutationFn: ({ tmdb_id, title }: { tmdb_id: number; title?: string }) =>
      api.createSession({ start_movie_tmdb_id: tmdb_id, name: sessionName.trim(), start_movie_title: title }),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ["activeSessions"] })
      navigate(`/game/${session.id}`, { state: { radarr_status: session.radarr_status ?? null } })
    },
    onError: (err: Error & { status?: number }) => {
      if (err.status === 409) toast("Session name already in use.")
      else toast("Failed to start session.")
    },
  })

  // Import CSV mutation
  const importMutation = useMutation({
    mutationFn: () => api.importCsv(csvRows, sessionName.trim() || "Imported Chain", overrides),
    onSuccess: (result) => {
      if ("status" in result && result.status === "validation_required") {
        setValidationResult(result as CsvValidationResponse)
      } else {
        const session = result as GameSessionDTO
        queryClient.invalidateQueries({ queryKey: ["activeSessions"] })
        navigate(`/game/${session.id}`)
      }
    },
    onError: () => toast("Failed to import CSV chain."),
  })

  const csvLoadingMessage = useLoadingMessages(importMutation.isPending)

  const handleOverridePick = (row: number, tmdb_id: number) => {
    setOverrides(prev => {
      const filtered = prev.filter(o => o.row !== row)
      return [...filtered, { row, tmdb_id }]
    })
  }

  const allOverridesResolved = validationResult
    ? validationResult.unresolved.every(u => overrides.some(o => o.row === u.row))
    : false

  // Archive mutation
  const archiveMutation = useMutation({
    mutationFn: (sessionId: number) => api.archiveSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activeSessions"] })
      queryClient.invalidateQueries({ queryKey: ["archivedSessions"] })
    },
  })

  const isSequenceValid = !csvRows.some(r => !r.isValid)

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
        {view === "grid" ? (
          /* Session grid view */
          <div className="flex flex-col gap-4">
            {activeSessions.length === 0 ? (
              <p className="text-muted-foreground text-sm text-center py-6">
                No active sessions. Start one to begin.
              </p>
            ) : (
              <div className="flex flex-col gap-3">
                {activeSessions.map((session) => (
                  <Card key={session.id} className="cursor-pointer hover:border-primary/50 transition-colors">
                    <CardContent className="flex items-center justify-between py-4 px-5">
                      <div className="flex flex-col gap-1">
                        <span className="font-semibold text-foreground">{session.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center rounded-md bg-primary/10 text-primary text-xs font-medium px-2 py-0.5 ring-1 ring-inset ring-primary/20">
                            {session.current_movie_title ?? currentMovieForSession(session)}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {session.steps.length} step{session.steps.length !== 1 ? "s" : ""}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation()
                            archiveMutation.mutate(session.id)
                          }}
                          disabled={archiveMutation.isPending}
                        >
                          Archive
                        </Button>
                        <Button size="sm" onClick={() => navigate(`/game/${session.id}`)}>
                          Continue →
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
            <Button
              variant="outline"
              className="self-start"
              onClick={() => {
                setSessionName("")
                setCsvRows([])
                setCsvFileName(null)
                setDefaultTab("watched")
                setView("form")
              }}
            >
              + Start a new session
            </Button>
            {/* Standalone Import Chain card (BUG-5) */}
            <Card
              className="cursor-pointer hover:border-primary/50 transition-colors border-dashed"
              onClick={() => {
                setSessionName("")
                setCsvRows([])
                setCsvFileName(null)
                setDefaultTab("csv")
                setView("form")
              }}
            >
              <CardContent className="flex items-center gap-3 py-4 px-5">
                <div className="flex flex-col gap-0.5">
                  <span className="font-medium text-foreground">Import a chain</span>
                  <span className="text-sm text-muted-foreground">
                    Create a session from a CSV export
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          /* New session form (inline expansion) */
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <button
                className="text-sm text-muted-foreground hover:text-foreground"
                onClick={() => setView("grid")}
              >
                ← Back
              </button>
              <h2 className="text-xl font-semibold">Start a new session</h2>
            </div>

            {/* Session name input */}
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Session name</label>
              <Input
                placeholder="e.g. Friday Night Chain"
                value={sessionName}
                maxLength={100}
                onChange={(e) => setSessionName(e.target.value)}
                className={cn(isNameTaken && sessionName.trim().length > 0 && "border-red-500")}
              />
              {sessionName.trim().length > 0 && isNameTaken && (
                <p className="text-xs text-red-500">
                  A session with this name is already active. Choose a different name.
                </p>
              )}
              {sessionName.trim().length === 0 && (
                <p className="text-xs text-muted-foreground">Required — enter a name to continue.</p>
              )}
            </div>

            {/* Movie picker — only rendered once name is valid */}
            {isNameValid && <div>
              <Tabs key={defaultTab} defaultValue={defaultTab}>
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
                      No watched movies found. Watch something in Plex first, or mark movies as watched.
                    </p>
                  )}
                  <div className="flex flex-col gap-2">
                    {watchedMovies?.map((movie) => (
                      <MovieCard
                        key={movie.tmdb_id}
                        {...movie}
                        watched
                        onClick={() => createMutation.mutate({ tmdb_id: movie.tmdb_id, title: movie.title })}
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
                    onChange={handleSearchInput}
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
                        onClick={() => createMutation.mutate({ tmdb_id: movie.tmdb_id, title: movie.title })}
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
                        Upload a CSV with columns: order, movie_name, actor_name
                      </p>
                      <Button
                        variant="outline"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={importMutation.isPending}
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

                    {/* Loading state */}
                    {importMutation.isPending && (
                      <p className="text-sm text-muted-foreground text-center py-2 animate-pulse">
                        {csvLoadingMessage ?? "Validating your session history..."}
                      </p>
                    )}

                    {/* Validation report — shown when backend returns validation_required */}
                    {validationResult && !importMutation.isPending && (
                      <div className="flex flex-col gap-3">
                        <p className="text-sm text-amber-400">
                          {validationResult.resolved_count} row{validationResult.resolved_count !== 1 ? "s" : ""} resolved automatically.
                          The following {validationResult.unresolved.length} row{validationResult.unresolved.length !== 1 ? "s" : ""} need your input — each row = one movie in the chain.
                        </p>
                        <div className="flex flex-col gap-2 max-h-64 overflow-y-auto">
                          {validationResult.unresolved.map((u) => {
                            const picked = overrides.find(o => o.row === u.row)
                            return (
                              <div key={u.row} className="flex flex-col gap-1 rounded bg-muted px-3 py-2">
                                <span className="text-xs text-muted-foreground">Row {u.row + 1}: <span className="text-foreground font-medium">{u.csv_title}</span></span>
                                {u.suggestions.length === 0 ? (
                                  <span className="text-xs text-red-400">No TMDB results found.</span>
                                ) : (
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {u.suggestions.map(s => (
                                      <button
                                        key={s.tmdb_id}
                                        onClick={() => handleOverridePick(u.row, s.tmdb_id)}
                                        className={cn(
                                          "text-xs rounded px-2 py-1 border transition-colors",
                                          picked?.tmdb_id === s.tmdb_id
                                            ? "bg-primary text-primary-foreground border-primary"
                                            : "bg-background border-border hover:border-primary/50"
                                        )}
                                      >
                                        {s.title}{s.year ? ` (${s.year})` : ""}
                                      </button>
                                    ))}
                                  </div>
                                )}
                                {/* Direct TMDB ID input — overrides suggestion button selection */}
                                <div className="flex items-center gap-2 mt-2">
                                  <label className="text-xs text-muted-foreground whitespace-nowrap">
                                    Or enter TMDB ID directly:
                                  </label>
                                  <input
                                    type="number"
                                    min="1"
                                    placeholder="e.g. 550"
                                    className="text-xs rounded border border-border bg-background px-2 py-1 w-28 focus:outline-none focus:ring-1 focus:ring-primary"
                                    onChange={(e) => {
                                      const val = parseInt(e.target.value, 10)
                                      if (!isNaN(val) && val > 0) {
                                        handleOverridePick(u.row, val)
                                      }
                                    }}
                                  />
                                </div>
                              </div>
                            )
                          })}
                        </div>
                        <Button
                          className="w-full"
                          disabled={importMutation.isPending || !allOverridesResolved || !isNameValid}
                          onClick={() => importMutation.mutate()}
                        >
                          {importMutation.isPending ? "Importing..." : "Confirm and Import"}
                        </Button>
                      </div>
                    )}

                    {/* Normal pre-validation row preview */}
                    {csvRows.length > 0 && !validationResult && !importMutation.isPending && (
                      <div className="flex flex-col gap-2">
                        {csvRows.some(r => !r.isValid) && (
                          <p className="text-xs text-amber-400">Fix invalid rows before importing. Delete rows to fix the sequence.</p>
                        )}
                        <div className="max-h-48 overflow-y-auto flex flex-col gap-1">
                          {csvRows.map((row, i) => (
                            <div
                              key={i}
                              className={cn(
                                "flex items-center justify-between text-xs rounded px-2 py-1 bg-muted",
                                !row.isValid && "border border-red-600 bg-red-950/20"
                              )}
                            >
                              <span>
                                {row.movieName
                                  ? <span className="text-foreground font-medium">{row.movieName}</span>
                                  : <span className="text-muted-foreground italic">via {row.actorName}</span>
                                }
                              </span>
                              <button
                                onClick={() => setCsvRows(rows => rows.filter((_, j) => j !== i))}
                                className="text-muted-foreground hover:text-foreground ml-2"
                                aria-label="Remove row"
                              >x</button>
                            </div>
                          ))}
                        </div>
                        <Button
                          className="w-full"
                          disabled={importMutation.isPending || !isSequenceValid || !isNameValid}
                          onClick={() => importMutation.mutate()}
                        >
                          Import Chain
                        </Button>
                      </div>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </div>}
          </div>
        )}
      </div>
    </div>
  )
}

import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, type SettingsDTO, type ServiceValidationResult } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

const ENV_NOTICE_KEY = "cinemachain_env_notice_dismissed"

type ValidationState = { status: 'idle' | 'testing' | 'ok' | 'error' | 'warning'; message?: string }
const initialValidation: ValidationState = { status: 'idle' }

function ValidationBadge({ state, onTest, service }: { state: ValidationState; onTest: () => void; service: string }) {
  return (
    <div className="space-y-2 pt-1">
      <Button
        variant="outline"
        size="sm"
        disabled={state.status === 'testing'}
        onClick={onTest}
        className={
          state.status === 'ok' ? 'border-green-500 text-green-600' :
          state.status === 'error' ? 'border-red-500 text-red-600' :
          state.status === 'warning' ? 'border-yellow-500 text-yellow-600' :
          ''
        }
      >
        {state.status === 'testing' ? 'Testing...' :
         state.status === 'ok' ? 'Connected' :
         state.status === 'error' ? 'Test Failed' :
         state.status === 'warning' ? 'Warning' :
         `Test ${service}`}
      </Button>
      {state.message && state.status !== 'ok' && (
        <p className={`text-xs ${state.status === 'error' ? 'text-red-500' : 'text-yellow-600'}`}>
          {state.message}
        </p>
      )}
    </div>
  )
}

type FieldErrors = Partial<Record<keyof SettingsDTO, string>>

const emptyForm: SettingsDTO = {
  tmdb_api_key: "",
  radarr_url: "",
  radarr_api_key: "",
  radarr_quality_profile: "",
  tmdb_cache_time: "",
  tmdb_cache_top_n: "",
  tmdb_cache_top_actors: "",
  mdblist_api_key: "",
  tmdb_suggestions_seed_count: "",
  mdblist_schedule_time: "",
  mdblist_refetch_days: "",
}

function nullToEmpty(settings: SettingsDTO): SettingsDTO {
  const result: SettingsDTO = { ...emptyForm }
  for (const key of Object.keys(emptyForm) as Array<keyof SettingsDTO>) {
    result[key] = settings[key] ?? ""
  }
  return result
}

interface DbHealth {
  row_health: {
    total_movies: number
    missing_overview: number
    missing_mpaa: number
    missing_imdb_id: number
    missing_imdb_rating: number
    missing_rt_score: number
    never_mdblist_fetched: number
    total_actors: number
  }
  table_sizes: {
    total_db: string
    movies: string
    credits: string
    actors: string
    watch_events: string
  }
}

export function Settings() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<SettingsDTO>(emptyForm)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [noticeDismissed, setNoticeDismissed] = useState(
    () => localStorage.getItem(ENV_NOTICE_KEY) === "true"
  )

  // API key validation state
  const [tmdbValidation, setTmdbValidation] = useState<ValidationState>(initialValidation)
  const [radarrValidation, setRadarrValidation] = useState<ValidationState>(initialValidation)
  const [mdblistValidation, setMdblistValidation] = useState<ValidationState>(initialValidation)

  // MDBList backfill state
  const [backfillRunning, setBackfillRunning] = useState(false)
  const [backfillStatus, setBackfillStatus] = useState<{
    fetched: number
    total: number
    calls_used_today: number
    daily_limit: number
  } | null>(null)
  const [showConfirm, setShowConfirm] = useState(false)
  const [backfillDone, setBackfillDone] = useState(false)

  // TMDB cache state
  const [cacheRunning, setCacheRunning] = useState(false)
  const [cacheLastRunAt, setCacheLastRunAt] = useState<string | null>(null)
  const [cacheLastDurationS, setCacheLastDurationS] = useState<number | null>(null)

  // DB health state
  const [dbHealth, setDbHealth] = useState<DbHealth | null>(null)
  const [dbHealthLoading, setDbHealthLoading] = useState(false)

  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: api.getSettings,
  })

  const { data: settingsStatus } = useQuery({
    queryKey: ["settingsStatus"],
    queryFn: api.getSettingsStatus,
  })

  useEffect(() => {
    if (settings) {
      setFormData(nullToEmpty(settings))
    }
  }, [settings])

  // On mount: check if MDBList backfill is already running and load current quota
  useEffect(() => {
    api.mdblist.getBackfillStatus().then(status => {
      if (status.running) {
        setBackfillRunning(true)
        setBackfillStatus({ fetched: status.fetched, total: status.total, calls_used_today: status.calls_used_today, daily_limit: status.daily_limit })
      } else {
        setBackfillStatus({ fetched: status.fetched, total: status.total, calls_used_today: status.calls_used_today, daily_limit: status.daily_limit })
      }
    }).catch(() => {})
  }, [])

  // On mount: check TMDB cache status
  useEffect(() => {
    api.cache.getStatus().then(status => {
      setCacheRunning(status.running)
      setCacheLastRunAt(status.last_run_at)
      setCacheLastDurationS(status.last_run_duration_s)
    }).catch(() => {})
  }, [])

  // Poll MDBList backfill status every 2000ms while running
  useEffect(() => {
    if (!backfillRunning) return
    const interval = setInterval(async () => {
      const status = await api.mdblist.getBackfillStatus()
      setBackfillStatus({ fetched: status.fetched, total: status.total, calls_used_today: status.calls_used_today, daily_limit: status.daily_limit })
      if (!status.running) {
        setBackfillRunning(false)
        setBackfillDone(true)
        clearInterval(interval)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [backfillRunning])

  // Poll TMDB cache status every 2000ms while running
  useEffect(() => {
    if (!cacheRunning) return
    const interval = setInterval(async () => {
      const status = await api.cache.getStatus()
      setCacheLastRunAt(status.last_run_at)
      setCacheLastDurationS(status.last_run_duration_s)
      if (!status.running) {
        setCacheRunning(false)
        clearInterval(interval)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [cacheRunning])

  const saveMutation = useMutation({
    mutationFn: () => api.saveSettings(formData),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] })
      queryClient.invalidateQueries({ queryKey: ["settingsStatus"] })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
      // Auto-validate all configured services
      setTmdbValidation({ status: 'testing' })
      setRadarrValidation({ status: 'testing' })
      setMdblistValidation({ status: 'testing' })
      try {
        const results = await api.validateAllServices(formData)
        for (const [svc, res] of Object.entries(results) as Array<["tmdb" | "radarr" | "mdblist", ServiceValidationResult]>) {
          const setFn = svc === "tmdb" ? setTmdbValidation : svc === "radarr" ? setRadarrValidation : setMdblistValidation
          if (res.ok && res.warning) {
            setFn({ status: 'warning', message: res.warning })
          } else if (res.ok) {
            setFn({ status: 'ok', message: 'Connected' })
          } else {
            setFn({ status: 'error', message: res.error ?? 'Connection failed' })
          }
        }
      } catch {
        // silently fail validation on save — settings were still saved
        setTmdbValidation(initialValidation)
        setRadarrValidation(initialValidation)
        setMdblistValidation(initialValidation)
      }
    },
  })

  const handleChange = (field: keyof SettingsDTO) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [field]: e.target.value }))
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }))
  }

  const handleSave = () => {
    const errors: FieldErrors = {}
    if (!formData.tmdb_api_key?.trim()) errors.tmdb_api_key = "This field is required."
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return
    saveMutation.mutate()
  }

  const handleTest = async (service: "tmdb" | "radarr" | "mdblist") => {
    const setFn = service === "tmdb" ? setTmdbValidation : service === "radarr" ? setRadarrValidation : setMdblistValidation
    setFn({ status: 'testing' })
    try {
      const result = await api.validateService(service, formData)
      if (result.ok && result.warning) {
        setFn({ status: 'warning', message: result.warning })
      } else if (result.ok) {
        setFn({ status: 'ok', message: 'Connected' })
      } else {
        setFn({ status: 'error', message: result.error ?? 'Connection failed' })
      }
    } catch {
      setFn({ status: 'error', message: 'Request failed — check your network' })
    }
  }

  const handleBackfillClick = async () => {
    // Fetch latest status before showing confirm dialog so counts are fresh
    try {
      const status = await api.mdblist.getBackfillStatus()
      setBackfillStatus({ fetched: status.fetched, total: status.total, calls_used_today: status.calls_used_today, daily_limit: status.daily_limit })
    } catch {
      // proceed with stale / null status
    }
    setBackfillDone(false)
    setShowConfirm(true)
  }

  const handleBackfillConfirm = async () => {
    setShowConfirm(false)
    try {
      await api.mdblist.startBackfill()
      setBackfillRunning(true)
      setBackfillDone(false)
    } catch {
      // silently fail — user will see button re-enabled
    }
  }

  const handleRunCacheNow = async () => {
    try {
      await api.cache.runNow()
      setCacheRunning(true)
    } catch {
      // silently fail
    }
  }

  const handleRefreshDbHealth = async () => {
    setDbHealthLoading(true)
    try {
      const health = await api.getDbHealth()
      setDbHealth(health)
    } catch {
      // silently fail
    } finally {
      setDbHealthLoading(false)
    }
  }

  const showMigrationNotice =
    !noticeDismissed && settingsStatus?.migrated_from_env === true

  const dismissNotice = () => {
    localStorage.setItem(ENV_NOTICE_KEY, "true")
    setNoticeDismissed(true)
  }

  const fmtPct = (count: number, total: number) => {
    if (!total) return String(count)
    const pct = Math.round((count / total) * 100)
    return `${count.toLocaleString()} (${pct}%)`
  }

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-6">
      <h1 className="text-xl font-semibold mb-6">Settings</h1>

      {showMigrationNotice && (
        <div className="flex items-start justify-between gap-2 bg-secondary/50 rounded-md px-4 py-2">
          <p className="text-sm text-muted-foreground">
            Your existing .env configuration has been imported automatically.
          </p>
          <button
            onClick={dismissNotice}
            className="text-xs text-muted-foreground hover:text-foreground shrink-0"
            aria-label="Dismiss migration notice"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Card 1: TMDB */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">TMDB</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="tmdb-api-key" className="text-xs">API Key</label>
            <Input
              id="tmdb-api-key"
              type="password"
              value={formData.tmdb_api_key ?? ""}
              onChange={handleChange("tmdb_api_key")}
            />
            <p className="text-xs text-muted-foreground">Required. Found in your TMDB account under Settings &gt; API.</p>
            {fieldErrors.tmdb_api_key && (
              <p className="text-red-500 text-xs">{fieldErrors.tmdb_api_key}</p>
            )}
          </div>
          <div className="space-y-1">
            <label htmlFor="tmdb-cache-time" className="text-xs">Cache time (Los Angeles)</label>
            <Input
              id="tmdb-cache-time"
              value={formData.tmdb_cache_time ?? ""}
              onChange={handleChange("tmdb_cache_time")}
              placeholder="03:00"
            />
            <p className="text-xs text-muted-foreground">Time to run nightly TMDB cache sync (HH:MM, 24h format, Los Angeles time)</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="tmdb-cache-top-n" className="text-xs">Top N movies</label>
            <Input
              id="tmdb-cache-top-n"
              type="number"
              value={formData.tmdb_cache_top_n ?? ""}
              onChange={handleChange("tmdb_cache_top_n")}
              placeholder="5000"
            />
            <p className="text-xs text-muted-foreground">Number of top-voted movies to pre-cache nightly</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="tmdb-cache-top-actors" className="text-xs">Top K actors</label>
            <Input
              id="tmdb-cache-top-actors"
              type="number"
              value={formData.tmdb_cache_top_actors ?? ""}
              onChange={handleChange("tmdb_cache_top_actors")}
              placeholder="1500"
            />
            <p className="text-xs text-muted-foreground">Number of top actors to pre-fetch filmographies nightly</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="tmdb-suggestions-seed-count" className="text-xs">Suggestions seed count</label>
            <Input
              id="tmdb-suggestions-seed-count"
              type="number"
              min={1}
              max={20}
              value={formData.tmdb_suggestions_seed_count ?? ""}
              onChange={handleChange("tmdb_suggestions_seed_count")}
              placeholder="5"
            />
            <p className="text-xs text-muted-foreground">
              How many recently watched movies to use as recommendation seeds (1–20, default 5).
              Takes effect on the next movie watched.
            </p>
          </div>

          {/* TMDB on-demand run */}
          <div className="space-y-2 pt-1">
            <Button
              variant="outline"
              size="sm"
              disabled={cacheRunning}
              onClick={handleRunCacheNow}
            >
              {cacheRunning ? "Running..." : "Run TMDB Cache Now"}
            </Button>
            {cacheLastRunAt && (
              <p className="text-xs text-muted-foreground">
                Last run: {new Date(cacheLastRunAt).toLocaleString()}
                {cacheLastDurationS != null ? ` (${cacheLastDurationS.toFixed(0)}s)` : ""}
              </p>
            )}
          </div>
          <ValidationBadge state={tmdbValidation} onTest={() => handleTest("tmdb")} service="TMDB" />
        </CardContent>
      </Card>

      {/* Card 2: MDBList */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">MDBList</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="mdblist-api-key" className="text-xs">API Key</label>
            <Input
              id="mdblist-api-key"
              type="password"
              value={formData.mdblist_api_key ?? ""}
              onChange={handleChange("mdblist_api_key")}
            />
            <p className="text-xs text-muted-foreground">Optional. Enables Rotten Tomatoes scores on movies. Get your key at mdblist.com.</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="mdblist-schedule-time" className="text-xs">Schedule time (Los Angeles)</label>
            <Input
              id="mdblist-schedule-time"
              value={formData.mdblist_schedule_time ?? ""}
              onChange={handleChange("mdblist_schedule_time")}
              placeholder="04:00"
            />
            <p className="text-xs text-muted-foreground">Time to run nightly MDBList backfill (HH:MM, 24h format, Los Angeles time)</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="mdblist-refetch-days" className="text-xs">Stale refetch days</label>
            <Input
              id="mdblist-refetch-days"
              type="number"
              value={formData.mdblist_refetch_days ?? ""}
              onChange={handleChange("mdblist_refetch_days")}
              placeholder="90"
            />
            <p className="text-xs text-muted-foreground">Days before a previously fetched movie is considered stale and re-fetched</p>
          </div>

          {/* Quota display (read-only) */}
          {backfillStatus && (
            <p className="text-xs text-muted-foreground">
              Calls today: {backfillStatus.calls_used_today} / {backfillStatus.daily_limit}
            </p>
          )}

          {/* Backfill trigger */}
          <div className="space-y-3 pt-1">
            <Button
              variant="outline"
              size="sm"
              disabled={backfillRunning}
              onClick={handleBackfillClick}
            >
              {backfillRunning ? "Refreshing..." : "Run MDBList Backfill Now"}
            </Button>

            {/* Confirm dialog */}
            {showConfirm && (
              <div className="rounded-md border border-border bg-secondary/30 p-4 space-y-3 text-sm">
                <p className="font-medium">Refresh ratings for all movies?</p>
                <p className="text-muted-foreground">
                  This will fetch ratings for approximately{" "}
                  <span className="text-foreground font-medium">{backfillStatus?.total ?? "?"}</span> movies.
                </p>
                <p className="text-muted-foreground">
                  Quota:{" "}
                  <span className="text-foreground font-medium">
                    {backfillStatus?.calls_used_today ?? 0} of {backfillStatus?.daily_limit ?? 10000}
                  </span>{" "}
                  API calls used today.
                </p>
                {backfillStatus && backfillStatus.total > (backfillStatus.daily_limit - backfillStatus.calls_used_today) && (
                  <p className="text-yellow-600 dark:text-yellow-400 text-xs">
                    Estimated calls exceed remaining daily quota. Backfill will stop at the limit.
                  </p>
                )}
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleBackfillConfirm}>
                    Confirm
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setShowConfirm(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {/* Progress section — visible while running or when there is status data */}
            {(backfillRunning || (backfillStatus && backfillStatus.total > 0)) && !showConfirm && (
              <div className="space-y-2">
                {/* Progress bar */}
                <div className="bg-muted rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-500"
                    style={{
                      width: backfillStatus && backfillStatus.total > 0
                        ? `${Math.min(100, Math.round((backfillStatus.fetched / backfillStatus.total) * 100))}%`
                        : "0%",
                    }}
                  />
                </div>
                {/* Status text */}
                {backfillDone && backfillStatus ? (
                  <p className="text-xs text-muted-foreground">
                    Done — {backfillStatus.fetched} movies updated.
                  </p>
                ) : (
                  backfillStatus && (
                    <p className="text-xs text-muted-foreground">
                      {backfillStatus.fetched} of {backfillStatus.total} movies updated
                    </p>
                  )
                )}
                {/* Quota counter */}
                {backfillStatus && (
                  <p className="text-xs text-muted-foreground">
                    {backfillStatus.calls_used_today} / {backfillStatus.daily_limit} API calls today
                  </p>
                )}
              </div>
            )}
          </div>
          <ValidationBadge state={mdblistValidation} onTest={() => handleTest("mdblist")} service="MDBList" />
        </CardContent>
      </Card>

      {/* Card 3: Radarr */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Radarr</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="radarr-url" className="text-xs">URL</label>
            <Input
              id="radarr-url"
              value={formData.radarr_url ?? ""}
              onChange={handleChange("radarr_url")}
            />
            <p className="text-xs text-muted-foreground">Radarr server URL (e.g., http://localhost:7878)</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="radarr-api-key" className="text-xs">API Key</label>
            <Input
              id="radarr-api-key"
              type="password"
              value={formData.radarr_api_key ?? ""}
              onChange={handleChange("radarr_api_key")}
            />
            <p className="text-xs text-muted-foreground">Found in Radarr under Settings &gt; General &gt; API Key</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="radarr-quality-profile" className="text-xs">Quality Profile</label>
            <Input
              id="radarr-quality-profile"
              value={formData.radarr_quality_profile ?? ""}
              onChange={handleChange("radarr_quality_profile")}
            />
            <p className="text-xs text-muted-foreground">Default quality profile for new downloads (e.g., HD+)</p>
          </div>
          <ValidationBadge state={radarrValidation} onTest={() => handleTest("radarr")} service="Radarr" />
        </CardContent>
      </Card>

      {/* Card 4: DB Health */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">DB Health</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            variant="outline"
            size="sm"
            disabled={dbHealthLoading}
            onClick={handleRefreshDbHealth}
          >
            {dbHealthLoading ? "Loading..." : "Refresh Stats"}
          </Button>

          {dbHealth && (
            <div className="space-y-4">
              {/* Row Health table */}
              <div>
                <p className="text-xs font-medium mb-2">Row Health</p>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-1 pr-4 font-medium text-muted-foreground">Metric</th>
                      <th className="text-right py-1 font-medium text-muted-foreground">Count / %</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">Total movies</td>
                      <td className="text-right py-1">{dbHealth.row_health.total_movies.toLocaleString()}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">Missing overview</td>
                      <td className="text-right py-1">{fmtPct(dbHealth.row_health.missing_overview, dbHealth.row_health.total_movies)}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">Missing MPAA</td>
                      <td className="text-right py-1">{fmtPct(dbHealth.row_health.missing_mpaa, dbHealth.row_health.total_movies)}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">Missing IMDB ID</td>
                      <td className="text-right py-1">{fmtPct(dbHealth.row_health.missing_imdb_id, dbHealth.row_health.total_movies)}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">Missing IMDB rating</td>
                      <td className="text-right py-1">{fmtPct(dbHealth.row_health.missing_imdb_rating, dbHealth.row_health.total_movies)}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">Missing RT score</td>
                      <td className="text-right py-1">{fmtPct(dbHealth.row_health.missing_rt_score, dbHealth.row_health.total_movies)}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">Never MDBList fetched</td>
                      <td className="text-right py-1">{fmtPct(dbHealth.row_health.never_mdblist_fetched, dbHealth.row_health.total_movies)}</td>
                    </tr>
                    <tr>
                      <td className="py-1 pr-4">Total actors</td>
                      <td className="text-right py-1">{dbHealth.row_health.total_actors.toLocaleString()}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Table Sizes */}
              <div>
                <p className="text-xs font-medium mb-2">Table Sizes</p>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-1 pr-4 font-medium text-muted-foreground">Table</th>
                      <th className="text-right py-1 font-medium text-muted-foreground">Size</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">Total DB</td>
                      <td className="text-right py-1">{dbHealth.table_sizes.total_db}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">movies</td>
                      <td className="text-right py-1">{dbHealth.table_sizes.movies}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">credits</td>
                      <td className="text-right py-1">{dbHealth.table_sizes.credits}</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="py-1 pr-4">actors</td>
                      <td className="text-right py-1">{dbHealth.table_sizes.actors}</td>
                    </tr>
                    <tr>
                      <td className="py-1 pr-4">watch_events</td>
                      <td className="text-right py-1">{dbHealth.table_sizes.watch_events}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Save area */}
      <div className="flex flex-col sm:flex-row sm:justify-end gap-2">
        {saveMutation.isError && (
          <p className="text-red-500 text-xs self-center">Failed to save settings. Check your connection and try again.</p>
        )}
        {saveSuccess && (
          <p className="text-sm text-muted-foreground self-center">Settings saved.</p>
        )}
        <Button
          onClick={handleSave}
          disabled={saveMutation.isPending}
          className="w-full sm:w-auto sm:ml-auto"
        >
          {saveMutation.isPending ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </div>
  )
}

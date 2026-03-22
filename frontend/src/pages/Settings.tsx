import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, type SettingsDTO } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

const ENV_NOTICE_KEY = "cinemachain_env_notice_dismissed"

type FieldErrors = Partial<Record<keyof SettingsDTO, string>>

const emptyForm: SettingsDTO = {
  tmdb_api_key: "",
  tmdb_base_url: "",
  radarr_url: "",
  radarr_api_key: "",
  radarr_quality_profile: "",
  sonarr_url: "",
  sonarr_api_key: "",
  plex_token: "",
  plex_url: "",
  tmdb_cache_time: "",
  tmdb_cache_top_n: "",
  mdblist_api_key: "",
}

function nullToEmpty(settings: SettingsDTO): SettingsDTO {
  const result: SettingsDTO = { ...emptyForm }
  for (const key of Object.keys(emptyForm) as Array<keyof SettingsDTO>) {
    result[key] = settings[key] ?? ""
  }
  return result
}

export function Settings() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<SettingsDTO>(emptyForm)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [noticeDismissed, setNoticeDismissed] = useState(
    () => localStorage.getItem(ENV_NOTICE_KEY) === "true"
  )

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

  const saveMutation = useMutation({
    mutationFn: () => api.saveSettings(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] })
      queryClient.invalidateQueries({ queryKey: ["settingsStatus"] })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    },
  })

  const handleChange = (field: keyof SettingsDTO) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [field]: e.target.value }))
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }))
  }

  const handleSave = () => {
    const errors: FieldErrors = {}
    if (!formData.tmdb_api_key?.trim()) errors.tmdb_api_key = "This field is required."
    if (!formData.tmdb_base_url?.trim()) {
      errors.tmdb_base_url = "This field is required."
    } else if (!/^https?:\/\//.test(formData.tmdb_base_url)) {
      errors.tmdb_base_url = "Enter a valid URL starting with http:// or https://."
    }
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return
    saveMutation.mutate()
  }

  const showMigrationNotice =
    !noticeDismissed && settingsStatus?.migrated_from_env === true

  const dismissNotice = () => {
    localStorage.setItem(ENV_NOTICE_KEY, "true")
    setNoticeDismissed(true)
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

      {/* TMDB */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">TMDB</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="tmdb-api-key" className="text-xs">TMDB API Key</label>
            <Input
              id="tmdb-api-key"
              value={formData.tmdb_api_key ?? ""}
              onChange={handleChange("tmdb_api_key")}
            />
            <p className="text-xs text-muted-foreground">Required. Found in your TMDB account under Settings &gt; API.</p>
            {fieldErrors.tmdb_api_key && (
              <p className="text-red-500 text-xs">{fieldErrors.tmdb_api_key}</p>
            )}
          </div>
          <div className="space-y-1">
            <label htmlFor="tmdb-base-url" className="text-xs">TMDB Base URL</label>
            <Input
              id="tmdb-base-url"
              value={formData.tmdb_base_url ?? ""}
              onChange={handleChange("tmdb_base_url")}
            />
            <p className="text-xs text-muted-foreground">Required. Default: https://api.themoviedb.org/3</p>
            {fieldErrors.tmdb_base_url && (
              <p className="text-red-500 text-xs">{fieldErrors.tmdb_base_url}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Radarr */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Radarr</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="radarr-url" className="text-xs">Radarr URL</label>
            <Input
              id="radarr-url"
              value={formData.radarr_url ?? ""}
              onChange={handleChange("radarr_url")}
            />
            <p className="text-xs text-muted-foreground">Radarr server URL (e.g., http://localhost:7878)</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="radarr-api-key" className="text-xs">Radarr API Key</label>
            <Input
              id="radarr-api-key"
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
        </CardContent>
      </Card>

      {/* Sonarr */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Sonarr</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="sonarr-url" className="text-xs">Sonarr URL</label>
            <Input
              id="sonarr-url"
              value={formData.sonarr_url ?? ""}
              onChange={handleChange("sonarr_url")}
            />
            <p className="text-xs text-muted-foreground">Sonarr server URL (e.g., http://localhost:8989)</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="sonarr-api-key" className="text-xs">Sonarr API Key</label>
            <Input
              id="sonarr-api-key"
              value={formData.sonarr_api_key ?? ""}
              onChange={handleChange("sonarr_api_key")}
            />
            <p className="text-xs text-muted-foreground">Found in Sonarr under Settings &gt; General &gt; API Key</p>
          </div>
        </CardContent>
      </Card>

      {/* Plex */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Plex</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="plex-token" className="text-xs">Plex Token</label>
            <Input
              id="plex-token"
              value={formData.plex_token ?? ""}
              onChange={handleChange("plex_token")}
            />
            <p className="text-xs text-muted-foreground">Your Plex authentication token</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="plex-url" className="text-xs">Plex URL</label>
            <Input
              id="plex-url"
              value={formData.plex_url ?? ""}
              onChange={handleChange("plex_url")}
            />
            <p className="text-xs text-muted-foreground">Plex server URL (e.g., http://localhost:32400)</p>
          </div>
        </CardContent>
      </Card>

      {/* MDBList */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">MDBList</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="mdblist-api-key" className="text-xs">MDBList API Key</label>
            <Input
              id="mdblist-api-key"
              type="password"
              value={formData.mdblist_api_key ?? ""}
              onChange={handleChange("mdblist_api_key")}
            />
            <p className="text-xs text-muted-foreground">Optional. Enables Rotten Tomatoes scores on movies. Get your key at mdblist.com.</p>
          </div>
        </CardContent>
      </Card>

      {/* Sync Schedule */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Sync Schedule</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="tmdb-cache-time" className="text-xs">Cache Time</label>
            <Input
              id="tmdb-cache-time"
              value={formData.tmdb_cache_time ?? ""}
              onChange={handleChange("tmdb_cache_time")}
            />
            <p className="text-xs text-muted-foreground">Time to run nightly TMDB cache sync (HH:MM, 24h format)</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="tmdb-cache-top-n" className="text-xs">Cache Top N</label>
            <Input
              id="tmdb-cache-top-n"
              value={formData.tmdb_cache_top_n ?? ""}
              onChange={handleChange("tmdb_cache_top_n")}
            />
            <p className="text-xs text-muted-foreground">Number of top movies to cache nightly</p>
          </div>
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

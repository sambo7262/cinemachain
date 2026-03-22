import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function OnboardingScreen() {
  const queryClient = useQueryClient()
  const [tmdbApiKey, setTmdbApiKey] = useState("")
  const [tmdbBaseUrl, setTmdbBaseUrl] = useState("https://api.themoviedb.org/3")
  const [errors, setErrors] = useState<{ apiKey?: string; baseUrl?: string }>({})

  const saveMutation = useMutation({
    mutationFn: () =>
      api.saveSettings({
        tmdb_api_key: tmdbApiKey,
        tmdb_base_url: tmdbBaseUrl,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settingsStatus"] })
    },
  })

  const handleSubmit = () => {
    const newErrors: typeof errors = {}
    if (!tmdbApiKey.trim()) newErrors.apiKey = "This field is required."
    if (!tmdbBaseUrl.trim()) {
      newErrors.baseUrl = "This field is required."
    } else if (!/^https?:\/\//.test(tmdbBaseUrl)) {
      newErrors.baseUrl = "Enter a valid URL starting with http:// or https://."
    }
    setErrors(newErrors)
    if (Object.keys(newErrors).length > 0) return
    saveMutation.mutate()
  }

  return (
    <div className="fixed inset-0 bg-background flex items-center justify-center p-4 z-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl font-semibold">Welcome to CinemaChain</CardTitle>
          <p className="text-sm text-muted-foreground">
            Connect your TMDB account to get started. Your API key lets CinemaChain fetch movie data, posters, and cast information.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="onboard-tmdb-key" className="text-xs">
              TMDB API Key
            </label>
            <Input
              id="onboard-tmdb-key"
              value={tmdbApiKey}
              onChange={(e) => { setTmdbApiKey(e.target.value); setErrors((prev) => ({ ...prev, apiKey: undefined })) }}
              placeholder=""
            />
            <p className="text-xs text-muted-foreground">Required. Found in your TMDB account under Settings &gt; API.</p>
            {errors.apiKey && <p className="text-red-500 text-xs">{errors.apiKey}</p>}
          </div>

          <div className="space-y-1">
            <label htmlFor="onboard-tmdb-url" className="text-xs">
              TMDB Base URL
            </label>
            <Input
              id="onboard-tmdb-url"
              value={tmdbBaseUrl}
              onChange={(e) => { setTmdbBaseUrl(e.target.value); setErrors((prev) => ({ ...prev, baseUrl: undefined })) }}
            />
            <p className="text-xs text-muted-foreground">Required. Default: https://api.themoviedb.org/3</p>
            {errors.baseUrl && <p className="text-red-500 text-xs">{errors.baseUrl}</p>}
          </div>

          {saveMutation.isError && (
            <p className="text-red-500 text-xs">Failed to save settings. Check your connection and try again.</p>
          )}

          <Button onClick={handleSubmit} disabled={saveMutation.isPending} className="w-full">
            {saveMutation.isPending ? "Saving..." : "Save and Continue"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

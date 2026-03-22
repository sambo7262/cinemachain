import { Routes, Route, Navigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import GameLobby from "./pages/GameLobby"
import GameSession from "./pages/GameSession"
import ArchivedSessions from "./pages/ArchivedSessions"
import { Settings as SettingsPage } from "./pages/Settings"
import { NavBar } from "./components/NavBar"
import { RadarrNotificationBanner } from "./components/RadarrNotificationBanner"
import { NotificationProvider } from "./contexts/NotificationContext"
import { OnboardingScreen } from "./components/OnboardingScreen"
import { api } from "@/lib/api"

export default function App() {
  const { data: settingsStatus, isLoading: settingsLoading } = useQuery({
    queryKey: ["settingsStatus"],
    queryFn: api.getSettingsStatus,
  })

  // Show nothing during initial settings check (avoids onboarding flash)
  if (settingsLoading) {
    return null
  }

  // Block app if TMDB not configured
  if (settingsStatus && !settingsStatus.tmdb_configured) {
    return <OnboardingScreen />
  }

  return (
    <NotificationProvider>
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <NavBar />
        <RadarrNotificationBanner />
        <div className="max-w-[1400px] mx-auto px-6 w-full flex-1">
          <Routes>
            <Route path="/" element={<GameLobby />} />
            <Route path="/game/:sessionId" element={<GameSession />} />
            <Route path="/archived" element={<ArchivedSessions />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </NotificationProvider>
  )
}

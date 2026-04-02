import { Routes, Route, Navigate, useLocation } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import GameLobby from "./pages/GameLobby"
import GameSession from "./pages/GameSession"
import SearchPage from "./pages/SearchPage"
import WatchHistoryPage from "./pages/WatchHistoryPage"
import { Settings as SettingsPage } from "./pages/Settings"
import { NavBar } from "./components/NavBar"
import { RadarrNotificationBanner } from "./components/RadarrNotificationBanner"
import { NotificationProvider } from "./contexts/NotificationContext"
import { OnboardingScreen } from "./components/OnboardingScreen"
import { api } from "@/lib/api"

export default function App() {
  const location = useLocation()
  const { data: settingsStatus, isLoading: settingsLoading } = useQuery({
    queryKey: ["settingsStatus"],
    queryFn: api.getSettingsStatus,
  })

  // Show NavBar during initial settings check so the settings link is always clickable
  if (settingsLoading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <NavBar />
        <div className="flex-1" />
      </div>
    )
  }

  // Block app if TMDB not configured (but always allow /settings through)
  if (settingsStatus && !settingsStatus.tmdb_configured && location.pathname !== "/settings") {
    return <OnboardingScreen />
  }

  return (
    <NotificationProvider>
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <NavBar />
        <RadarrNotificationBanner />
        <div className="max-w-[1400px] mx-auto px-2 sm:px-3 w-full flex-1">
          <Routes>
            <Route path="/game" element={<GameLobby />} />
            <Route path="/game/:sessionId" element={<GameSession />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/watched" element={<WatchHistoryPage />} />
            <Route path="*" element={<Navigate to="/game" replace />} />
          </Routes>
        </div>
      </div>
    </NotificationProvider>
  )
}

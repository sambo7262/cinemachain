import { Routes, Route, Navigate } from "react-router-dom"
import GameLobby from "./pages/GameLobby"
import GameSession from "./pages/GameSession"
import ArchivedSessions from "./pages/ArchivedSessions"
import { NavBar } from "./components/NavBar"
import { RadarrNotificationBanner } from "./components/RadarrNotificationBanner"
import { NotificationProvider } from "./contexts/NotificationContext"

export default function App() {
  return (
    <NotificationProvider>
      <div className="min-h-screen bg-background text-foreground">
        <NavBar />
        <RadarrNotificationBanner />
        <div className="max-w-[1400px] mx-auto px-6">
          <Routes>
            <Route path="/" element={<GameLobby />} />
            <Route path="/game/:sessionId" element={<GameSession />} />
            <Route path="/archived" element={<ArchivedSessions />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </NotificationProvider>
  )
}

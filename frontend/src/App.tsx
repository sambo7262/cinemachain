import { Routes, Route, Navigate } from "react-router-dom"
import GameLobby from "./pages/GameLobby"
import GameSession from "./pages/GameSession"
import { NavBar } from "./components/NavBar"

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <NavBar />
      <Routes>
        <Route path="/" element={<GameLobby />} />
        <Route path="/game/:sessionId" element={<GameSession />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

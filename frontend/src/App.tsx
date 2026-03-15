import { Routes, Route, Navigate } from "react-router-dom"
import GameLobby from "./pages/GameLobby"
import GameSession from "./pages/GameSession"

// Placeholder pages — will be implemented in plans 03-07 and 03-08
// Create stub files now so App.tsx compiles

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Routes>
        <Route path="/" element={<GameLobby />} />
        <Route path="/game/:sessionId" element={<GameSession />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

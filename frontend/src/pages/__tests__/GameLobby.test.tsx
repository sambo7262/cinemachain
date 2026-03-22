import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"

// Wave 0 stub — RED phase. Tests will fail until Plan 03 Task 1 updates session card stats.

// Mock API to return sessions with new stat fields
vi.mock("@/lib/api", () => ({
  api: {
    getActiveSessions: vi.fn().mockResolvedValue([
      {
        id: 1,
        name: "Test Session",
        status: "active",
        current_movie_tmdb_id: 550,
        current_movie_watched: false,
        steps: [],
        radarr_status: null,
        current_movie_title: "Fight Club",
        watched_count: 5,
        watched_runtime_minutes: 645,
        step_count: 8,
        unique_actor_count: 7,
        created_at: "2026-01-15T10:30:00Z",
      },
    ]),
    getArchivedSessions: vi.fn().mockResolvedValue([]),
  },
}))

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe("GameLobby session card stats (Item 8)", () => {
  it("displays watched count on session card", async () => {
    const { default: GameLobby } = await import("@/pages/GameLobby")
    renderWithProviders(<GameLobby />)
    // Should show "5 watched" from the mock data
    expect(await screen.findByText(/5 watched/i)).toBeInTheDocument()
  })

  it("displays total runtime on session card", async () => {
    const { default: GameLobby } = await import("@/pages/GameLobby")
    renderWithProviders(<GameLobby />)
    // 645 minutes = 10h 45m
    expect(await screen.findByText(/10h 45m/i)).toBeInTheDocument()
  })

  it("displays started date on session card", async () => {
    const { default: GameLobby } = await import("@/pages/GameLobby")
    renderWithProviders(<GameLobby />)
    // January 15, 2026
    expect(await screen.findByText(/January 15, 2026/i)).toBeInTheDocument()
  })

  it("does not show archive button on session card", async () => {
    const { default: GameLobby } = await import("@/pages/GameLobby")
    renderWithProviders(<GameLobby />)
    // Wait for cards to render
    await screen.findByText("Test Session")
    // Archive button should not exist on cards (D-11: moved to session menu only)
    expect(screen.queryByRole("button", { name: /archive/i })).not.toBeInTheDocument()
  })
})

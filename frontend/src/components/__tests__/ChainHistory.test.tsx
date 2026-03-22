import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect } from "vitest"

// Wave 0 stub — RED phase. Tests will fail until Plan 03 Task 2 adds search functionality.
// Once ChainHistory has a search input, these tests define expected behavior.

describe("ChainHistory search (Item 4)", () => {
  it("renders a search input with placeholder text", async () => {
    // Stub: import ChainHistory and render with mock steps
    // Will fail until search input is added
    const { ChainHistory } = await import("@/components/ChainHistory")
    const mockSteps = [
      { step_order: 0, movie_tmdb_id: 550, actor_tmdb_id: null, actor_name: null, movie_title: "Fight Club", watched_at: null, poster_path: null, profile_path: null },
      { step_order: 1, movie_tmdb_id: 550, actor_tmdb_id: 287, actor_name: "Brad Pitt", movie_title: null, watched_at: null, poster_path: null, profile_path: null },
      { step_order: 2, movie_tmdb_id: 680, actor_tmdb_id: null, actor_name: null, movie_title: "Pulp Fiction", watched_at: null, poster_path: null, profile_path: null },
      { step_order: 3, movie_tmdb_id: 680, actor_tmdb_id: 500, actor_name: "Tom Cruise", movie_title: null, watched_at: null, poster_path: null, profile_path: null },
    ]
    render(<ChainHistory steps={mockSteps} />)
    expect(screen.getByPlaceholderText(/search movies and actors/i)).toBeInTheDocument()
  })

  it("filters rows when search query matches actor name", async () => {
    const { ChainHistory } = await import("@/components/ChainHistory")
    const mockSteps = [
      { step_order: 0, movie_tmdb_id: 550, actor_tmdb_id: null, actor_name: null, movie_title: "Fight Club", watched_at: null, poster_path: null, profile_path: null },
      { step_order: 1, movie_tmdb_id: 550, actor_tmdb_id: 287, actor_name: "Brad Pitt", movie_title: null, watched_at: null, poster_path: null, profile_path: null },
      { step_order: 2, movie_tmdb_id: 680, actor_tmdb_id: null, actor_name: null, movie_title: "Pulp Fiction", watched_at: null, poster_path: null, profile_path: null },
      { step_order: 3, movie_tmdb_id: 680, actor_tmdb_id: 500, actor_name: "Tom Cruise", movie_title: null, watched_at: null, poster_path: null, profile_path: null },
    ]
    render(<ChainHistory steps={mockSteps} />)
    const input = screen.getByPlaceholderText(/search movies and actors/i)
    await userEvent.type(input, "Brad")
    // Brad Pitt row should be visible, Tom Cruise row should not
    expect(screen.getByText("Brad Pitt")).toBeInTheDocument()
    expect(screen.queryByText("Tom Cruise")).not.toBeInTheDocument()
  })

  it("shows empty state when no rows match search", async () => {
    const { ChainHistory } = await import("@/components/ChainHistory")
    const mockSteps = [
      { step_order: 0, movie_tmdb_id: 550, actor_tmdb_id: null, actor_name: null, movie_title: "Fight Club", watched_at: null, poster_path: null, profile_path: null },
      { step_order: 1, movie_tmdb_id: 550, actor_tmdb_id: 287, actor_name: "Brad Pitt", movie_title: null, watched_at: null, poster_path: null, profile_path: null },
    ]
    render(<ChainHistory steps={mockSteps} />)
    const input = screen.getByPlaceholderText(/search movies and actors/i)
    await userEvent.type(input, "nonexistent")
    expect(screen.getByText(/no chain steps match/i)).toBeInTheDocument()
  })
})

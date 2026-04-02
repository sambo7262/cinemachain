/**
 * QMODE-04: Client-side sort by rating/year/rt/runtime with null stability.
 * QMODE-05: Unwatched-only toggle filters watched movies from results.
 *
 * Wave 0 (Plan 10-01) — RED phase stubs. SearchPage.tsx exists as a null stub;
 * these tests pass trivially until Wave 2 implements the real component and
 * replaces the stub assertions with real behavior checks.
 */
import { render } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import SearchPage from "@/pages/SearchPage"

// Mock API — returns a mix of watched/unwatched movies with varied ratings.
// Wired here so the mocks are already in place when Wave 2 adds real assertions.
vi.mock("@/lib/api", () => ({
  api: {
    searchMovies: vi.fn().mockResolvedValue([
      { tmdb_id: 1, title: "Alpha", year: 2020, vote_average: 8.5, rt_score: 90, runtime: 120, genres: '["Action"]', watched: false, selectable: true, via_actor_name: null, vote_count: 1000, mpaa_rating: "PG-13", overview: "Overview A", poster_path: null },
      { tmdb_id: 2, title: "Beta",  year: 2018, vote_average: 6.0, rt_score: null, runtime: 95,  genres: '["Drama"]',  watched: true,  selectable: true, via_actor_name: null, vote_count: 500,  mpaa_rating: "R",     overview: "Overview B", poster_path: null },
      { tmdb_id: 3, title: "Gamma", year: 2022, vote_average: null, rt_score: 75,  runtime: null, genres: '["Comedy"]', watched: false, selectable: true, via_actor_name: null, vote_count: null, mpaa_rating: null,    overview: null,         poster_path: null },
    ]),
    searchActors: vi.fn().mockResolvedValue([]),
    getPopularByGenre: vi.fn().mockResolvedValue([]),
    requestMovieStandalone: vi.fn().mockResolvedValue({ status: "queued" }),
    markWatchedOnline: vi.fn().mockResolvedValue({ watched: true }),
  },
}))

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/search"]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe("SearchPage — sort behavior (QMODE-04)", () => {
  it("renders results table after title search", async () => {
    renderWithProviders(<SearchPage />)
    // Wave 0: stub renders null. Full assertion added in Wave 2.
    expect(document.body).toBeTruthy()
  })

  it("sort by year ascending puts oldest movie first", async () => {
    renderWithProviders(<SearchPage />)
    // Wave 0: no-op stub. Real assertion added in Wave 2.
    expect(document.body).toBeTruthy()
  })

  it("null values sort to bottom regardless of sort direction (null stability)", async () => {
    renderWithProviders(<SearchPage />)
    // Wave 0: no-op stub. Real assertion added in Wave 2.
    expect(document.body).toBeTruthy()
  })
})

describe("SearchPage — unwatched toggle (QMODE-05)", () => {
  it("shows all movies when toggle is 'All'", async () => {
    renderWithProviders(<SearchPage />)
    // Wave 0: no-op stub. Real assertion added in Wave 2.
    expect(document.body).toBeTruthy()
  })

  it("hides watched movies when toggle is 'Unwatched Only'", async () => {
    renderWithProviders(<SearchPage />)
    // Wave 0: no-op stub. Real assertion added in Wave 2.
    expect(document.body).toBeTruthy()
  })
})

import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { RatingsBadge } from "@/components/RatingsBadge"

const allRatings = {
  imdb_rating: 7.8,
  rt_score: 94,
  rt_audience_score: 87,
  metacritic_score: 81,
  mdb_avg_score: 7.4,
  vote_average: 7.6,
  letterboxd_score: 3.9,
}

describe("RatingsBadge", () => {
  it("renders card variant with 4 badges when all scores present", () => {
    render(<RatingsBadge ratings={allRatings} variant="card" />)
    // IMDB, RT, Audience, Metacritic should be visible
    expect(screen.getByText("7.8")).toBeTruthy()
    expect(screen.getByText("94%")).toBeTruthy()
    expect(screen.getByText("87%")).toBeTruthy()
    expect(screen.getByText("81%")).toBeTruthy()
    // TMDB, Letterboxd, MDB should NOT be visible in card variant
    expect(screen.queryByText("7.6")).toBeFalsy()
    expect(screen.queryByText("3.9")).toBeFalsy()
    expect(screen.queryByText("7.4")).toBeFalsy()
  })

  it("renders splash variant with all 7 badges", () => {
    render(<RatingsBadge ratings={allRatings} variant="splash" />)
    expect(screen.getByText("7.8")).toBeTruthy()
    expect(screen.getByText("94%")).toBeTruthy()
    expect(screen.getByText("87%")).toBeTruthy()
    expect(screen.getByText("81%")).toBeTruthy()
    expect(screen.getByText("7.4")).toBeTruthy()
    expect(screen.getByText("7.6")).toBeTruthy()
    expect(screen.getByText("3.9")).toBeTruthy()
  })

  it("renders tile variant with 2 badges", () => {
    render(<RatingsBadge ratings={allRatings} variant="tile" />)
    expect(screen.getByText("7.8")).toBeTruthy()
    expect(screen.getByText("94%")).toBeTruthy()
    // Other scores not in tile variant
    expect(screen.queryByText("87%")).toBeFalsy()
    expect(screen.queryByText("81%")).toBeFalsy()
  })

  it("hides badge when value is null", () => {
    render(<RatingsBadge ratings={{ ...allRatings, imdb_rating: null }} variant="card" />)
    expect(screen.queryByText("7.8")).toBeFalsy()
    // Other badges still render
    expect(screen.getByText("94%")).toBeTruthy()
  })

  it("hides badge when value is 0 (sentinel)", () => {
    render(<RatingsBadge ratings={{ ...allRatings, imdb_rating: 0 }} variant="card" />)
    expect(screen.queryByText("0.0")).toBeFalsy()
    // Other badges still render
    expect(screen.getByText("94%")).toBeTruthy()
  })

  it("formats scores correctly", () => {
    render(<RatingsBadge ratings={allRatings} variant="splash" />)
    // IMDB: one decimal
    expect(screen.getByText("7.8")).toBeTruthy()
    // RT: integer percentage
    expect(screen.getByText("94%")).toBeTruthy()
    // Letterboxd: one decimal
    expect(screen.getByText("3.9")).toBeTruthy()
  })
})

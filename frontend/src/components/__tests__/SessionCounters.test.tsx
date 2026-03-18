import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SessionCounters } from "../SessionCounters"

describe("SessionCounters", () => {
  it("renders Watched count and Runtime (core stats)", () => {
    render(
      <SessionCounters
        watchedCount={3}
        watchedRuntimeMinutes={180}
        stepCount={5}
        uniqueActorCount={4}
        createdAt={new Date(Date.now() - 90 * 60 * 1000).toISOString()}
      />
    )
    // Watched count
    expect(screen.getByText("3")).toBeTruthy()
    // Runtime: 3h
    expect(screen.getByText("3h")).toBeTruthy()
    // Started label is present
    expect(screen.getByText("Started")).toBeTruthy()
  })

  it("does NOT render Steps or Actors stats (UX-C simplification)", () => {
    // UX-C: SessionCounters shows only Watched, Runtime, Started.
    // Steps and Actors have been removed. This test will be RED until
    // Wave 2 removes the Steps and Actors <div> blocks from the component.
    render(
      <SessionCounters
        watchedCount={2}
        watchedRuntimeMinutes={120}
        stepCount={6}
        uniqueActorCount={5}
        createdAt={new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()}
      />
    )
    // These labels must NOT appear
    expect(screen.queryByText("Steps")).toBeNull()
    expect(screen.queryByText("Actors")).toBeNull()
    // Core stats must still be present
    expect(screen.getByText("Watched")).toBeTruthy()
    expect(screen.getByText("Runtime")).toBeTruthy()
    expect(screen.getByText("Started")).toBeTruthy()
  })
})

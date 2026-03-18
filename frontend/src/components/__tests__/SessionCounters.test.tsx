import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SessionCounters } from "../SessionCounters"

describe("SessionCounters", () => {
  it("renders watched count and runtime (existing behavior)", () => {
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
  })

  it("renders new stats: Steps, Actors, Started labels", () => {
    render(
      <SessionCounters
        watchedCount={2}
        watchedRuntimeMinutes={120}
        stepCount={6}
        uniqueActorCount={5}
        createdAt={new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()}
      />
    )
    expect(screen.getByText("Steps")).toBeTruthy()
    expect(screen.getByText("6")).toBeTruthy()
    expect(screen.getByText("Actors")).toBeTruthy()
    expect(screen.getByText("5")).toBeTruthy()
    expect(screen.getByText("Started")).toBeTruthy()
  })
})

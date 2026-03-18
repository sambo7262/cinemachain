import { describe, it, expect } from "vitest"
import { render, screen, act } from "@testing-library/react"
import { RadarrNotificationBanner } from "../components/RadarrNotificationBanner"
import { NotificationProvider, useNotification } from "../contexts/NotificationContext"

// Helper component that triggers showRadarr via context
function BannerWithMessage({ message }: { message: string }) {
  const { showRadarr } = useNotification()
  return (
    <button onClick={() => showRadarr(message as "Already in Radarr" | "Movie Queued for Download")}>
      trigger
    </button>
  )
}

describe("RadarrNotificationBanner", () => {
  it("renders null when radarrMessage is null", () => {
    // UX-06: banner must not appear when there is no active message
    const { container } = render(
      <NotificationProvider>
        <RadarrNotificationBanner />
      </NotificationProvider>
    )
    // No message set — banner returns null
    expect(container.firstChild).toBeNull()
  })

  it("renders the message text when radarrMessage is set", async () => {
    // UX-06: banner must display the exact message string passed in
    const { getByRole } = render(
      <NotificationProvider>
        <BannerWithMessage message="Movie Queued for Download" />
        <RadarrNotificationBanner />
      </NotificationProvider>
    )
    await act(async () => {
      getByRole("button", { name: "trigger" }).click()
    })
    expect(screen.getByText("Movie Queued for Download")).toBeTruthy()
  })
})

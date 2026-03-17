import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

// RadarrNotificationBanner does not exist yet — created in Plan 04.
// These tests will fail (RED) until Plan 04 implements the component.
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-expect-error — component not yet implemented
import { RadarrNotificationBanner } from "../components/RadarrNotificationBanner"

describe("RadarrNotificationBanner", () => {
  it("renders null when radarrMessage is null", () => {
    // UX-06: banner must not appear when there is no active message
    const { container } = render(<RadarrNotificationBanner radarrMessage={null} onDismiss={() => {}} />)
    expect(container.firstChild).toBeNull()
  })

  it("renders the message text when radarrMessage is set", () => {
    // UX-06: banner must display the exact message string passed in
    render(<RadarrNotificationBanner radarrMessage="Movie Queued for Download" onDismiss={() => {}} />)
    expect(screen.getByText("Movie Queued for Download")).toBeTruthy()
  })
})

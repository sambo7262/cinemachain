import { useState, useEffect, useRef } from "react"

const CONCESSION_MESSAGES = [
  "Popping the popcorn...",
  "Making the nachos...",
  "Filling the sodas...",
  "Buttering the popcorn...",
  "Getting the candy...",
  "Finding your seats...",
  "Dimming the lights...",
  "Starting the previews...",
]

/**
 * Returns a rotating loading message that cycles every 2 seconds while `isLoading` is true.
 * Returns null when isLoading is false.
 */
export function useLoadingMessages(isLoading: boolean): string | null {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * CONCESSION_MESSAGES.length))
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!isLoading) {
      if (intervalRef.current) clearInterval(intervalRef.current)
      return
    }
    intervalRef.current = setInterval(() => {
      setIndex((i) => (i + 1) % CONCESSION_MESSAGES.length)
    }, 2000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isLoading])

  return isLoading ? CONCESSION_MESSAGES[index] : null
}

import { useState } from "react"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"

interface RatingSliderProps {
  movieTitle: string
  posterPath: string | null
  currentRating: number | null
  onSave: (rating: number) => void
  onSkip: () => void
  isPending?: boolean
}

export function RatingSlider({
  movieTitle,
  posterPath,
  currentRating,
  onSave,
  onSkip,
  isPending = false,
}: RatingSliderProps) {
  const [value, setValue] = useState<number>(currentRating ?? 7)

  return (
    <div className="flex flex-col gap-4 py-2">
      {/* Movie header: poster + title */}
      <div className="flex items-center gap-3">
        {posterPath ? (
          <img
            src={`https://image.tmdb.org/t/p/w92${posterPath}`}
            alt={movieTitle}
            className="w-16 h-24 object-cover rounded"
          />
        ) : (
          <div className="w-16 h-24 bg-muted rounded flex items-center justify-center text-xs text-muted-foreground">
            No poster
          </div>
        )}
        <p className="font-medium text-sm leading-snug">{movieTitle}</p>
      </div>

      {/* Numeric value */}
      <div className="text-center">
        <span className="text-2xl font-bold tabular-nums">{value}</span>
        <span className="text-muted-foreground text-sm"> / 10</span>
      </div>

      {/* Slider */}
      <Slider
        min={1}
        max={10}
        step={1}
        value={[value]}
        onValueChange={(v) => setValue(v[0])}
        disabled={isPending}
        aria-label="Movie rating"
      />

      {/* Save / Skip buttons */}
      <div className="flex gap-2 pt-1">
        <Button
          className="flex-1"
          variant="default"
          disabled={isPending}
          onClick={() => onSave(value)}
        >
          {isPending ? "Saving..." : "Save"}
        </Button>
        <Button
          className="flex-1"
          variant="outline"
          disabled={isPending}
          onClick={onSkip}
        >
          Skip
        </Button>
      </div>
    </div>
  )
}

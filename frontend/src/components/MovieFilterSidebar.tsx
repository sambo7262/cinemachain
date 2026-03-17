import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Checkbox } from "@/components/ui/checkbox"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ChevronRight, ChevronDown } from "lucide-react"
import { useState } from "react"

export interface FilterState {
  runtimeRange: [number, number]
  genres: string[]
  mpaaRatings: string[]
}

export const DEFAULT_FILTER_STATE: FilterState = {
  runtimeRange: [0, 300],
  genres: [],
  mpaaRatings: [],
}

const MPAA_OPTIONS = ["G", "PG", "PG-13", "R", "NR"] as const

function formatRuntime(minutes: number): string {
  if (minutes < 60) return `${minutes}m`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m === 0 ? `${h}h` : `${h}h ${m}m`
}

interface MovieFilterSidebarProps {
  genres: string[]             // all available genres derived from loaded movie list
  filters: FilterState
  onChange: (f: FilterState) => void
}

export function MovieFilterSidebar({ genres, filters, onChange }: MovieFilterSidebarProps) {
  const [runtimeOpen, setRuntimeOpen] = useState(false)
  const [genreOpen, setGenreOpen] = useState(false)
  const [mpaaOpen, setMpaaOpen] = useState(false)

  // Count active filters for header badge
  const activeFilterCount =
    (filters.runtimeRange[0] !== 0 || filters.runtimeRange[1] !== 300 ? 1 : 0) +
    (filters.genres.length > 0 ? 1 : 0) +
    (filters.mpaaRatings.length > 0 ? 1 : 0)

  const runtimeLabel =
    filters.runtimeRange[0] === 0 && filters.runtimeRange[1] === 300
      ? "Any runtime"
      : `${formatRuntime(filters.runtimeRange[0])} – ${formatRuntime(filters.runtimeRange[1])}`

  function toggleGenre(genre: string) {
    const next = filters.genres.includes(genre)
      ? filters.genres.filter((g) => g !== genre)
      : [...filters.genres, genre]
    onChange({ ...filters, genres: next })
  }

  function toggleMpaa(rating: string) {
    const next = filters.mpaaRatings.includes(rating)
      ? filters.mpaaRatings.filter((r) => r !== rating)
      : [...filters.mpaaRatings, rating]
    onChange({ ...filters, mpaaRatings: next })
  }

  return (
    <div className="w-56 shrink-0 border border-border rounded-md bg-card p-3 space-y-1">
      {/* Header */}
      <div className="flex items-center justify-between pb-2">
        <span className="text-sm font-semibold">Filters</span>
        {activeFilterCount > 0 && (
          <Badge className="bg-primary text-primary-foreground text-xs px-1.5 py-0.5">
            {activeFilterCount}
          </Badge>
        )}
      </div>

      <Separator />

      {/* Runtime */}
      <Collapsible open={runtimeOpen} onOpenChange={setRuntimeOpen}>
        <CollapsibleTrigger className="flex w-full items-center justify-between py-2 text-sm hover:text-foreground text-muted-foreground">
          <span>Runtime</span>
          {runtimeOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </CollapsibleTrigger>
        <CollapsibleContent className="pb-2 space-y-2">
          <p className="text-xs text-muted-foreground">{runtimeLabel}</p>
          <Slider
            min={0}
            max={300}
            step={15}
            value={filters.runtimeRange}
            onValueChange={(v) => onChange({ ...filters, runtimeRange: v as [number, number] })}
            className="mt-1"
          />
        </CollapsibleContent>
      </Collapsible>

      <Separator />

      {/* Genre */}
      <Collapsible open={genreOpen} onOpenChange={setGenreOpen}>
        <CollapsibleTrigger className="flex w-full items-center justify-between py-2 text-sm hover:text-foreground text-muted-foreground">
          <span>Genre</span>
          {genreOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </CollapsibleTrigger>
        <CollapsibleContent className="pb-2 space-y-1.5 max-h-48 overflow-y-auto">
          {genres.length === 0 && (
            <p className="text-xs text-muted-foreground">No genres available</p>
          )}
          {genres.map((genre) => (
            <label key={genre} className="flex items-center gap-2 text-sm cursor-pointer">
              <Checkbox
                checked={filters.genres.includes(genre)}
                onCheckedChange={() => toggleGenre(genre)}
              />
              {genre}
            </label>
          ))}
        </CollapsibleContent>
      </Collapsible>

      <Separator />

      {/* MPAA Rating */}
      <Collapsible open={mpaaOpen} onOpenChange={setMpaaOpen}>
        <CollapsibleTrigger className="flex w-full items-center justify-between py-2 text-sm hover:text-foreground text-muted-foreground">
          <span>Rating</span>
          {mpaaOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </CollapsibleTrigger>
        <CollapsibleContent className="pb-2 space-y-1.5">
          {MPAA_OPTIONS.map((rating) => (
            <label key={rating} className="flex items-center gap-2 text-sm cursor-pointer">
              <Checkbox
                checked={filters.mpaaRatings.includes(rating)}
                onCheckedChange={() => toggleMpaa(rating)}
              />
              {rating}
            </label>
          ))}
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}

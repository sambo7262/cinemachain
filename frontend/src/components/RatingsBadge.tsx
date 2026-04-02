import React from "react"
import { SiImdb, SiThemoviedatabase, SiRottentomatoes, SiMetacritic, SiMdblist } from "@icons-pack/react-simple-icons"
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip"

// Custom tricolor Letterboxd icon (three circles in brand colors)
const LetterboxdIcon = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <circle cx="4.5" cy="12" r="4.5" fill="#FF8000" />
    <circle cx="12" cy="12" r="4.5" fill="#00E054" />
    <circle cx="19.5" cy="12" r="4.5" fill="#40BCF4" />
  </svg>
)

export interface RatingsData {
  imdb_rating?: number | null
  rt_score?: number | null
  rt_audience_score?: number | null
  metacritic_score?: number | null
  mdb_avg_score?: number | null
  vote_average?: number | null
  letterboxd_score?: number | null
}

export type BadgeVariant = "card" | "splash" | "tile"

interface RatingsBadgeProps {
  ratings: RatingsData
  variant?: BadgeVariant
}

const VARIANT_KEYS: Record<BadgeVariant, (keyof RatingsData)[]> = {
  card: ["imdb_rating", "rt_score", "rt_audience_score", "metacritic_score", "vote_average"],
  splash: ["imdb_rating", "rt_score", "rt_audience_score", "metacritic_score", "mdb_avg_score", "vote_average", "letterboxd_score"],
  tile: ["imdb_rating", "rt_score"],
}

interface BadgeDef {
  key: keyof RatingsData
  icon: React.ReactNode
  format: (v: number) => string
  label: string
}

const BADGE_DEFS: BadgeDef[] = [
  {
    key: "imdb_rating",
    icon: <SiImdb size={14} color="#F5C518" />,
    format: (v) => v.toFixed(1),
    label: "IMDB",
  },
  {
    key: "rt_score",
    icon: <SiRottentomatoes size={14} color="#FA320A" />,
    format: (v) => `${v}%`,
    label: "RT Tomatometer",
  },
  {
    key: "rt_audience_score",
    icon: <span role="img" aria-label="popcorn">🍿</span>,
    format: (v) => `${v}%`,
    label: "RT Audience",
  },
  {
    key: "metacritic_score",
    icon: <SiMetacritic size={14} color="#FFCC34" />,
    format: (v) => `${v}%`,
    label: "Metacritic",
  },
  {
    key: "mdb_avg_score",
    icon: <SiMdblist size={14} color="#4284CA" />,
    format: (v) => v.toFixed(1),
    label: "MDB Average",
  },
  {
    key: "vote_average",
    icon: <SiThemoviedatabase size={14} color="#01B4E4" />,
    format: (v) => v.toFixed(1),
    label: "TMDB",
  },
  {
    key: "letterboxd_score",
    icon: <LetterboxdIcon size={14} />,
    format: (v) => v.toFixed(1),
    label: "Letterboxd",
  },
]

export function RatingsBadge({ ratings, variant = "card" }: RatingsBadgeProps) {
  const keys = VARIANT_KEYS[variant]
  const visibleDefs = BADGE_DEFS.filter((def) => keys.includes(def.key))

  const badges = visibleDefs
    .map((def) => {
      const value = ratings[def.key]
      // Skip null, undefined, or 0 (sentinel for "fetched, no data")
      if (value == null || value === 0) return null
      return (
        <Tooltip key={def.key}>
          <TooltipTrigger asChild>
            <span
              className="inline-flex items-center gap-0.5 text-xs"
              aria-label={`${def.label}: ${def.format(value)}`}
            >
              {def.icon}
              <span>{def.format(value)}</span>
            </span>
          </TooltipTrigger>
          <TooltipContent side="top" className="text-xs">
            {def.label}: {def.format(value)}
          </TooltipContent>
        </Tooltip>
      )
    })
    .filter(Boolean)

  if (badges.length === 0) return null

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex flex-wrap gap-1.5 items-center max-w-full">
        {badges}
      </div>
    </TooltipProvider>
  )
}

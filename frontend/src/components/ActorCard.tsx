import React from "react"
import { Card } from "@/components/ui/card"

interface ActorCardProps {
  tmdb_id: number
  name: string
  profile_path: string | null
  character: string | null
  onClick: () => void
}

const TMDB_PROFILE = "https://image.tmdb.org/t/p/w185"

export function ActorCard({ name, profile_path, character, onClick }: ActorCardProps) {
  const photo = profile_path ? `${TMDB_PROFILE}${profile_path}` : null
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()

  return (
    <Card
      className="flex items-center gap-3 p-4 cursor-pointer hover:bg-accent transition-colors"
      onClick={onClick}
    >
      {photo ? (
        <img
          src={photo}
          alt={name}
          className="w-12 h-12 rounded-full object-cover flex-shrink-0"
        />
      ) : (
        <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center text-sm font-bold flex-shrink-0">
          {initials}
        </div>
      )}
      <div>
        <p className="font-semibold">{name}</p>
        {character && (
          <p className="text-sm text-muted-foreground italic">{character}</p>
        )}
      </div>
    </Card>
  )
}

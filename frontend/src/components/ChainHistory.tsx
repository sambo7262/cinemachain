import React, { useState } from "react"
import { Search, ExternalLink } from "lucide-react"
import { Input } from "@/components/ui/input"
import type { GameSessionStepDTO } from "@/lib/api"

export function ChainHistory({ steps }: { steps: GameSessionStepDTO[] }) {
  const [searchQuery, setSearchQuery] = useState("")

  if (steps.length === 0) return null

  const sorted = [...steps].sort((a, b) => a.step_order - b.step_order)

  // Build display rows: one row per movie (actor_tmdb_id === null steps).
  // The immediately following step (step_order + 1) holds the actor pick for that movie.
  const movieSteps = sorted.filter((s) => s.actor_tmdb_id === null)

  const filteredSteps = movieSteps.filter((step) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    const actorStep = sorted.find((s) => s.step_order === step.step_order + 1 && s.actor_tmdb_id !== null)
    return (
      (step.movie_title ?? "").toLowerCase().includes(q) ||
      (actorStep?.actor_name ?? "").toLowerCase().includes(q)
    )
  })

  return (
    <div className="rounded-md border border-border overflow-hidden">
      <div className="relative mb-0 px-3 pt-3">
        <Search className="absolute left-6 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search movies and actors..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>
      <table className="w-full text-sm mt-2">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left px-3 py-2 text-muted-foreground w-8 font-medium">#</th>
            <th className="text-left px-3 py-2 text-muted-foreground w-12 font-medium"></th>
            <th className="text-left px-3 py-2 text-muted-foreground font-medium">Name</th>
            <th className="text-right px-3 py-2 text-muted-foreground hidden sm:table-cell font-medium">When</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {filteredSteps.map((step, i) => {
            // Actor for this movie lives in the very next step by step_order
            const actorStep = sorted.find((s) => s.step_order === step.step_order + 1 && s.actor_tmdb_id !== null)
            return (
              <React.Fragment key={step.step_order}>
                {/* Movie row */}
                <tr>
                  <td className="px-3 py-2 text-muted-foreground text-xs">{i + 1}</td>
                  <td className="px-3 py-2">
                    {step.poster_path ? (
                      <img
                        src={`https://image.tmdb.org/t/p/w92${step.poster_path}`}
                        alt={step.movie_title ?? "Movie poster"}
                        className="w-10 h-14 rounded object-cover"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none" }}
                      />
                    ) : (
                      <div className="w-10 h-14 rounded bg-muted flex items-center justify-center text-muted-foreground" aria-hidden="true">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M4 2h16a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                        </svg>
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2 font-medium">
                    <span className="inline-flex items-center gap-1">
                      {step.movie_title ?? "(untitled)"}
                      <a
                        href={`https://www.themoviedb.org/movie/${step.movie_tmdb_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label="View on TMDB"
                        className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-muted-foreground text-xs hidden sm:table-cell">
                    {step.watched_at
                      ? new Date(step.watched_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
                      : "—"}
                  </td>
                </tr>
                {/* Actor row — only if an actor was picked from this movie */}
                {actorStep?.actor_name && (
                  <tr className="bg-muted/20">
                    <td className="px-3 py-2 text-muted-foreground text-xs"></td>
                    <td className="px-3 py-2">
                      {actorStep.profile_path ? (
                        <img
                          src={`https://image.tmdb.org/t/p/w45${actorStep.profile_path}`}
                          alt={actorStep.actor_name ?? "Actor"}
                          className="w-7 h-7 rounded-full object-cover"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = "none" }}
                        />
                      ) : (
                        <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground" aria-hidden="true">
                          {actorStep.actor_name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground italic" colSpan={2}>
                      <span className="inline-flex items-center gap-1">
                        {actorStep.actor_name}
                        {actorStep.actor_tmdb_id && (
                          <a
                            href={`https://www.themoviedb.org/person/${actorStep.actor_tmdb_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label="View on TMDB"
                            className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </span>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            )
          })}
        </tbody>
      </table>
      {filteredSteps.length === 0 && searchQuery && (
        <p className="text-sm text-muted-foreground text-center py-4">
          No chain steps match "{searchQuery}".
        </p>
      )}
    </div>
  )
}

import React from "react"
import type { GameSessionStepDTO } from "@/lib/api"

export function ChainHistory({ steps }: { steps: GameSessionStepDTO[] }) {
  if (steps.length === 0) return null

  const sorted = [...steps].sort((a, b) => a.step_order - b.step_order)

  return (
    <div className="rounded-md border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left px-3 py-2 text-muted-foreground w-8 font-medium">#</th>
            <th className="text-left px-3 py-2 text-muted-foreground w-12 font-medium"></th>
            <th className="text-left px-3 py-2 text-muted-foreground font-medium">Name</th>
            <th className="text-right px-3 py-2 text-muted-foreground hidden sm:table-cell font-medium">When</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {sorted.map((step, i) => (
            <React.Fragment key={step.step_order}>
              {/* Movie row */}
              <tr>
                <td className="px-3 py-2 text-muted-foreground text-xs">{i + 1}</td>
                <td className="px-3 py-2">
                  {/* Poster placeholder — step DTO does not carry poster_path */}
                  <div className="w-10 h-14 rounded bg-muted flex items-center justify-center text-muted-foreground">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M4 2h16a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                    </svg>
                  </div>
                </td>
                <td className="px-3 py-2 font-medium">
                  {step.movie_title ?? "(untitled)"}
                </td>
                <td className="px-3 py-2 text-right text-muted-foreground text-xs hidden sm:table-cell">
                  {step.watched_at
                    ? new Date(step.watched_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
                    : "—"}
                </td>
              </tr>
              {/* Actor row — only if actor was picked on this step */}
              {step.actor_name && (
                <tr className="bg-muted/20">
                  <td className="px-3 py-2 text-muted-foreground text-xs"></td>
                  <td className="px-3 py-2">
                    {/* Actor thumbnail placeholder — step DTO does not carry profile_path */}
                    <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground">
                      {step.actor_name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase()}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-muted-foreground italic" colSpan={2}>
                    {step.actor_name}
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}

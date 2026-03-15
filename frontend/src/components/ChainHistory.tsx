import React from "react"
import { Film, User, ChevronRight } from "lucide-react"
import type { GameSessionStepDTO } from "@/lib/api"

export function ChainHistory({ steps }: { steps: GameSessionStepDTO[] }) {
  if (steps.length === 0) return null

  return (
    <div className="overflow-x-auto py-3">
      <div className="flex items-center gap-2 min-w-max px-2">
        {steps.map((step) => (
          <React.Fragment key={step.step_order}>
            {/* Movie node */}
            <div className="flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-2 text-sm">
              <Film className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              <span className="font-medium max-w-32 truncate">
                {step.movie_title ?? `Movie ${step.movie_tmdb_id}`}
              </span>
            </div>
            {/* Actor connector — only if actor was picked on this step */}
            {step.actor_name && (
              <>
                <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="flex items-center gap-1 bg-accent/30 rounded-full px-3 py-1 text-xs">
                  <User className="w-3 h-3" />
                  <span>{step.actor_name}</span>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              </>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}

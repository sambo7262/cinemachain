interface SessionCountersProps {
  watchedCount: number
  watchedRuntimeMinutes: number
  stepCount: number
  uniqueActorCount: number
  createdAt: string  // ISO 8601 timestamp
}

function formatRuntime(minutes: number): string {
  if (minutes === 0) return "—"
  if (minutes < 60) return `${minutes}m`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m === 0 ? `${h}h` : `${h}h ${m}m`
}

function formatSessionAge(createdAt: string): string {
  if (!createdAt) return "—"
  try {
    const diffMs = Date.now() - new Date(createdAt).getTime()
    const diffMinutes = Math.floor(diffMs / 60000)
    if (diffMinutes < 60) return `${diffMinutes}m ago`
    const diffHours = Math.floor(diffMinutes / 60)
    const remainingMinutes = diffMinutes % 60
    if (diffHours < 24) {
      return remainingMinutes === 0 ? `${diffHours}h ago` : `${diffHours}h ${remainingMinutes}m ago`
    }
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  } catch {
    return "—"
  }
}

export function SessionCounters({
  watchedCount,
  watchedRuntimeMinutes,
  stepCount,
  uniqueActorCount,
  createdAt,
}: SessionCountersProps) {
  return (
    <dl className="flex items-center gap-4 text-sm">
      <div className="flex flex-col items-center">
        <dt className="text-xs text-muted-foreground uppercase tracking-wide">Watched</dt>
        <dd className="text-sm font-semibold text-foreground">{watchedCount}</dd>
      </div>
      <div className="h-8 w-px bg-border" aria-hidden="true" />
      <div className="flex flex-col items-center">
        <dt className="text-xs text-muted-foreground uppercase tracking-wide">Runtime</dt>
        <dd className="text-sm font-semibold text-foreground">
          {watchedCount === 0 ? "—" : formatRuntime(watchedRuntimeMinutes)}
        </dd>
      </div>
      <div className="h-8 w-px bg-border" aria-hidden="true" />
      <div className="flex flex-col items-center">
        <dt className="text-xs text-muted-foreground uppercase tracking-wide">Steps</dt>
        <dd className="text-sm font-semibold text-foreground">{stepCount}</dd>
      </div>
      <div className="h-8 w-px bg-border" aria-hidden="true" />
      <div className="flex flex-col items-center">
        <dt className="text-xs text-muted-foreground uppercase tracking-wide">Actors</dt>
        <dd className="text-sm font-semibold text-foreground">{uniqueActorCount}</dd>
      </div>
      <div className="h-8 w-px bg-border" aria-hidden="true" />
      <div className="flex flex-col items-center">
        <dt className="text-xs text-muted-foreground uppercase tracking-wide">Started</dt>
        <dd className="text-sm font-semibold text-foreground">{formatSessionAge(createdAt)}</dd>
      </div>
    </dl>
  )
}

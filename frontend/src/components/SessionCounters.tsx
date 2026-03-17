interface SessionCountersProps {
  watchedCount: number
  watchedRuntimeMinutes: number
}

function formatRuntime(minutes: number): string {
  if (minutes === 0) return "—"
  if (minutes < 60) return `${minutes}m`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m === 0 ? `${h}h` : `${h}h ${m}m`
}

export function SessionCounters({ watchedCount, watchedRuntimeMinutes }: SessionCountersProps) {
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
    </dl>
  )
}

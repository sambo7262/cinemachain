import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { api } from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export default function ArchivedSessions() {
  const navigate = useNavigate()

  const { data: archivedSessions = [], isLoading } = useQuery({
    queryKey: ["archivedSessions"],
    queryFn: api.listArchivedSessions,
    staleTime: 30000,
  })

  return (
    <div className="min-h-screen flex flex-col items-center justify-start p-6 gap-8">
      <div className="text-center mt-8">
        <h1 className="text-2xl font-bold tracking-tight">Archived Sessions</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Past chains — read-only
        </p>
      </div>

      <div className="w-full max-w-2xl flex flex-col gap-3">
        {isLoading && (
          <p className="text-muted-foreground text-sm text-center py-8">Loading...</p>
        )}
        {!isLoading && archivedSessions.length === 0 && (
          <p className="text-muted-foreground text-sm text-center py-8">
            No archived sessions yet.
          </p>
        )}
        {archivedSessions.map((session) => {
          const currentStep = [...session.steps]
            .sort((a, b) => b.step_order - a.step_order)[0]
          const movieTitle = currentStep?.movie_title ?? session.steps[0]?.movie_title ?? "(untitled)"
          return (
            <Card key={session.id}>
              <CardContent className="flex items-center justify-between py-4 px-5">
                <div className="flex flex-col gap-0.5">
                  <span className="font-semibold text-foreground">{session.name || `Session ${session.id}`}</span>
                  <span className="text-sm text-muted-foreground">
                    {movieTitle} · {session.steps.length} step{session.steps.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/game/${session.id}`)}
                >
                  View
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

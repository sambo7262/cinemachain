import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { api } from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog"

export default function ArchivedSessions() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteSessionId, setDeleteSessionId] = useState<number | null>(null)

  const { data: archivedSessions = [], isLoading } = useQuery({
    queryKey: ["archivedSessions"],
    queryFn: api.listArchivedSessions,
    staleTime: 30000,
  })

  const deleteSessionMutation = useMutation({
    mutationFn: (id: number) => api.deleteSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["archivedSessions"] })
      setDeleteSessionId(null)
    },
    onError: () => {
      // Error displayed inline in dialog
    },
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
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/game/${session.id}`)}
                  >
                    View
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => setDeleteSessionId(session.id)}
                  >
                    Delete Session
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Delete Session Dialog */}
      <Dialog
        open={deleteSessionId !== null}
        onOpenChange={(open) => { if (!open) setDeleteSessionId(null) }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Session</DialogTitle>
            <DialogDescription>
              This will permanently remove this session and all its steps. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteSessionMutation.isError && (
            <p className="text-sm text-destructive">Could not delete session. Try again.</p>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteSessionId(null)}
              disabled={deleteSessionMutation.isPending}
            >
              Keep Session
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteSessionId !== null && deleteSessionMutation.mutate(deleteSessionId)}
              disabled={deleteSessionMutation.isPending}
            >
              {deleteSessionMutation.isPending ? "Deleting..." : "Delete Session"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

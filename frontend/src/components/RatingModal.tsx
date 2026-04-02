import { Button } from "@/components/ui/button"

interface RatingModalProps {
  movieTitle: string
  onRate: (rating: number | null) => void
}

export function RatingModal({ movieTitle, onRate }: RatingModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-background rounded-lg border shadow-lg p-6 w-full max-w-sm space-y-4">
        <div className="space-y-1">
          <h2 className="text-base font-semibold">Rate this movie</h2>
          <p className="text-sm text-muted-foreground truncate">{movieTitle}</p>
        </div>

        <div className="grid grid-cols-5 gap-2">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
            <Button
              key={n}
              variant="outline"
              size="sm"
              className="aspect-square text-sm font-medium"
              onClick={() => onRate(n)}
            >
              {n}
            </Button>
          ))}
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="w-full text-muted-foreground"
          onClick={() => onRate(null)}
        >
          Skip
        </Button>
      </div>
    </div>
  )
}

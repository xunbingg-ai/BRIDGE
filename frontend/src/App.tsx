import { cn } from './lib/utils'

function App() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-8 text-foreground">
      <h1 className="text-3xl font-semibold tracking-tight">BRIDGE</h1>
      <p className="max-w-md text-center text-muted-foreground">
        AI standardized patient practice for OSCE/CCE training. The skeleton is
        up — features land one at a time.
      </p>
      <span className={cn('text-xs text-muted-foreground')}>v0.1.0 skeleton</span>
    </main>
  )
}

export default App

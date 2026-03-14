import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">ChartViz</h1>
        <p className="text-muted-foreground mt-4 text-lg">
          Chart visualization playground
        </p>
        <nav className="mt-8 flex justify-center gap-4">
          <Link
            href="/factory"
            className="bg-muted hover:bg-muted/80 rounded-md px-4 py-2 text-sm font-medium transition"
          >
            Chart Factory
          </Link>
          <Link
            href="/eval"
            className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-md px-4 py-2 text-sm font-medium transition"
          >
            Viz Designer Eval
          </Link>
        </nav>
      </div>
    </main>
  );
}

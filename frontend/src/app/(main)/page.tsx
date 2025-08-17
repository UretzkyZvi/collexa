export default function HomePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-lg border bg-card p-4">Card A</div>
        <div className="rounded-lg border bg-card p-4">Card B</div>
        <div className="rounded-lg border bg-card p-4">Card C</div>
      </div>
      <div className="rounded-lg border bg-card p-4 min-h-80">Main area</div>
    </div>
  );
}

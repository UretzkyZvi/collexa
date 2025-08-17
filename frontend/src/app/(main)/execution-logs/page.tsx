"use client";
import { useEffect, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card } from "~/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";

export default function LogsPage() {
  const authFetch = useAuthFetch();
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/runs`, { method: "GET" });
      if (res.ok) setRuns(await res.json());
    })();
  }, []);

  useEffect(() => {
    if (!selectedRun) return;
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/runs/${selectedRun}/logs`, { method: "GET" });
      if (res.ok) setLogs(await res.json());
    })();
  }, [selectedRun]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Recent Runs</h1>
      <Card className="p-4">
        <Select value={selectedRun} onValueChange={setSelectedRun}>
          <SelectTrigger><SelectValue placeholder="Select a run" /></SelectTrigger>
          <SelectContent>
            {runs.map((r) => (
              <SelectItem key={r.id} value={r.id}>{r.id} · {r.status}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Card>
      <Card className="p-4 text-sm">
        {logs.map((l, i) => (
          <div key={i}>{l.ts} [{l.level}] {l.message}</div>
        ))}
      </Card>
    </div>
  );
}

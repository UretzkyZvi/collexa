"use client";
import { useEffect, useMemo, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card } from "~/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Switch } from "~/components/ui/switch";
import { LogViewer } from "~/components/LogViewer";
import { useRunLiveStream } from "~/lib/useRunLiveStream";

export default function LogsPage() {
  const authFetch = useAuthFetch();
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [logs, setLogs] = useState<any[]>([]);
  const [live, setLive] = useState(false);

  useEffect(() => {
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/runs`, { method: "GET" });
      if (res.ok) setRuns(await res.json());
    })();
  }, []);

  useEffect(() => {
    if (!selectedRun || live) return;
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/runs/${selectedRun}/logs`, { method: "GET" });
      if (res.ok) setLogs(await res.json());
    })();
  }, [selectedRun, live]);

  const { events: liveEvents } = useRunLiveStream(live && selectedRun ? selectedRun : null);
  const events = useMemo(
    () => (live ? liveEvents : logs.map((l) => ({ ts: l.ts, level: l.level, message: l.message }))),
    [live, liveEvents, logs]
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Recent Runs</h1>
      <Card className="flex items-center justify-between p-4">
        <div className="min-w-0 flex-1 pr-4">
          <Select value={selectedRun} onValueChange={setSelectedRun}>
            <SelectTrigger><SelectValue placeholder="Select a run" /></SelectTrigger>
            <SelectContent>
              {runs.map((r) => (
                <SelectItem key={r.id} value={r.id}>{r.id} · {r.status}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Switch checked={live} onChange={(e) => setLive((e.target as HTMLInputElement).checked)} label="Live" />
      </Card>
      <Card className="p-4">
        <LogViewer events={events} />
      </Card>
    </div>
  );
}

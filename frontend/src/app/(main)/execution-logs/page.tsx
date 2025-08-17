"use client";
import { useEffect, useMemo, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card } from "~/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Switch } from "~/components/ui/switch";
import { LogViewer } from "~/components/LogViewer";
import { useRunLiveStream } from "~/lib/useRunLiveStream";

function StatusBadge({ status }: { status?: string }) {
  const cls =
    status === "succeeded" ? "bg-green-600 text-white" :
    status === "failed" ? "bg-red-600 text-white" :
    status === "running" ? "bg-yellow-500 text-black" : "bg-muted text-foreground";
  return <span className={`rounded px-2 py-0.5 text-xs ${cls}`}>{status ?? "unknown"}</span>;
}

export default function LogsPage() {
  const authFetch = useAuthFetch();
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [logs, setLogs] = useState<any[]>([]);
  const [live, setLive] = useState(false);
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  async function refreshRuns() {
    const qs = new URLSearchParams();
    if (agentFilter) qs.set("agent_id", agentFilter);
    if (statusFilter) qs.set("status", statusFilter);
    const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/runs?${qs.toString()}`, { method: "GET" });
    if (res.ok) setRuns(await res.json());
  }

  useEffect(() => { void refreshRuns(); }, [agentFilter, statusFilter]);

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
      <Card className="flex flex-wrap items-center gap-4 p-4">
        <div className="min-w-0 flex-1 pr-2">
          <Select value={selectedRun} onValueChange={setSelectedRun}>
            <SelectTrigger><SelectValue placeholder="Select a run" /></SelectTrigger>
            <SelectContent>
              {runs.map((r) => (
                <SelectItem key={r.id} value={r.id}>{r.id} · <StatusBadge status={r.status} /></SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Switch checked={live} onChange={(e) => setLive((e.target as HTMLInputElement).checked)} label="Live" />
        </div>
        <div className="flex items-center gap-2">
          <input placeholder="Agent ID" className="rounded border px-2 py-1 text-sm" value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)} />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="running">running</SelectItem>
              <SelectItem value="succeeded">succeeded</SelectItem>
              <SelectItem value="failed">failed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>
      <Card className="p-4">
        <LogViewer events={events} />
      </Card>
    </div>
  );
}

"use client";
import { useEffect, useMemo, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card } from "~/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Switch } from "~/components/ui/switch";
import { Button } from "~/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { Calendar } from "~/components/ui/calendar";
import { ArrowUpDown } from "lucide-react";
import { LogViewer } from "~/components/LogViewer";
import { useRunLiveStream } from "~/lib/useRunLiveStream";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { DataTable } from "~/components/DataTable";
import { type ColumnDef } from "@tanstack/react-table";

function StatusBadge({ status }: { status?: string }) {
  const cls =
    status === "succeeded" ? "bg-green-600 text-white" :
    status === "failed" ? "bg-red-600 text-white" :
    status === "running" ? "bg-yellow-500 text-black" : "bg-muted text-foreground";
  return <span className={`rounded px-2 py-0.5 text-xs ${cls}`}>{status ?? "unknown"}</span>;
}

export default function LogsPage() {
  const authFetch = useAuthFetch();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [runs, setRuns] = useState<any[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [logs, setLogs] = useState<any[]>([]);
  const [live, setLive] = useState(false);
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [agents, setAgents] = useState<Array<{ id: string; display_name?: string }>>([]);

  async function refreshRuns(page = 0, pageSize = 20) {
    setRunsLoading(true);
    try {
      const qs = new URLSearchParams();
      if (agentFilter) qs.set("agent_id", agentFilter);
      if (statusFilter) qs.set("status", statusFilter);
      if (dateFrom) qs.set("from", dateFrom);
      if (dateTo) qs.set("to", dateTo);
      qs.set("offset", String(page * pageSize));
      qs.set("limit", String(pageSize));
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/runs?${qs.toString()}`, { method: "GET" });
      if (res.ok) setRuns(await res.json());
    } finally {
      setRunsLoading(false);
    }
  }

  // Sync from querystring on mount
  useEffect(() => {
    const a = searchParams.get("agent_id") || "";
    const s = searchParams.get("status") || "";
    const f = searchParams.get("from") || "";
    const t = searchParams.get("to") || "";
    setAgentFilter(a);
    setStatusFilter(s);
    setDateFrom(f);
    setDateTo(t);
    void refreshRuns();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch agents for Agent Select
  useEffect(() => {
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents`, { method: "GET" });
      if (res.ok) setAgents(await res.json());
    })();
  }, []);

  // Update querystring and refresh when filters change
  useEffect(() => {
    const qs = new URLSearchParams();
    if (agentFilter) qs.set("agent_id", agentFilter);
    if (statusFilter) qs.set("status", statusFilter);
    if (dateFrom) qs.set("from", dateFrom);
    if (dateTo) qs.set("to", dateTo);
    router.replace(`/execution-logs?${qs.toString()}`);
    void refreshRuns();
  }, [agentFilter, statusFilter, dateFrom, dateTo]);

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

  const columns = useMemo<ColumnDef<any, any>[]>(() => [
    {
      accessorKey: "id",
      header: ({ column }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Run ID <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.id}</span>,
    },
    {
      accessorKey: "agent_id",
      header: ({ column }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Agent <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.agent_id}</span>,
    },
    {
      accessorKey: "status",
      header: ({ column }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Status <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: "created_at",
      header: ({ column }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Created <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => <span className="text-xs">{row.original.created_at ? new Date(row.original.created_at).toLocaleString() : ""}</span>,
    },
    {
      header: "",
      id: "actions",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => setSelectedRun(row.original.id)}>View</Button>
          <Link href={`/execution-logs/${row.original.id}`} className="underline text-xs">Replay</Link>
        </div>
      ),
      enableSorting: false,
    },
  ], [setSelectedRun]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Recent Runs</h1>
      <Card className="flex flex-wrap items-center gap-4 p-4">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <Switch checked={live} onCheckedChange={setLive} />
            <span className="text-sm text-muted-foreground">Live</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Select value={agentFilter} onValueChange={setAgentFilter}>
            <SelectTrigger className="w-[200px]"><SelectValue placeholder="Agent" /></SelectTrigger>
            <SelectContent>
              {agents.map((a) => (
                <SelectItem key={a.id} value={a.id}>{a.display_name || a.id}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[160px]"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="running">running</SelectItem>
              <SelectItem value="succeeded">succeeded</SelectItem>
              <SelectItem value="failed">failed</SelectItem>
            </SelectContent>
          </Select>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm">
                {dateFrom && dateTo ? `${dateFrom} → ${dateTo}` : "Date range"}
              </Button>
            </PopoverTrigger>
            <PopoverContent align="start" className="p-0">
              <div className="p-2">
                <Calendar
                  mode="range"
                  numberOfMonths={2}
                  selected={{ from: dateFrom ? new Date(dateFrom) : undefined, to: dateTo ? new Date(dateTo) : undefined }}
                  onSelect={(range) => {
                    const from = range?.from ? range.from.toISOString().slice(0, 10) : "";
                    const to = range?.to ? range.to.toISOString().slice(0, 10) : "";
                    setDateFrom(from);
                    setDateTo(to);
                  }}
                />
              </div>
            </PopoverContent>
          </Popover>
        </div>
      </Card>

      <Card className="p-0 overflow-hidden">
        <DataTable columns={columns} data={runs} loading={runsLoading} onPageChange={(page, size) => void refreshRuns(page, size)} />
      </Card>

      <Card className="p-4">
        <LogViewer events={events} />
      </Card>
    </div>
  );
}

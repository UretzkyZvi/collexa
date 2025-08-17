"use client";
import { useEffect, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card } from "~/components/ui/card";
import Link from "next/link";

export default function AgentsPage() {
  const authFetch = useAuthFetch();
  const [agents, setAgents] = useState<any[]>([]);

  useEffect(() => {
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents`, { method: "GET" });
      if (res.ok) setAgents(await res.json());
    })();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
          <h1 className="text-2xl font-bold">Agents</h1>
        <Link className="rounded bg-indigo-600 px-3 py-1 text-white" href="/agents/new">Create New Agent</Link>
      </div>
    

      <Card className="p-4">
        <ul className="list-disc pl-6 text-sm">
          {agents.map((a) => (
            <li key={a.id}>
              <span className="font-medium">{a.display_name || a.id}</span>
              <span className="text-muted-foreground"> · {a.id}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}


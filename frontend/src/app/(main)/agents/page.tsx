"use client";
import { useEffect, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card } from "~/components/ui/card";

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
      <h1 className="text-2xl font-bold">Agents</h1>
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


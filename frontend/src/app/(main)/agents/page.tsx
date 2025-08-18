"use client";
import { useEffect, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Skeleton } from "~/components/ui/skeleton";
import Link from "next/link";

interface Agent {
  id: string;
  display_name: string;
  created_at?: string;
}

export default function AgentsPage() {
  const authFetch = useAuthFetch();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents`, { method: "GET" });
      if (res.ok) {
        const data = await res.json();
        setAgents(data);
      } else {
        setError("Failed to load agents");
      }
    } catch (err) {
      setError("Failed to load agents");
      console.error("Error loading agents:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">Agents</h1>
          <Skeleton className="h-9 w-32" />
        </div>
        <Card className="p-4">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-6 w-full" />
            ))}
          </div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">Agents</h1>
          <Button asChild>
            <Link href="/agents/new">Create New Agent</Link>
          </Button>
        </div>
        <Card className="p-4">
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{error}</p>
            <Button onClick={loadAgents} variant="outline">
              Try Again
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Agents</h1>
        <Button asChild>
          <Link href="/agents/new">Create New Agent</Link>
        </Button>
      </div>

      {agents.length === 0 ? (
        <Card className="p-8">
          <div className="text-center">
            <h3 className="text-lg font-medium mb-2">No agents yet</h3>
            <p className="text-muted-foreground mb-4">
              Create your first agent to get started with AI automation.
            </p>
            <Button asChild>
              <Link href="/agents/new">Create Your First Agent</Link>
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Card key={agent.id} className="p-4 hover:shadow-md transition-shadow">
              <div className="space-y-2">
                <h3 className="font-medium text-lg">{agent.display_name || "Unnamed Agent"}</h3>
                <p className="text-sm text-muted-foreground font-mono">{agent.id}</p>
                {agent.created_at && (
                  <p className="text-xs text-muted-foreground">
                    Created {new Date(agent.created_at).toLocaleDateString()}
                  </p>
                )}
                <div className="flex gap-2 pt-2">
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/agents/${agent.id}`}>View</Link>
                  </Button>
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/agents/${agent.id}/instructions`}>Instructions</Link>
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}


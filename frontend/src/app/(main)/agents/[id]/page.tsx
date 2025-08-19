"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthFetch } from "~/lib/authFetch";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Skeleton } from "~/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Badge } from "~/components/ui/badge";
import { Separator } from "~/components/ui/separator";

interface Agent {
  id: string;
  display_name: string;
  org_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

interface SandboxService {
  url: string;
  status: string;
  endpoints: string[];
}

interface Sandbox {
  sandbox_id: string;
  agent_id: string;
  status: string;
  services: Record<string, SandboxService>;
  proxy_url: string;
  created_at: string;
  expires_at: string;
  last_accessed?: string;
  ttl_minutes?: number;
}

interface SandboxRun {
  run_id: string;
  sandbox_id: string;
  phase: string;
  status: string;
  started_at: string;
  completed_at?: string;
  metrics?: Record<string, any>;
}

export default function AgentDetailPage({ params }: { params: { id: string } }) {
  const authFetch = useAuthFetch();
  const router = useRouter();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [sandboxes, setSandboxes] = useState<Sandbox[]>([]);
  const [sandboxRuns, setSandboxRuns] = useState<SandboxRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [sandboxLoading, setSandboxLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAgent();
    loadSandboxes();
  }, [params.id]);

  const loadAgent = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents/${params.id}`, { method: "GET" });
      if (res.ok) {
        const data = await res.json();
        setAgent(data);
      } else if (res.status === 404) {
        router.replace("/404");
        return;
      } else {
        setError("Failed to load agent");
      }
    } catch (err) {
      setError("Failed to load agent");
      console.error("Error loading agent:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadSandboxes = async () => {
    try {
      setSandboxLoading(true);
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents/${params.id}/sandboxes`, { method: "GET" });
      if (res.ok) {
        const data = await res.json();
        setSandboxes(data.sandboxes || []);

        // For now, we'll skip loading runs since the dynamic system doesn't have runs yet
        // This can be implemented later when we add run tracking to the dynamic orchestrator
        setSandboxRuns([]);
      }
    } catch (err) {
      console.error("Error loading sandboxes:", err);
    } finally {
      setSandboxLoading(false);
    }
  };

  const createSandbox = async (targetSystem: string) => {
    try {
      setSandboxLoading(true);
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents/${params.id}/sandboxes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          required_services: [targetSystem],
          custom_configs: {
            [targetSystem]: {
              service_type: targetSystem,
              workspace_config: {
                environment: "agent_testing",
                created_by: `agent_${params.id}`
              }
            }
          },
          ttl_minutes: 120
        })
      });

      if (res.ok) {
        await loadSandboxes(); // Reload sandboxes
      } else {
        const errorData = await res.json();
        setError(errorData.detail || "Failed to create sandbox");
      }
    } catch (err) {
      setError("Failed to create sandbox");
      console.error("Error creating sandbox:", err);
    } finally {
      setSandboxLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-48" />
          </div>
          <Skeleton className="h-9 w-32" />
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Card className="p-8">
          <div className="text-center">
            <h3 className="text-lg font-medium mb-2 text-destructive">Error</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={() => window.location.reload()}>Try Again</Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!agent) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold">{agent.display_name || "Unnamed Agent"}</h1>
          <p className="text-muted-foreground font-mono text-sm">{agent.id}</p>
          <p className="text-xs text-muted-foreground">
            Created {new Date(agent.created_at).toLocaleDateString()} • 
            Updated {new Date(agent.updated_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href={`/agents/${agent.id}/instructions`}>Instructions</Link>
          </Button>
          <Button asChild>
            <Link href="/playground">Test in Playground</Link>
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="sandbox">Sandbox</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Agent Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Display Name</label>
                  <p className="text-sm">{agent.display_name || "Unnamed Agent"}</p>
                </div>
                <Separator />
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Agent ID</label>
                  <p className="text-sm font-mono">{agent.id}</p>
                </div>
                <Separator />
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Organization</label>
                  <p className="text-sm font-mono">{agent.org_id}</p>
                </div>
                <Separator />
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Created By</label>
                  <p className="text-sm font-mono">{agent.created_by}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Quick Stats</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Active Sandboxes</span>
                  <Badge variant="secondary">{sandboxes.filter(s => s.status === "running").length}</Badge>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total Sandboxes</span>
                  <Badge variant="outline">{sandboxes.length}</Badge>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Recent Runs</span>
                  <Badge variant="outline">{sandboxRuns.length}</Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="sandbox" className="space-y-4">
          {/* Sandbox content will be added here */}
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-semibold">Sandbox Environments</h3>
              <p className="text-sm text-muted-foreground">
                Test your agent in isolated environments with mock APIs
              </p>
            </div>
            <div className="flex gap-2">
              <Button 
                onClick={() => createSandbox("figma")} 
                disabled={sandboxLoading}
                variant="outline"
                size="sm"
              >
                {sandboxLoading ? "Creating..." : "Create Figma Sandbox"}
              </Button>
              <Button 
                onClick={() => createSandbox("slack")} 
                disabled={sandboxLoading}
                variant="outline"
                size="sm"
              >
                {sandboxLoading ? "Creating..." : "Create Slack Sandbox"}
              </Button>
              <Button 
                onClick={() => createSandbox("generic")} 
                disabled={sandboxLoading}
                variant="outline"
                size="sm"
              >
                {sandboxLoading ? "Creating..." : "Create Generic Sandbox"}
              </Button>
            </div>
          </div>

          {sandboxes.length === 0 ? (
            <Card className="p-8">
              <div className="text-center">
                <h3 className="text-lg font-medium mb-2">No sandboxes yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create a sandbox environment to test your agent safely with mock APIs.
                </p>
                <div className="flex gap-2 justify-center">
                  <Button onClick={() => createSandbox("figma")} disabled={sandboxLoading}>
                    Create Figma Sandbox
                  </Button>
                  <Button onClick={() => createSandbox("slack")} disabled={sandboxLoading} variant="outline">
                    Create Slack Sandbox
                  </Button>
                </div>
              </div>
            </Card>
          ) : (
            <div className="grid gap-4">
              {sandboxes.map((sandbox) => (
                <Card key={sandbox.sandbox_id}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-base">
                          {Object.keys(sandbox.services).length > 0
                            ? `${Object.keys(sandbox.services).map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(" + ")} Sandbox`
                            : "Dynamic Sandbox"
                          }
                        </CardTitle>
                        <CardDescription className="font-mono text-xs">
                          {sandbox.sandbox_id}
                        </CardDescription>
                      </div>
                      <div className="flex gap-2">
                        <Badge variant={sandbox.status === "running" ? "default" : "secondary"}>
                          {sandbox.status}
                        </Badge>
                        <Badge variant="outline">
                          {Object.keys(sandbox.services).length} service{Object.keys(sandbox.services).length !== 1 ? 's' : ''}
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Proxy URL</label>
                      <p className="text-sm font-mono bg-muted p-2 rounded mt-1">
                        {sandbox.proxy_url}
                      </p>
                    </div>

                    {Object.keys(sandbox.services).length > 0 && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Active Services</label>
                        <div className="mt-2 space-y-2">
                          {Object.entries(sandbox.services).map(([serviceName, service]) => (
                            <div key={serviceName} className="border rounded p-3">
                              <div className="flex justify-between items-center mb-2">
                                <span className="font-medium text-sm capitalize">{serviceName}</span>
                                <Badge variant={service.status === "running" ? "default" : "secondary"}>
                                  {service.status}
                                </Badge>
                              </div>
                              <div className="text-xs text-muted-foreground mb-2">
                                URL: <span className="font-mono">{service.url}</span>
                              </div>
                              {service.endpoints.length > 0 && (
                                <div className="text-xs">
                                  <span className="text-muted-foreground">Endpoints: </span>
                                  <span className="font-mono">{service.endpoints.join(", ")}</span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex justify-between items-start pt-2">
                      <div className="text-xs text-muted-foreground space-y-1">
                        <div>Created {new Date(sandbox.created_at).toLocaleDateString()}</div>
                        {sandbox.expires_at && (
                          <div>Expires {new Date(sandbox.expires_at).toLocaleDateString()}</div>
                        )}
                        {sandbox.ttl_minutes && (
                          <div>TTL: {sandbox.ttl_minutes} minutes</div>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" asChild>
                          <a href={sandbox.proxy_url} target="_blank" rel="noopener noreferrer">
                            Open Proxy
                          </a>
                        </Button>
                        <Button size="sm" variant="outline">
                          View Runs
                        </Button>
                        <Button size="sm" variant="destructive">
                          Delete
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>
                Sandbox runs and execution logs for this agent
              </CardDescription>
            </CardHeader>
            <CardContent>
              {sandboxRuns.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No recent activity</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {sandboxRuns.slice(0, 10).map((run) => (
                    <div key={run.run_id} className="flex justify-between items-center p-3 border rounded">
                      <div>
                        <p className="text-sm font-medium">Run {run.run_id.slice(0, 8)}</p>
                        <p className="text-xs text-muted-foreground">
                          Phase: {run.phase} • Status: {run.status}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">
                          {new Date(run.started_at).toLocaleString()}
                        </p>
                        {run.completed_at && (
                          <p className="text-xs text-muted-foreground">
                            Completed {new Date(run.completed_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

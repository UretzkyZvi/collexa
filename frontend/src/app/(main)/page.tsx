"use client";
import { useEffect, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Skeleton } from "~/components/ui/skeleton";
import Link from "next/link";

interface DashboardStats {
  agents_count: number;
  api_calls_today: number;
  recent_invocations: Array<{
    agent_id: string;
    capability: string;
    status: string;
    created_at: string;
  }>;
}

interface MetricsData {
  org_id: string;
  api_calls: {
    total: number;
    errors: number;
    success_rate: number;
  };
  request_duration_ms: {
    count: number;
    p50: number;
    p95: number;
    p99: number;
    avg: number;
  };
  agent_invocations: {
    total: number;
    duration_ms: {
      count: number;
      p50: number;
      p95: number;
      p99: number;
      avg: number;
    };
  };
}

export default function HomePage() {
  const authFetch = useAuthFetch();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Load agents count
      const agentsRes = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents`);
      const agents = agentsRes.ok ? await agentsRes.json() : [];

      // Load metrics data
      const metricsRes = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/metrics`);
      const metricsData = metricsRes.ok ? await metricsRes.json() : null;

      setStats({
        agents_count: agents.length,
        api_calls_today: metricsData?.api_calls?.total || 0,
        recent_invocations: [], // Would come from actual API
      });

      setMetrics(metricsData);
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-8 w-16" />
              </CardHeader>
            </Card>
          ))}
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Button asChild>
          <Link href="/agents/new">Create Agent</Link>
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Agents</CardTitle>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              className="h-4 w-4 text-muted-foreground"
            >
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="m22 21-3-3m0 0a5 5 0 1 0-7-7 5 5 0 0 0 7 7z" />
            </svg>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.agents_count || 0}</div>
            <p className="text-xs text-muted-foreground">
              {stats?.agents_count === 0 ? "Create your first agent" : "Active agents"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Calls Total</CardTitle>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              className="h-4 w-4 text-muted-foreground"
            >
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.api_calls?.total || 0}</div>
            <p className="text-xs text-muted-foreground">
              {metrics?.api_calls?.errors || 0} errors
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              className="h-4 w-4 text-muted-foreground"
            >
              <polyline points="22,6 12,16 2,6" />
            </svg>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.api_calls?.success_rate
                ? `${(metrics.api_calls.success_rate * 100).toFixed(1)}%`
                : "100%"
              }
            </div>
            <p className="text-xs text-muted-foreground">
              API call success rate
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Get started with common tasks
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Button asChild variant="outline" className="h-20 flex-col">
              <Link href="/agents/new">
                <div className="text-lg mb-1">🤖</div>
                <div>Create Agent</div>
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-20 flex-col">
              <Link href="/playground">
                <div className="text-lg mb-1">🎮</div>
                <div>Test Playground</div>
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-20 flex-col">
              <Link href="/settings">
                <div className="text-lg mb-1">🔑</div>
                <div>Manage API Keys</div>
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-20 flex-col">
              <Link href="/execution-logs">
                <div className="text-lg mb-1">📊</div>
                <div>View Logs</div>
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Performance Metrics */}
      {metrics && metrics.api_calls.total > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Request Performance</CardTitle>
              <CardDescription>API response times</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Average:</span>
                  <span className="text-sm font-medium">
                    {metrics.request_duration_ms.avg.toFixed(1)}ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">P50:</span>
                  <span className="text-sm font-medium">
                    {metrics.request_duration_ms.p50.toFixed(1)}ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">P95:</span>
                  <span className="text-sm font-medium">
                    {metrics.request_duration_ms.p95.toFixed(1)}ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">P99:</span>
                  <span className="text-sm font-medium">
                    {metrics.request_duration_ms.p99.toFixed(1)}ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total Requests:</span>
                  <span className="text-sm font-medium">
                    {metrics.request_duration_ms.count}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Agent Invocations</CardTitle>
              <CardDescription>Agent execution performance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total Invocations:</span>
                  <span className="text-sm font-medium">
                    {metrics.agent_invocations.total}
                  </span>
                </div>
                {metrics.agent_invocations.duration_ms.count > 0 && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Avg Duration:</span>
                      <span className="text-sm font-medium">
                        {metrics.agent_invocations.duration_ms.avg.toFixed(1)}ms
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">P95 Duration:</span>
                      <span className="text-sm font-medium">
                        {metrics.agent_invocations.duration_ms.p95.toFixed(1)}ms
                      </span>
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Getting Started */}
      {stats?.agents_count === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Welcome to Collexa! 🎉</CardTitle>
            <CardDescription>
              Get started by creating your first AI agent
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Collexa helps you create and manage AI agents that can be integrated with external tools like n8n, Make.com, and custom applications.
              </p>
              <div className="flex gap-2">
                <Button asChild>
                  <Link href="/agents/new">Create Your First Agent</Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/playground">Try the Playground</Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

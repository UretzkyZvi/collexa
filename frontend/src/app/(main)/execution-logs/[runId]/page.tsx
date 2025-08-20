"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";

export default function RunDetailsPage() {
  const { runId } = useParams<{ runId: string }>();
  const authFetch = useAuthFetch();
  const [run, setRun] = useState<any | null>(null);
  const [replaying, setReplaying] = useState(false);

  useEffect(() => {
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/runs/${runId}`);
      if (res.ok) setRun(await res.json());
    })();
  }, [runId]);

  async function replay() {
    setReplaying(true);
    try {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/runs/${runId}/replay`, { method: "POST" });
      if (!res.ok) throw new Error("Replay not available");
      // Optional: navigate to the new run id or show a toast
    } catch (e) {
      // Placeholder behavior for now
      console.warn("Replay endpoint not available yet.");
    } finally {
      setReplaying(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Run {runId}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Details to be expanded when backend provides full schema.</div>
        </CardContent>
      </Card>
      <Button onClick={replay} disabled={replaying}>{replaying ? "Replaying..." : "Replay"}</Button>
    </div>
  );
}


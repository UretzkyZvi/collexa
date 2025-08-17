"use client";

import { useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card } from "~/components/ui/card";
import { Textarea } from "~/components/ui/textarea";
import { Button } from "~/components/ui/button";
import { Label } from "~/components/ui/label";

export default function NewAgentPage() {
  const [brief, setBrief] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const authFetch = useAuthFetch();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief }),
      });
      const data = await res.json();
      setResult(data);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">Create a new Agent</h1>
      <Card className="p-4 space-y-3">
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1">
            <Label>Agent brief</Label>
            <Textarea
              rows={6}
              placeholder="Describe your agent (e.g., 'UX designer for 3 months to improve onboarding by 15%')"
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
            />
          </div>
          <Button disabled={submitting} type="submit">
            {submitting ? "Creating..." : "Create Agent"}
          </Button>
        </form>
      </Card>
      {result && (
        <Card className="p-4">
          <pre className="overflow-auto text-sm">{JSON.stringify(result, null, 2)}</pre>
        </Card>
      )}
    </div>
  );
}


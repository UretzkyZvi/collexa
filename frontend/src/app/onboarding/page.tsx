"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@stackframe/stack";
import { Card } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { Label } from "~/components/ui/label";
import { Button } from "~/components/ui/button";

export default function OnboardingPage() {
  const user = useUser({ or: "redirect" });
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onCreateTeam(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!displayName.trim()) {
      setError("Team name is required");
      return;
    }
    setCreating(true);
    try {
      const team = await user.createTeam({ displayName });
      if (description.trim()) {
        await team.update({ clientMetadata: { description: description.trim() } });
      }
      await user.setSelectedTeam(team);
      router.replace("/");
    } catch (err: any) {
      setError(err?.message ?? "Failed to create team");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4 p-6">
      <div>
        <h1 className="text-2xl font-bold">Create your team</h1>
        <p className="text-sm text-muted-foreground">
          To get started, create your first team. Teams help organize access and data for members of your organization.
        </p>
      </div>

      <Card className="p-4">
        <form onSubmit={onCreateTeam} className="space-y-4">
          <div className="space-y-1">
            <Label>Team name</Label>
            <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="e.g., Acme, Inc." />
          </div>
          <div className="space-y-1">
            <Label>Description (optional)</Label>
            <Textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Short description of your team" />
          </div>
          {error && <div className="rounded bg-red-900/40 p-2 text-sm text-red-200">{error}</div>}
          <Button type="submit" disabled={creating}>{creating ? "Creating…" : "Create Team"}</Button>
        </form>
      </Card>
    </div>
  );
}


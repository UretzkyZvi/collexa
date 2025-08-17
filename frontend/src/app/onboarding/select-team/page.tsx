"use client";
import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@stackframe/stack";
import { Card } from "~/components/ui/card";
import { Button } from "~/components/ui/button";

export default function SelectTeamPage() {
  const user = useUser({ or: "redirect" });
  const router = useRouter();
  const teams = (user as any)?.useTeams?.() ?? [];

  const sorted = useMemo(() => teams.slice().sort((a: any,b: any) => (a.displayName||"").localeCompare(b.displayName||"")), [teams]);

  async function selectTeam(team: any) {
    await user.setSelectedTeam(team);
    router.replace("/");
  }

  return (
    <div className="mx-auto max-w-md space-y-4 p-6">
      <div>
        <h1 className="text-2xl font-bold">Select a team</h1>
        <p className="text-sm text-muted-foreground">Choose which team to use with the app. You can change this later.</p>
      </div>
      <Card className="p-2 space-y-2">
        {sorted.map((t: any) => (
          <Button key={t.id} variant="outline" className="w-full justify-between" onClick={() => selectTeam(t)}>
            <span>{t.displayName ?? t.id}</span>
            <span className="text-xs text-muted-foreground">{t.id}</span>
          </Button>
        ))}
      </Card>
    </div>
  );
}


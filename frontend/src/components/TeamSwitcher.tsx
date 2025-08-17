"use client";
import { useMemo, useState } from "react";
import { useUser } from "@stackframe/stack";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";

export function TeamSwitcher() {
  const user = useUser();
  const teams = (user as any)?.useTeams?.() ?? [];
  const selectedTeam = (user as any)?.selectedTeam ?? null;
  const [pending, setPending] = useState<string | null>(null);

  const items = useMemo(() => teams.map((t: any) => ({ id: t.id, name: t.displayName ?? t.id })), [teams]);

  async function onChange(val: string) {
    setPending(val);
    try {
      const team = teams.find((t: any) => t.id === val);
      if (team) await (user as any).setSelectedTeam(team);
    } finally {
      setPending(null);
    }
  }

  return (
    <Select value={selectedTeam?.id} onValueChange={onChange} disabled={pending !== null}>
      <SelectTrigger className="h-8 w-full">
        <SelectValue placeholder="Select team" />
      </SelectTrigger>
      <SelectContent>
        {items.map((t) => (
          <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}


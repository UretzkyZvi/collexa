"use client";
import { useMemo, useState } from "react";
import { type CurrentInternalUser, type CurrentUser, type Team, useUser } from "@stackframe/stack";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";

export function TeamSwitcher() {
  const user = useUser() as CurrentUser | CurrentInternalUser | null;
  const teams = user?.useTeams?.() ?? [];
  const selectedTeam = user?.selectedTeam ?? null;
  const [pending, setPending] = useState<string | null>(null);

  const items = useMemo(() => teams.map((t: Team) => ({ id: t.id as string, name: (t.displayName ?? t.id) as string })), [teams]);

  async function onChange(val: string) {
    setPending(val);
    try {
      const team = teams.find((t: Team) => t.id as string === val);
      if (team) await user?.setSelectedTeam(team);
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
        {items.map((t: { id: string; name: string }) => (
          <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}


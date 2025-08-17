"use client";
import { useEffect } from "react";
import { useUser } from "@stackframe/stack";
import { usePathname, useRouter } from "next/navigation";

export default function OnboardingGate() {
  const user = useUser();
  const pathname = usePathname();
  const router = useRouter();

  // Avoid redirect loops on these routes
  const allowlistPrefixes = ["/onboarding", "/handler", "/api", "/health"];
  const isAllowlisted = allowlistPrefixes.some((p) => pathname?.startsWith(p));

  // Synchronous hooks from Stack user
  const teams = (user as any)?.useTeams?.() ?? [];
  const selectedTeam = (user as any)?.selectedTeam ?? null;

  useEffect(() => {
    if (!user) return; // not signed in or loading
    if (isAllowlisted) return;

    if (teams.length === 0) {
      router.replace("/onboarding");
      return;
    }
    if (!selectedTeam && teams.length > 0) {
      router.replace("/onboarding/select-team");
      return;
    }
  }, [user, teams?.length, selectedTeam?.id, isAllowlisted, pathname]);

  return null;
}


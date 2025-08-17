"use client";
import { useUser } from "@stackframe/stack";

type FetchOptions = RequestInit & { auth?: boolean; teamId?: string | null };

export function useAuthFetch() {
  const user = useUser();

  return async function authFetch(input: string | URL, init?: FetchOptions) {
    const opts: RequestInit = { ...(init ?? {}) };
    if (init?.auth !== false && user) {
      const { accessToken } = await user.getAuthJson();
      // Prefer explicit teamId, otherwise use selectedTeam from user
      const teamId = (init as any)?.teamId ?? (user.selectedTeam?.id ?? null);
      const headers: Record<string, string> = {
        ...(opts.headers as Record<string, string> | undefined),
        Authorization: `Bearer ${accessToken}`,
      };
      if (teamId) headers["X-Team-Id"] = teamId;
      opts.headers = headers;
    }
    return fetch(input, opts);
  };
}


"use client";
import { useUser } from "@stackframe/stack";
import { useProjectContext } from "~/hooks/project-context";

type FetchOptions = RequestInit & { auth?: boolean; teamId?: string | null };

export function useAuthFetch() {
  const user = useUser();
  const { selectedProjectId } = useProjectContext();

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
      if (selectedProjectId) headers["X-Project-Id"] = selectedProjectId;
      opts.headers = headers;
    }
    return fetch(input, opts);
  };
}


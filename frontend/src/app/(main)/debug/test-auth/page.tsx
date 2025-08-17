"use client";
import { useUser } from "@stackframe/stack";
import { useAuthFetch } from "~/lib/authFetch";

export default function TestAuthPage() {
  const user = useUser({ or: "redirect" });
const authFetch = useAuthFetch();
  const run = async () => {
    const { accessToken } = await user.getAuthJson();
    const teamId = (user as any)?.selectedTeam?.id ?? null;
    const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      // authFetch will add X-Team-Id automatically if teamId is provided or selectedTeam is set
      // Pass teamId explicitly in case selectedTeam isn't synced yet
      ...(teamId ? { teamId } : {} as any),
      body: JSON.stringify({ brief: "e2e test" }),
    });
    const text = await res.text();
    alert(`${res.status} ${text}`);
  };

  const me = async () => {
    const teamId = (user as any)?.selectedTeam?.id ?? null;
    const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/debug/me`, {
      method: "GET",
      ...(teamId ? { teamId } : {} as any),
    });
    const text = await res.text();
    alert(`${res.status} ${text}`);
  };

  return (
    <main className="mx-auto max-w-xl p-6 space-y-4">
      <h1 className="text-xl font-semibold">Auth E2E Test</h1>
      <div className="flex gap-3">
        <button className="rounded bg-indigo-600 px-3 py-1 text-white" onClick={run}>Test POST /v1/agents</button>
        <button className="rounded bg-slate-600 px-3 py-1 text-white" onClick={me}>Test GET /v1/debug/me</button>
      </div>
    </main>
  );
}


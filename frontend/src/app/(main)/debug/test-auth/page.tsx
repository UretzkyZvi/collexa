"use client";
import { useUser } from "@stackframe/stack";

export default function TestAuthPage() {
  const user = useUser({ or: "redirect" });

  const run = async () => {
    const { accessToken } = await user.getAuthJson();
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ brief: "e2e test" }),
    });
    const text = await res.text();
    alert(`${res.status} ${text}`);
  };

  const me = async () => {
    const { accessToken } = await user.getAuthJson();
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/debug/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
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


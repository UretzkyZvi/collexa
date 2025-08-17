"use client";

import { useEffect, useRef, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { Card } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { Button } from "~/components/ui/button";

export default function PlaygroundPage() {
  const [agentId, setAgentId] = useState("");
  const [capability, setCapability] = useState("");
  const [inputJson, setInputJson] = useState("{}");
  const [stream, setStream] = useState<string[]>([]);
  const evtSrcRef = useRef<EventSource | null>(null);
  const authFetch = useAuthFetch();

  async function startInvoke() {
    setStream([]);
    await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents/${agentId}/invoke`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ capability, input: JSON.parse(inputJson) }),
    });

    if (evtSrcRef.current) evtSrcRef.current.close();
    // SSE: include auth token via ?token= and team via ?team= for PoC simplicity
    const { accessToken } = await (await (useAuthFetch as any)().user?.getAuthJson?.()) ?? { accessToken: "" };
    const teamId = (useAuthFetch as any)().user?.selectedTeam?.id ?? "";
    const url = `${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents/${agentId}/logs?since=now&token=${encodeURIComponent(accessToken)}&team=${encodeURIComponent(teamId)}`;
    const es = new EventSource(url);
    es.onmessage = (e) => setStream((s) => [...s, e.data]);
    es.onerror = () => es.close();
    evtSrcRef.current = es;
  }

  useEffect(() => {
    return () => evtSrcRef.current?.close();
  }, []);

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">Playground</h1>
      <Card className="space-y-3 p-4">
        <Input placeholder="Agent ID" value={agentId} onChange={(e) => setAgentId(e.target.value)} />
        <Input placeholder="Capability" value={capability} onChange={(e) => setCapability(e.target.value)} />
        <Textarea rows={6} value={inputJson} onChange={(e) => setInputJson(e.target.value)} />
        <Button onClick={startInvoke}>Invoke</Button>
      </Card>
      <Card className="p-3 text-sm">
        {stream.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </Card>
    </div>
  );
}


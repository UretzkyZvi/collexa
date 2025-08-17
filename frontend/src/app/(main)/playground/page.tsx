"use client";

import { useEffect, useRef, useState } from "react";
import { useUser } from "@stackframe/stack";
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
  const [finalResult, setFinalResult] = useState<any | null>(null);
  const evtSrcRef = useRef<EventSource | null>(null);
  const authFetch = useAuthFetch();
  const user = useUser();

  async function startInvoke() {
    setStream([]);
    setFinalResult(null);
    await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents/${agentId}/invoke`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ capability, input: JSON.parse(inputJson) }),
    });

    if (evtSrcRef.current) evtSrcRef.current.close();
    // SSE: include auth token via ?token= and team via ?team=
    const { accessToken } = await user!.getAuthJson();
    const teamId = String((user as any)?.selectedTeam?.id ?? "");
    const url = `${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents/${agentId}/logs?since=now&token=${encodeURIComponent(accessToken ?? "")}&team=${encodeURIComponent(teamId ?? "")}`;
    const es = new EventSource(url);
    es.onmessage = (e) => {
      setStream((s) => [...s, e.data]);
      try {
        const msg = JSON.parse(e.data);
        if (msg?.type === "complete") {
          setFinalResult(msg.output ?? msg);
        }
      } catch {}
    };
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
      <Card className="p-3 text-sm space-y-2">
        <div>
          <div className="mb-1 font-semibold">Stream</div>
          {stream.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
        {finalResult && (
          <div>
            <div className="mb-1 font-semibold">Final Result</div>
            <pre className="overflow-auto rounded bg-black/40 p-2 text-xs" data-testid="final-result">
              {JSON.stringify(finalResult, null, 2)}
            </pre>
          </div>
        )}
      </Card>
    </div>
  );
}


"use client";
import { useEffect, useRef, useState } from "react";
import { useUser } from "@stackframe/stack";

export type StreamEvent = { type: string; [k: string]: any };
export type LogLike = { ts?: string; level?: string; message: string };

export function useRunLiveStream(runId: string | null) {
  const user = useUser();
  const [events, setEvents] = useState<LogLike[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    (async () => {
      try {
        const { accessToken } = user ? await user.getAuthJson() : { accessToken: "" } as { accessToken: string };
        const token = accessToken ?? "";
        const teamId: string = (user?.selectedTeam?.id as string | undefined) ?? "";
        const base = process.env.NEXT_PUBLIC_API_BASE_URL;
        const url = `${base}/v1/runs/${String(runId)}/stream?token=${encodeURIComponent(token)}&team=${encodeURIComponent(teamId)}`;
        const es = new EventSource(url);
        es.onopen = () => !cancelled && setConnected(true);
        es.onmessage = (e) => {
          try {
            const obj = JSON.parse(e.data) as StreamEvent;
            if (obj.type === "log") {
              setEvents((prev) => [...prev, { ts: obj.ts, level: obj.level, message: obj.message ?? "" }]);
            } else if (obj.type === "complete") {
              setEvents((prev) => [...prev, { ts: obj.ts, level: "info", message: `complete: ${JSON.stringify(obj.output)}` }]);
            }
          } catch {
            // ignore keep-alives or malformed
          }
        };
        es.onerror = () => {
          setConnected(false);
          es.close();
        };
        esRef.current = es;
      } catch {
        // ignore
      }
    })();
    return () => {
      cancelled = true;
      esRef.current?.close();
      setConnected(false);
    };
  }, [runId]);

  return { events, connected };
}


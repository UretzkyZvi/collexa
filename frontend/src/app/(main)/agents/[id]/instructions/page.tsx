"use client";
import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuthFetch } from "~/lib/authFetch";

import { CodeBlock } from "~/components/CodeBlock";

type Instruction = { id: string; label: string; language: string; code: string };

function copy(text: string) {
  try {
    void navigator.clipboard.writeText(text);
  } catch {
    // ignore clipboard errors (unsupported environment)
  }
}

export default function InstructionsPage() {
  const { id } = useParams<{ id: string }>();
  const authFetch = useAuthFetch();
  const router = useRouter();
  const [data, setData] = useState<{ agent_id: string; instructions: Instruction[] } | null>(null);

  useEffect(() => {
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents/${id}/instructions`, { method: "GET" });
      if (!res.ok) {
        router.replace("/404");
        return;
      }
      setData(await res.json());
    })();
    // authFetch and router are stable hooks; effect only depends on id
     
  }, [id]);

  const host = useMemo(() => (typeof window !== "undefined" ? window.location.host : "<host>"), []);

  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="mb-2 text-2xl font-bold">Instructions Pack</h1>
      <p className="mb-6 text-sm text-muted-foreground">Host inferred as {host}. Replace placeholders as needed.</p>
      <div className="space-y-4">
        {data?.instructions?.map((ins) => (
          <section key={ins.id} className="rounded border bg-card p-4">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold">{ins.label}</h2>
              <button className="text-xs underline" onClick={() => copy(ins.code.replaceAll("<host>", host).replaceAll("<agent-id>", id))}>Copy</button>
            </div>
            <CodeBlock language={ins.language} code={ins.code} />
          </section>
        ))}
      </div>
    </main>
  );
}

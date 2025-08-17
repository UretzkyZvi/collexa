"use client";
import { useEffect, useState } from "react";
import { useAuthFetch } from "~/lib/authFetch";
import { useRouter } from "next/navigation";

export default function InstructionsPage({ params }: { params: { id: string } }) {
  const authFetch = useAuthFetch();
  const router = useRouter();
  const [data, setData] = useState<any | null>(null);

  useEffect(() => {
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents/${params.id}/instructions`, { method: "GET" });
      if (!res.ok) {
        router.replace("/404");
        return;
      }
      setData(await res.json());
    })();
  }, [params.id]);

  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="mb-4 text-2xl font-bold">Instructions Pack</h1>
      <pre className="overflow-auto rounded bg-black/40 p-4 text-sm">{JSON.stringify(data, null, 2)}</pre>
    </main>
  );
}

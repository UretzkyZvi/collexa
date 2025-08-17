"use client";

export default function BillingPage() {
  async function startCheckout() {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/billing/checkout`, { method: "POST" });
    const data = await res.json();
    if (data?.url) window.location.href = data.url;
  }
  return (
    <main className="mx-auto max-w-2xl p-6 space-y-4">
      <h1 className="text-2xl font-bold">Billing</h1>
      <button onClick={startCheckout} className="rounded bg-green-600 px-4 py-2 text-white">Start Checkout</button>
    </main>
  );
}


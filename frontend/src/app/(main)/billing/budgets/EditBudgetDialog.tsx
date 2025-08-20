"use client";

import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "~/components/ui/dialog";
import { Button } from "~/components/ui/button";
import { Label } from "~/components/ui/label";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { useAuthFetch } from "~/lib/authFetch";

export default function EditBudgetDialog({ budget, onUpdated }: { budget: any; onUpdated?: () => void }) {
  const authFetch = useAuthFetch();
  const [open, setOpen] = useState(false);
  const [limit, setLimit] = useState<string>("");
  const [enforcement, setEnforcement] = useState<string>("soft");
  const [alertThreshold, setAlertThreshold] = useState<number>(90);

  useEffect(() => {
    if (budget) {
      setLimit((budget.limit_cents / 100).toFixed(2));
      setEnforcement(budget.enforcement_mode);
      setAlertThreshold(budget.alerts_config?.threshold_percent ?? 90);
    }
  }, [budget]);

  async function onSubmit() {
    const payload: any = {
      limit_cents: Math.round(parseFloat(limit) * 100),
      enforcement_mode: enforcement,
      alerts_config: { threshold_percent: alertThreshold },
    };
    const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/budgets/${budget.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      setOpen(false);
      onUpdated?.();
    } else {
      console.error("Failed to update budget", await res.text());
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">Edit</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Budget</DialogTitle>
          <DialogDescription>Update budget limit, enforcement, and alert thresholds.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Limit (USD)</Label>
            <Input type="number" step="0.01" value={limit} onChange={(e) => setLimit(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Enforcement</Label>
            <Select value={enforcement} onValueChange={setEnforcement}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="soft">Soft (warn)</SelectItem>
                <SelectItem value="hard">Hard (block)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Alert threshold (%)</Label>
            <Input type="number" min={10} max={100} step={5} value={alertThreshold} onChange={(e) => setAlertThreshold(parseInt(e.target.value || "0", 10))} />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={onSubmit}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


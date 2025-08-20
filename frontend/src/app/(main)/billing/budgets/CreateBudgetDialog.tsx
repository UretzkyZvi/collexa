"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "~/components/ui/dialog";
import { Button } from "~/components/ui/button";
import { Label } from "~/components/ui/label";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Plus } from "lucide-react";
import { useAuthFetch } from "~/lib/authFetch";

const schema = z.object({
  agent_id: z.string().optional(),
  period: z.enum(["daily", "weekly", "monthly"]),
  limit_dollars: z.coerce.number().min(0.01, "Budget must be greater than $0"),
  enforcement_mode: z.enum(["soft", "hard"]).default("soft"),
});

export type CreateBudgetValues = z.infer<typeof schema>;

export default function CreateBudgetDialog({ onCreated }: { onCreated?: () => void }) {
  const authFetch = useAuthFetch();
  const [agents, setAgents] = useState<Array<{ id: string; display_name?: string }>>([]);
  const [open, setOpen] = useState(false);
  const {
    register,
    handleSubmit,
    setValue,
    setError,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<CreateBudgetValues>({
    defaultValues: { period: "monthly", enforcement_mode: "soft" },
  });

  useEffect(() => {
    (async () => {
      const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/agents`, { method: "GET" });
      if (res.ok) setAgents(await res.json());
    })();
  }, [authFetch]);

  async function onSubmit(values: CreateBudgetValues) {
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      parsed.error.issues.forEach((issue) => {
        const path = issue.path?.[0] as keyof CreateBudgetValues | undefined;
        if (path) {
          setError(path as any, { type: "validate", message: issue.message });
        }
      });
      return;
    }
    const payload = {
      agent_id: values.agent_id || null,
      period: values.period,
      limit_cents: Math.round(values.limit_dollars * 100),
      enforcement_mode: values.enforcement_mode,
      alerts_config: null,
    };
    const res = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/budgets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      setOpen(false);
      reset();
      onCreated?.();
    } else {
      // TODO: show toast
      console.error("Failed to create budget", await res.text());
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Budget
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>Create Budget</DialogTitle>
          <DialogDescription>Define a budget for your organization or a specific agent.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            <div className="space-y-2">
              <Label>Scope</Label>
              <Select onValueChange={(v) => setValue("agent_id", v === "org" ? undefined : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Organization-wide" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="org">Organization-wide</SelectItem>
                  {agents.map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      {a.display_name || a.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.agent_id && (
                <p className="text-sm text-destructive">{errors.agent_id.message?.toString()}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Period</Label>
              <Select defaultValue="monthly" onValueChange={(v) => setValue("period", v as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
              {errors.period && (
                <p className="text-sm text-destructive">{errors.period.message?.toString()}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Limit (USD)</Label>
              <Input type="number" step="0.01" placeholder="100.00" {...register("limit_dollars")} />
              {errors.limit_dollars && (
                <p className="text-sm text-destructive">{errors.limit_dollars.message?.toString()}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Enforcement</Label>
              <Select defaultValue="soft" onValueChange={(v) => setValue("enforcement_mode", v as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="soft">Soft (warn)</SelectItem>
                  <SelectItem value="hard">Hard (block)</SelectItem>
                </SelectContent>
              </Select>
              {errors.enforcement_mode && (
                <p className="text-sm text-destructive">{errors.enforcement_mode.message?.toString()}</p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}


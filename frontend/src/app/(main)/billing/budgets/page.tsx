"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Progress } from "~/components/ui/progress";
import { /* Select, */ SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { useAuthFetch } from "~/lib/authFetch";
import CreateBudgetDialog from "./CreateBudgetDialog";
import { DollarSign, AlertTriangle, CheckCircle } from "lucide-react";
import EditBudgetDialog from "./EditBudgetDialog";

interface Budget {
  id: string;
  org_id: string;
  agent_id?: string;
  period: string;
  limit_cents: number;
  current_usage_cents: number;
  utilization_percent: number;
  period_start: string;
  period_end: string;
  enforcement_mode: string;
  status: string;
  alerts_config: any;
  created_at: string;
  updated_at?: string;
}

interface UsageSummary {
  total_cost_cents: number;
  total_cost_dollars: number;
  usage_by_type: Record<string, any>;
  record_count: number;
}

export default function BudgetsPage() {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [usageSummary, setUsageSummary] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBudgets();
    fetchUsageSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const authFetch = useAuthFetch();

  const fetchBudgets = async () => {
    try {
      const response = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/budgets`, { method: "GET" });
      if (!response.ok) throw new Error('Failed to fetch budgets');
      const data = await response.json();
      setBudgets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch budgets');
    }
  };

  const fetchUsageSummary = async () => {
    try {
      const response = await authFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/usage/summary`, { method: "GET" });
      if (!response.ok) throw new Error('Failed to fetch usage summary');
      const data = await response.json();
      setUsageSummary(data);
    } catch (err) {
      console.error('Failed to fetch usage summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(cents / 100);
  };

  const getStatusColor = (status: string, utilizationPercent: number) => {
    if (status === 'exceeded') return 'destructive';
    if (utilizationPercent >= 90) return 'destructive';
    if (utilizationPercent >= 75) return 'secondary';
    return 'default';
  };

  const getStatusIcon = (status: string, utilizationPercent: number) => {
    if (status === 'exceeded') return <AlertTriangle className="h-4 w-4" />;
    if (utilizationPercent >= 90) return <AlertTriangle className="h-4 w-4" />;
    return <CheckCircle className="h-4 w-4" />;
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-2 text-sm text-gray-600">Loading budgets...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Budget Management</h1>
          <p className="text-gray-600">Monitor and control your spending across agents and services</p>
        </div>
        <CreateBudgetDialog onCreated={() => { fetchBudgets(); fetchUsageSummary(); }} />
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-800">
              <AlertTriangle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Usage Summary */}
      {usageSummary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <DollarSign className="h-5 w-5" />
              <span>Current Month Usage</span>
            </CardTitle>
            <CardDescription>
              Your usage and spending for the current billing period
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {formatCurrency(usageSummary.total_cost_cents)}
                </div>
                <div className="text-sm text-gray-600">Total Spent</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {usageSummary.record_count}
                </div>
                <div className="text-sm text-gray-600">Usage Records</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {Object.keys(usageSummary.usage_by_type).length}
                </div>
                <div className="text-sm text-gray-600">Usage Types</div>
              </div>
            </div>

            {/* Usage by Type */}
            <div className="mt-4 space-y-2">
              <h4 className="font-medium">Usage Breakdown</h4>
              {Object.entries(usageSummary.usage_by_type).map(([type, data]: [string, any]) => (
                <div key={type} className="flex justify-between items-center py-2 border-b">
                  <span className="capitalize">{type.replace('_', ' ')}</span>
                  <div className="text-right">
                    <div className="font-medium">{formatCurrency(data.cost_cents)}</div>
                    <div className="text-sm text-gray-600">{data.quantity} units</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Budgets List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {budgets.map((budget) => (
          <Card key={budget.id} className="relative">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">
                  {budget.agent_id ? `Agent Budget` : 'Organization Budget'}
                </CardTitle>
                <Badge variant={getStatusColor(budget.status, budget.utilization_percent)}>
                  {getStatusIcon(budget.status, budget.utilization_percent)}
                  <span className="ml-1 capitalize">{budget.status}</span>
                </Badge>
              </div>
              <CardDescription>
                {budget.period} • {budget.enforcement_mode} enforcement
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Budget Progress */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Usage</span>
                  <span>{budget.utilization_percent.toFixed(1)}%</span>
                </div>
                <Progress 
                  value={Math.min(budget.utilization_percent, 100)} 
                  className="h-2"
                />
                <div className="flex justify-between text-sm mt-1 text-gray-600">
                  <span>{formatCurrency(budget.current_usage_cents)}</span>
                  <span>{formatCurrency(budget.limit_cents)}</span>
                </div>
              </div>

              {/* Budget Details */}
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Period:</span>
                  <span className="capitalize">{budget.period}</span>
                </div>
                <div className="flex justify-between">
                  <span>Enforcement:</span>
                  <span className="capitalize">{budget.enforcement_mode}</span>
                </div>
                <div className="flex justify-between">
                  <span>Period End:</span>
                  <span>{new Date(budget.period_end).toLocaleDateString()}</span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex space-x-2 pt-2">
                <EditBudgetDialog budget={budget} onUpdated={() => { fetchBudgets(); fetchUsageSummary(); }} />
                <Button variant="outline" size="sm" className="flex-1">
                  View Details
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {budgets.length === 0 && !loading && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <DollarSign className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No budgets configured</h3>
              <p className="text-gray-600 mb-4">
                Create your first budget to start monitoring and controlling your spending.
              </p>
              <CreateBudgetDialog onCreated={() => { fetchBudgets(); fetchUsageSummary(); }} />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

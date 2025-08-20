"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { CreditCard, DollarSign, Settings, TrendingUp, AlertCircle } from "lucide-react";

interface Subscription {
  subscription_id: string;
  status: string;
  plan_id: string;
  current_period_start?: string;
  current_period_end?: string;
  provider: string;
}

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSubscriptionStatus();
  }, []);

  const fetchSubscriptionStatus = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/billing/subscription`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status !== 'no_subscription') {
          setSubscription(data);
        }
      }
    } catch (err) {
      console.error('Failed to fetch subscription status:', err);
    } finally {
      setLoading(false);
    }
  };

  const startCheckout = async () => {
    try {
      setError(null);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/billing/checkout`, {
        method: "POST",
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify({
          plan_id: "price_monthly_pro", // Default plan
          success_url: `${window.location.origin}/billing/success`,
          cancel_url: `${window.location.origin}/billing`
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create checkout session');
      }

      const data = await response.json();
      if (data?.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start checkout');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'default';
      case 'trialing': return 'secondary';
      case 'past_due': return 'destructive';
      case 'canceled': return 'outline';
      default: return 'outline';
    }
  };

  return (
    <main className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Billing & Subscription</h1>
          <p className="text-gray-600">Manage your subscription, billing, and usage</p>
        </div>
        {!subscription && (
          <Button onClick={startCheckout} disabled={loading}>
            <CreditCard className="h-4 w-4 mr-2" />
            Subscribe Now
          </Button>
        )}
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-800">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Subscription Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <CreditCard className="h-5 w-5" />
            <span>Subscription Status</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
              <span>Loading subscription status...</span>
            </div>
          ) : subscription ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <Badge variant={getStatusColor(subscription.status)}>
                      {subscription.status.replace('_', ' ').toUpperCase()}
                    </Badge>
                    <span className="text-sm text-gray-600">
                      Plan: {subscription.plan_id}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    Provider: {subscription.provider}
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  <Settings className="h-4 w-4 mr-2" />
                  Manage
                </Button>
              </div>

              {subscription.current_period_end && (
                <div className="text-sm text-gray-600">
                  Current period ends: {new Date(subscription.current_period_end).toLocaleDateString()}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-gray-600 mb-4">No active subscription</p>
              <Button onClick={startCheckout}>
                <CreditCard className="h-4 w-4 mr-2" />
                Start Subscription
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="hover:shadow-md transition-shadow cursor-pointer">
          <Link href="/billing/budgets">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-lg">
                <DollarSign className="h-5 w-5" />
                <span>Budget Management</span>
              </CardTitle>
              <CardDescription>
                Set spending limits and monitor usage across agents
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:shadow-md transition-shadow cursor-pointer">
          <Link href="/billing/usage">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-lg">
                <TrendingUp className="h-5 w-5" />
                <span>Usage Analytics</span>
              </CardTitle>
              <CardDescription>
                View detailed usage reports and trends
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:shadow-md transition-shadow cursor-pointer">
          <Link href="/billing/invoices">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-lg">
                <CreditCard className="h-5 w-5" />
                <span>Invoices & Payments</span>
              </CardTitle>
              <CardDescription>
                Access your billing history and invoices
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>
      </div>
    </main>
  );
}


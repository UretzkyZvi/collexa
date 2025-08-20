"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Button } from "~/components/ui/button";

export default function OrgSettingsPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl space-y-6">
      <h1 className="text-3xl font-bold">Organization Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Domain Settings</CardTitle>
          <CardDescription>Configure your organization domain and branding (placeholder)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Coming soon. This section will allow configuring custom domains and branding once backend support lands.</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>SSO Providers</CardTitle>
          <CardDescription>Connect identity providers (placeholder)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between border rounded p-3">
            <div>
              <div className="font-medium">SAML</div>
              <div className="text-xs text-muted-foreground">Configure SAML SSO for your org</div>
            </div>
            <Button variant="outline" size="sm">Configure</Button>
          </div>
          <div className="flex items-center justify-between border rounded p-3">
            <div>
              <div className="font-medium">OIDC</div>
              <div className="text-xs text-muted-foreground">Configure OIDC (Auth0/Okta)</div>
            </div>
            <Button variant="outline" size="sm">Configure</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Policy Attachments</CardTitle>
          <CardDescription>View policies attached to your org (read-only placeholder)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Pending Milestone J. Will display OPA policy bundles attached to this org.</div>
        </CardContent>
      </Card>
    </div>
  );
}


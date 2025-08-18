"use client";

import { useState, useEffect } from "react";
import { useAuthFetch } from "@/hooks/useAuthFetch";

interface ApiKey {
  key_id: string;
  name?: string;
  created_at: string;
}

interface Agent {
  id: string;
  display_name: string;
}

export default function SettingsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [keyName, setKeyName] = useState("");
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const authFetch = useAuthFetch();

  useEffect(() => {
    loadAgents();
  }, []);

  useEffect(() => {
    if (selectedAgent) {
      loadApiKeys();
    }
  }, [selectedAgent]);

  const loadAgents = async () => {
    try {
      const response = await authFetch("/v1/agents");
      if (response.ok) {
        const data = await response.json();
        setAgents(data);
        if (data.length > 0) {
          setSelectedAgent(data[0].id);
        }
      }
    } catch (error) {
      console.error("Failed to load agents:", error);
    }
  };

  const loadApiKeys = async () => {
    if (!selectedAgent) return;
    
    try {
      // Note: This endpoint doesn't exist yet, but would list keys for an agent
      // For now, we'll show a placeholder
      setApiKeys([]);
    } catch (error) {
      console.error("Failed to load API keys:", error);
    }
  };

  const createApiKey = async () => {
    if (!selectedAgent || !keyName.trim()) return;
    
    setLoading(true);
    try {
      const response = await authFetch(`/v1/agents/${selectedAgent}/keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: keyName.trim() }),
      });

      if (response.ok) {
        const data = await response.json();
        setNewApiKey(data.api_key);
        setKeyName("");
        loadApiKeys(); // Refresh the list
      } else {
        alert("Failed to create API key");
      }
    } catch (error) {
      console.error("Failed to create API key:", error);
      alert("Failed to create API key");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-8">Settings</h1>

      {/* API Keys Section */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">API Keys</h2>
        <p className="text-gray-600 mb-6">
          Create API keys to access your agents programmatically from external tools like n8n, Make.com, or custom applications.
        </p>

        {/* Agent Selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Agent
          </label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select an agent...</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.display_name}
              </option>
            ))}
          </select>
        </div>

        {/* Create New Key */}
        {selectedAgent && (
          <div className="mb-6">
            <div className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Key Name (optional)
                </label>
                <input
                  type="text"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  placeholder="e.g., Production Key, n8n Integration"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={createApiKey}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Creating..." : "Create Key"}
              </button>
            </div>
          </div>
        )}

        {/* New API Key Display */}
        {newApiKey && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
            <h3 className="font-medium text-yellow-800 mb-2">
              ⚠️ New API Key Created
            </h3>
            <p className="text-sm text-yellow-700 mb-3">
              Copy this key now - it won't be shown again for security reasons.
            </p>
            <div className="flex gap-2">
              <code className="flex-1 px-3 py-2 bg-white border rounded text-sm font-mono">
                {newApiKey}
              </code>
              <button
                onClick={() => copyToClipboard(newApiKey)}
                className="px-3 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 text-sm"
              >
                Copy
              </button>
            </div>
            <button
              onClick={() => setNewApiKey(null)}
              className="mt-2 text-sm text-yellow-600 hover:text-yellow-800"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Existing Keys List */}
        {selectedAgent && (
          <div>
            <h3 className="font-medium mb-3">Existing Keys</h3>
            {apiKeys.length === 0 ? (
              <p className="text-gray-500 text-sm">
                No API keys created yet. Create one above to get started.
              </p>
            ) : (
              <div className="space-y-2">
                {apiKeys.map((key) => (
                  <div
                    key={key.key_id}
                    className="flex items-center justify-between p-3 border rounded-md"
                  >
                    <div>
                      <div className="font-medium">
                        {key.name || "Unnamed Key"}
                      </div>
                      <div className="text-sm text-gray-500">
                        Created: {new Date(key.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <button className="text-red-600 hover:text-red-800 text-sm">
                      Revoke
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Usage Instructions */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Using API Keys</h2>
        <div className="space-y-4 text-sm">
          <div>
            <h3 className="font-medium mb-2">HTTP Requests</h3>
            <pre className="bg-white p-3 rounded border text-xs overflow-x-auto">
{`curl -X POST https://api.yourdomain.com/v1/agents/{agent_id}/invoke \\
  -H "X-API-Key: your-api-key-here" \\
  -H "Content-Type: application/json" \\
  -d '{"capability": "example", "input": {"key": "value"}}'`}
            </pre>
          </div>
          <div>
            <h3 className="font-medium mb-2">n8n Integration</h3>
            <p className="text-gray-600">
              Use the HTTP Request node with the X-API-Key header. Visit the Instructions page for your agent to get pre-configured snippets.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

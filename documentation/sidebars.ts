import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  // Getting Started sidebar
  gettingStartedSidebar: [
    'getting-started/introduction',
    'getting-started/quick-start',
    'getting-started/installation',
    'getting-started/first-agent',
    'getting-started/concepts',
  ],

  // User Guide sidebar
  userGuideSidebar: [
    'user-guide/dashboard',
    'user-guide/agents',
    'user-guide/api-keys',
    'user-guide/monitoring',
    'user-guide/logs',
  ],

  // Integrations sidebar
  integrationsSidebar: [
    'integrations/overview',
    'integrations/n8n',
    'integrations/make-com',
    'integrations/langchain',
    'integrations/openai',
    'integrations/mcp-clients',
    'integrations/custom-api',
  ],

  // API Reference sidebar
  apiSidebar: [
    'api/overview',
    'api/authentication',
    'api/agents',
    'api/invocations',
    'api/logs',
    'api/metrics',
    'api/webhooks',
    'api/errors',
  ],

  // Architecture sidebar
  architectureSidebar: [
    'architecture/overview',
    'architecture/security',
    'architecture/database',
    'architecture/observability',
  ],

  // Deployment sidebar
  deploymentSidebar: [
    'deployment/overview',
    'deployment/docker',
    'deployment/environment',
    'deployment/production',
    'deployment/monitoring',
  ],
};

export default sidebars;

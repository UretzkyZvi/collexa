# Dashboard Overview

The Collexa dashboard is your central hub for monitoring agents, tracking performance, and managing your AI automation platform.

## Dashboard Layout

### Navigation Sidebar

- **Dashboard**: Overview and quick actions
- **Agents**: Create and manage your AI agents
- **Playground**: Test agents interactively
- **Logs**: View execution history and debugging
- **Settings**: API keys and account management

### Main Dashboard

The dashboard provides real-time insights into your platform usage and performance.

## Key Metrics Cards

### 1. Total Agents
- **Purpose**: Shows the number of agents in your organization
- **Actions**: Click to navigate to the Agents page
- **Empty State**: Displays "Create your first agent" when no agents exist

### 2. API Calls Total
- **Real-time Data**: Updates automatically as you make API calls
- **Error Tracking**: Shows total errors below the main count
- **Calculation**: Includes all API endpoints (invoke, logs, metrics, etc.)

### 3. Success Rate
- **Formula**: `(Total Calls - Errors) / Total Calls * 100`
- **Display**: Percentage with one decimal place
- **Color Coding**: Green for greater than 95%, yellow for 90-95%, red for less than 90%

## Performance Metrics Section

*Appears only when you have API call data*

### Request Performance Card

Shows API response time statistics:

- **Average**: Mean response time across all requests
- **P50 (Median)**: 50% of requests complete faster than this time
- **P95**: 95% of requests complete faster than this time
- **P99**: 99% of requests complete faster than this time
- **Total Requests**: Number of requests measured

**Understanding Percentiles:**
- P50 shows typical performance
- P95 shows performance under load
- P99 helps identify outliers and worst-case scenarios

### Agent Invocations Card

Tracks agent execution performance:

- **Total Invocations**: Number of times agents have been called
- **Average Duration**: Mean execution time for agent processing
- **P95 Duration**: 95th percentile execution time

## Quick Actions Section

### Create Agent
- **Purpose**: Start building a new AI agent
- **Icon**: 🤖
- **Destination**: `/agents/new`

### Test Playground
- **Purpose**: Interactive agent testing environment
- **Icon**: 🎮
- **Destination**: `/playground`

### Manage API Keys
- **Purpose**: Create and manage authentication keys
- **Icon**: 🔑
- **Destination**: `/settings`

### View Logs
- **Purpose**: Monitor execution history and debug issues
- **Icon**: 📊
- **Destination**: `/execution-logs`

## Welcome Flow (New Users)

### First-Time Experience

When you have no agents, the dashboard shows:

1. **Welcome Message**: "Welcome to Collexa! 🎉"
2. **Platform Description**: Brief explanation of capabilities
3. **Primary CTA**: "Create Your First Agent"
4. **Secondary CTA**: "Try the Playground"

### Onboarding Tips

- Start with the playground to understand agent interaction
- Create a simple agent with a clear purpose
- Test thoroughly before integrating with external tools
- Monitor performance metrics as you scale

## Real-Time Updates

### Automatic Refresh

The dashboard automatically updates:
- **Metrics**: Refresh every 30 seconds
- **Agent Count**: Updates immediately when agents are created/deleted
- **Performance Data**: Updates after each API call

### Manual Refresh

- **Browser Refresh**: Reloads all data
- **Navigation**: Returning to dashboard fetches latest data

## Understanding Your Data

### Metrics Calculation

**API Calls**: Includes all endpoints:
- Agent invocations (`/v1/agents/{id}/invoke`)
- Log retrievals (`/v1/runs`, `/v1/runs/{id}/logs`)
- Metrics queries (`/v1/metrics`)
- Agent management (`/v1/agents`)

**Success Rate**: Based on HTTP status codes:
- **Success**: 200-299 status codes
- **Error**: 400+ status codes
- **Calculation**: Real-time, not cached

### Performance Interpretation

**Good Performance Indicators:**
- P95 latency < 2000ms for agent invocations
- P95 latency < 500ms for API calls
- Success rate > 99%
- Consistent response times

**Performance Concerns:**
- P95 latency > 5000ms
- Success rate < 95%
- Large gaps between P50 and P95 (inconsistent performance)

## Troubleshooting

### No Metrics Showing

**Cause**: No API calls have been made yet
**Solution**: 
1. Create an agent
2. Make at least one API call via playground or API
3. Return to dashboard to see metrics

### Metrics Not Updating

**Cause**: Browser caching or connection issues
**Solution**:
1. Refresh the browser page
2. Check network connection
3. Verify you're logged in to the correct organization

### Performance Seems Slow

**Investigation Steps**:
1. Check the Logs page for error patterns
2. Review P95/P99 latency for outliers
3. Monitor during different times of day
4. Consider agent complexity and input size

## Best Practices

### Monitoring Strategy

1. **Daily Check**: Review success rate and error count
2. **Weekly Analysis**: Examine latency trends and usage patterns
3. **Monthly Review**: Assess agent performance and optimization opportunities

### Performance Optimization

1. **Monitor Trends**: Watch for degrading performance over time
2. **Optimize Inputs**: Reduce unnecessary data in agent requests
3. **Error Analysis**: Address recurring error patterns
4. **Capacity Planning**: Scale based on usage growth

---

**Next**: [Agent Management →](./agents.md)

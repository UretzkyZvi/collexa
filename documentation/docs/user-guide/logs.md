# Logs & Debugging

Learn how to use Collexa's comprehensive logging system to monitor agent executions, debug issues, and optimize performance.

## Logs Overview

### What are Logs?

Logs in Collexa provide detailed records of:
- **Agent Invocations**: Every time an agent is called
- **Execution Steps**: Internal processing details
- **API Requests**: All interactions with your agents
- **System Events**: Platform operations and status changes

### Log Structure

Each log entry contains:
- **Timestamp**: When the event occurred
- **Level**: Severity (info, warning, error)
- **Message**: Human-readable description
- **Context**: Request ID, organization, agent, user
- **Metadata**: Additional structured data

## Accessing Logs

### Via Dashboard

1. **Navigate to Logs**
   - Click "Logs" in the sidebar
   - View recent executions and events

2. **Log Filters**
   - **Agent**: Filter by specific agent
   - **Status**: Success, error, or running
   - **Time Range**: Last hour, day, week, or custom
   - **Log Level**: Info, warning, error

### Via API

```bash
# Get recent logs
curl -X GET "http://localhost:8000/v1/runs?limit=50" \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id"

# Get logs for specific run
curl -X GET "http://localhost:8000/v1/runs/run_abc123/logs" \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id"
```

## Understanding Log Entries

### Run Records

Each agent invocation creates a **Run** with:

```json
{
  "run_id": "run_abc123",
  "agent_id": "agent_def456",
  "org_id": "org_ghi789",
  "status": "succeeded",
  "input": {
    "capability": "help",
    "input": {
      "question": "How do I reset my password?"
    }
  },
  "output": {
    "result": "To reset your password, follow these steps..."
  },
  "created_at": "2025-01-18T10:00:00Z",
  "completed_at": "2025-01-18T10:00:02Z",
  "duration_ms": 2150
}
```

### Log Messages

Individual log entries within a run:

```json
{
  "timestamp": "2025-01-18T10:00:01Z",
  "level": "info",
  "message": "Processing capability: help",
  "request_id": "req_xyz789",
  "org_id": "org_ghi789",
  "agent_id": "agent_def456",
  "run_id": "run_abc123"
}
```

## Log Levels

### Info Level
- Normal operation events
- Successful completions
- Processing milestones
- Performance metrics

**Example:**
```
INFO: Agent invocation started - capability: help
INFO: Processing user question about password reset
INFO: Agent invocation completed successfully in 2.1s
```

### Warning Level
- Unusual but handled conditions
- Performance concerns
- Deprecated feature usage
- Retry attempts

**Example:**
```
WARN: Request took longer than expected (5.2s)
WARN: Large input payload detected (>10KB)
WARN: Rate limit approaching for organization
```

### Error Level
- Failed operations
- System errors
- Invalid requests
- Timeout conditions

**Example:**
```
ERROR: Agent invocation failed - invalid capability: unknown
ERROR: Database connection timeout during request processing
ERROR: Authentication failed - invalid API key
```

## Debugging Common Issues

### Agent Not Responding

**Symptoms:**
- Requests timeout
- No response from agent
- Status stuck in "running"

**Investigation Steps:**
1. Check recent error logs for the agent
2. Verify API key is valid and not revoked
3. Test with echo capability
4. Check system status and connectivity

**Log Analysis:**
```bash
# Check for errors in recent runs
curl -X GET "http://localhost:8000/v1/runs?agent_id=agent_abc123&status=error&limit=10" \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id"
```

### Authentication Failures

**Symptoms:**
- 401 Unauthorized responses
- "Invalid API key" errors
- Authentication-related log entries

**Investigation Steps:**
1. Verify API key format and completeness
2. Check if key has been revoked
3. Confirm agent and organization match
4. Test with a known working key

**Log Patterns:**
```
ERROR: Authentication failed - API key not found
ERROR: API key revoked or expired
ERROR: Agent access denied for organization
```

### Performance Issues

**Symptoms:**
- Slow response times
- Timeout errors
- High latency warnings

**Investigation Steps:**
1. Review execution duration in logs
2. Check for resource-intensive operations
3. Analyze input payload size
4. Monitor system load patterns

**Log Analysis:**
```bash
# Find slow requests (>5 seconds)
curl -X GET "http://localhost:8000/v1/runs" \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id" | \
  jq '.[] | select(.duration_ms > 5000)'
```

## Real-Time Log Monitoring

### Live Log Streaming

Monitor logs in real-time during development:

```bash
# Stream logs for specific agent
curl -N -H "Authorization: Bearer your-token" \
     -H "X-Team-Id: your-org-id" \
     "http://localhost:8000/v1/agents/agent_abc123/logs/stream"
```

### Playground Integration

The Playground provides real-time log viewing:
1. Select your agent
2. Enter test input
3. Click "Invoke"
4. Watch logs appear in real-time
5. See final result and execution summary

## Log Retention and Management

### Retention Policy

- **Standard Logs**: Retained for 30 days
- **Error Logs**: Retained for 90 days
- **Audit Logs**: Retained for 1 year
- **Metrics Data**: Retained for 6 months

### Log Export

Export logs for external analysis:

```bash
# Export logs to JSON
curl -X GET "http://localhost:8000/v1/runs?limit=1000&format=json" \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id" > logs_export.json

# Export specific time range
curl -X GET "http://localhost:8000/v1/runs?start_date=2025-01-01&end_date=2025-01-31" \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id"
```

## Advanced Debugging

### Correlation IDs

Every request gets a unique correlation ID for tracking:
- **Request ID**: Tracks the API request
- **Run ID**: Tracks the agent execution
- **Trace ID**: Tracks distributed operations

**Finding Related Logs:**
```bash
# Find all logs for a specific request
curl -X GET "http://localhost:8000/v1/runs/run_abc123/logs" \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id"
```

### Error Context

Error logs include additional context:
- **Stack Traces**: For system errors
- **Input Data**: What caused the error
- **System State**: Resource usage, connections
- **Retry Information**: Previous attempts

### Performance Profiling

Detailed timing information:
- **Request Processing**: Authentication, validation
- **Agent Execution**: Core processing time
- **Database Operations**: Query performance
- **External Calls**: Third-party service latency

## Log Analysis Best Practices

### Regular Monitoring

1. **Daily Review**: Check error logs and performance warnings
2. **Weekly Analysis**: Look for patterns and trends
3. **Monthly Audit**: Review retention and cleanup needs
4. **Incident Response**: Investigate alerts promptly

### Pattern Recognition

**Common Patterns to Watch:**
- Repeated errors from same source
- Performance degradation over time
- Authentication failure spikes
- Unusual usage patterns

### Automated Analysis

**Log Processing Scripts:**
```bash
#!/bin/bash
# Daily error summary
curl -s -H "Authorization: Bearer $TOKEN" \
     -H "X-Team-Id: $ORG_ID" \
     "http://localhost:8000/v1/runs?status=error&limit=100" | \
jq -r '.[] | "\(.created_at) \(.agent_id) \(.error_message)"' | \
sort | uniq -c | sort -nr
```

### Integration with Monitoring Tools

**Splunk Integration:**
```bash
# Forward logs to Splunk
curl -X GET "http://localhost:8000/v1/runs?format=json" \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id" | \
curl -X POST "https://splunk.company.com/services/collector" \
  -H "Authorization: Splunk $SPLUNK_TOKEN" \
  -d @-
```

**ELK Stack Integration:**
```json
{
  "logstash": {
    "input": {
      "http_poller": {
        "urls": {
          "collexa_logs": "http://localhost:8000/v1/runs"
        },
        "headers": {
          "Authorization": "Bearer your-token",
          "X-Team-Id": "your-org-id"
        },
        "schedule": { "every": "1m" }
      }
    }
  }
}
```

## Troubleshooting Checklist

### Before Investigating

1. **Reproduce the Issue**: Can you recreate the problem?
2. **Check Recent Changes**: Any recent deployments or configuration changes?
3. **Verify Scope**: Is it affecting one agent or multiple?
4. **Check System Status**: Are there any known outages?

### Investigation Steps

1. **Review Error Logs**: Look for recent errors and patterns
2. **Check Performance Metrics**: Identify latency or throughput issues
3. **Analyze Request Patterns**: Look for unusual usage or load
4. **Verify Configuration**: Confirm settings and permissions
5. **Test Isolation**: Try with different agents or capabilities

### Resolution Documentation

1. **Record Findings**: Document what you discovered
2. **Note Solutions**: Record what fixed the issue
3. **Update Monitoring**: Add alerts to catch similar issues
4. **Share Knowledge**: Update team documentation

---

**Next**: [Integration Guides →](../integrations/overview.md)

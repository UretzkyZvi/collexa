# Monitoring & Analytics

Monitor your agents' performance, track usage patterns, and optimize your AI automation with Collexa's comprehensive observability features.

## Metrics Overview

### Real-Time Dashboard

The dashboard provides live metrics that update automatically:
- **API Call Volume**: Total requests and current rate
- **Success Rate**: Percentage of successful operations
- **Response Latency**: Performance metrics with percentiles
- **Agent Activity**: Invocation counts and execution times

### Metrics Endpoint

Access detailed metrics programmatically:

```bash
curl -X GET http://localhost:8000/v1/metrics \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id"
```

**Response:**
```json
{
  "org_id": "org_abc123",
  "api_calls": {
    "total": 1250,
    "errors": 15,
    "success_rate": 0.988
  },
  "request_duration_ms": {
    "count": 1250,
    "p50": 145.2,
    "p95": 890.5,
    "p99": 2100.8,
    "avg": 234.7
  },
  "agent_invocations": {
    "total": 450,
    "duration_ms": {
      "count": 450,
      "p50": 1200.0,
      "p95": 3500.0,
      "p99": 8000.0,
      "avg": 1650.5
    }
  }
}
```

## Understanding Metrics

### API Call Metrics

**Total Calls**: All API requests to your organization
- Agent invocations
- Log retrievals
- Metrics queries
- Agent management operations

**Success Rate**: Calculated as `(Total - Errors) / Total`
- **Excellent**: Greater than 99%
- **Good**: 95-99%
- **Needs Attention**: Less than 95%

**Error Count**: Failed requests (4xx and 5xx status codes)
- Authentication failures
- Invalid requests
- Server errors
- Rate limit exceeded

### Performance Metrics

**Percentile Explanation:**
- **P50 (Median)**: Half of requests complete faster than this time
- **P95**: 95% of requests complete faster than this time
- **P99**: 99% of requests complete faster than this time

**Interpreting Latency:**
- **P50**: Typical user experience
- **P95**: Performance under normal load
- **P99**: Worst-case scenarios and outliers

### Agent Performance

**Invocation Metrics:**
- **Total Invocations**: Number of agent executions
- **Average Duration**: Mean processing time
- **Success Rate**: Percentage of successful invocations

**Performance Benchmarks:**
- **Fast**: Less than 1 second average
- **Good**: 1-3 seconds average
- **Acceptable**: 3-5 seconds average
- **Slow**: Greater than 5 seconds average

## Performance Analysis

### Identifying Issues

**High Latency Indicators:**
- P95 greater than 2x P50 (inconsistent performance)
- P99 greater than 5x P50 (significant outliers)
- Increasing trend over time

**Error Pattern Analysis:**
- Sudden spikes in error rate
- Consistent error types
- Time-based error patterns

### Performance Optimization

**Request Optimization:**
1. **Reduce Input Size**: Minimize unnecessary data
2. **Batch Operations**: Group multiple requests when possible
3. **Cache Results**: Store frequently requested data
4. **Optimize Timing**: Avoid peak usage periods

**Agent Optimization:**
1. **Simplify Logic**: Reduce complexity where possible
2. **Input Validation**: Catch errors early
3. **Resource Management**: Monitor memory and CPU usage
4. **Capability Design**: Focus on specific, well-defined tasks

## Monitoring Strategies

### Daily Monitoring

**Key Metrics to Check:**
- Overall success rate
- Error count and types
- Average response time
- Agent invocation volume

**Quick Health Check:**
```bash
# Get current metrics
curl -X GET http://localhost:8000/v1/metrics \
  -H "Authorization: Bearer your-token" \
  -H "X-Team-Id: your-org-id" | jq '.api_calls.success_rate'
```

### Weekly Analysis

**Trend Analysis:**
- Compare metrics week-over-week
- Identify usage patterns
- Spot performance degradation
- Plan capacity needs

**Performance Review:**
- Analyze P95/P99 latency trends
- Review error patterns
- Assess agent efficiency
- Optimize based on usage data

### Monthly Reporting

**Business Metrics:**
- Total API calls and growth rate
- Agent utilization and adoption
- Cost per invocation
- User satisfaction indicators

**Technical Metrics:**
- System reliability (uptime, success rate)
- Performance trends
- Error analysis and resolution
- Capacity planning data

## Alerting and Notifications

### Setting Up Monitoring

**Key Thresholds to Monitor:**
- Success rate drops below 95%
- P95 latency exceeds 5 seconds
- Error rate increases by 50%
- API call volume drops significantly

**Monitoring Tools Integration:**
```bash
# Example: Check success rate in monitoring script
SUCCESS_RATE=$(curl -s -H "Authorization: Bearer $TOKEN" \
  -H "X-Team-Id: $ORG_ID" \
  http://localhost:8000/v1/metrics | jq -r '.api_calls.success_rate')

if (( $(echo "$SUCCESS_RATE < 0.95" | bc -l) )); then
  echo "ALERT: Success rate below 95%: $SUCCESS_RATE"
  # Send notification
fi
```

### Custom Dashboards

**Grafana Integration Example:**
```json
{
  "dashboard": {
    "title": "Collexa Metrics",
    "panels": [
      {
        "title": "API Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "collexa_api_success_rate",
            "legendFormat": "Success Rate"
          }
        ]
      },
      {
        "title": "Request Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "collexa_request_duration_p95",
            "legendFormat": "P95"
          }
        ]
      }
    ]
  }
}
```

## Troubleshooting Performance Issues

### High Latency

**Investigation Steps:**
1. Check the Logs page for slow requests
2. Analyze P95/P99 vs P50 gap
3. Review agent complexity and input size
4. Monitor during different time periods

**Common Causes:**
- Large input payloads
- Complex agent logic
- Network connectivity issues
- Database performance problems

### High Error Rate

**Investigation Steps:**
1. Review error logs for patterns
2. Check authentication and API key validity
3. Analyze request formats and validation
4. Monitor external dependencies

**Common Causes:**
- Invalid API keys or authentication
- Malformed requests
- Rate limiting
- Service dependencies

### Inconsistent Performance

**Investigation Steps:**
1. Compare performance across different times
2. Analyze request patterns and load
3. Check for resource contention
4. Review system capacity

**Common Causes:**
- Variable load patterns
- Resource constraints
- Network issues
- Concurrent request handling

## Best Practices

### Monitoring Setup

1. **Baseline Establishment**: Record normal performance metrics
2. **Threshold Setting**: Define acceptable performance ranges
3. **Alert Configuration**: Set up notifications for critical issues
4. **Regular Review**: Schedule periodic performance analysis

### Performance Optimization

1. **Continuous Monitoring**: Track metrics consistently
2. **Proactive Analysis**: Identify trends before they become problems
3. **Optimization Cycles**: Regular performance improvement efforts
4. **Capacity Planning**: Scale resources based on usage growth

### Data-Driven Decisions

1. **Metric-Based Optimization**: Use data to guide improvements
2. **A/B Testing**: Compare different approaches
3. **User Feedback**: Correlate metrics with user experience
4. **Business Impact**: Connect performance to business outcomes

---

**Next**: [Logs & Debugging →](./logs.md)

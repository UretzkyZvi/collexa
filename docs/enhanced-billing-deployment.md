# Enhanced Billing System Deployment Guide

## Overview

This guide covers deploying the enhanced billing system with Phase 2 libraries including Celery, APScheduler, and Apprise for production-ready reliability and automation.

## Prerequisites

### Required Services
- **PostgreSQL** - Main database
- **Redis** - Celery broker and result backend
- **SMTP Server** - Email notifications (optional)

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/collexa

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Payment Provider
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email Notifications (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourcompany.com
SMTP_PASS=your_app_password
SMTP_TO=admin@yourcompany.com

# Slack Notifications (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Discord Notifications (Optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Teams Notifications (Optional)
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...

# Custom Webhook (Optional)
CUSTOM_WEBHOOK_URL=https://your-monitoring-system.com/webhook
```

## Installation Steps

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Database Migration

```bash
# Run the billing tables migration
alembic upgrade head
```

### 3. Start Redis Server

```bash
# Ubuntu/Debian
sudo systemctl start redis-server

# macOS with Homebrew
brew services start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

### 4. Start Celery Worker

```bash
# In a separate terminal
cd backend
python scripts/start_celery_worker.py

# Or using celery command directly
celery -A app.services.billing.async_webhook_service worker --loglevel=info
```

### 5. Start Celery Beat Scheduler

```bash
# In another separate terminal
cd backend
python scripts/start_celery_beat.py

# Or using celery command directly
celery -A app.services.billing.async_webhook_service beat --loglevel=info
```

### 6. Start FastAPI Application

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Production Deployment

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: collexa
      POSTGRES_USER: collexa
      POSTGRES_PASSWORD: your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  api:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://collexa:your_secure_password@postgres:5432/collexa
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
      PAYMENT_PROVIDER: stripe
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET}
      SMTP_SERVER: ${SMTP_SERVER}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASS: ${SMTP_PASS}
      SLACK_WEBHOOK_URL: ${SLACK_WEBHOOK_URL}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  celery-worker:
    build: ./backend
    command: celery -A app.services.billing.async_webhook_service worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://collexa:your_secure_password@postgres:5432/collexa
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  celery-beat:
    build: ./backend
    command: celery -A app.services.billing.async_webhook_service beat --loglevel=info
    environment:
      DATABASE_URL: postgresql://collexa:your_secure_password@postgres:5432/collexa
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collexa-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: collexa-api
  template:
    metadata:
      labels:
        app: collexa-api
    spec:
      containers:
      - name: api
        image: collexa/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: collexa-secrets
              key: database-url
        - name: CELERY_BROKER_URL
          value: "redis://redis-service:6379/0"
        - name: STRIPE_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: collexa-secrets
              key: stripe-secret-key

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collexa-celery-worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app: collexa-celery-worker
  template:
    metadata:
      labels:
        app: collexa-celery-worker
    spec:
      containers:
      - name: celery-worker
        image: collexa/api:latest
        command: ["celery", "-A", "app.services.billing.async_webhook_service", "worker", "--loglevel=info"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: collexa-secrets
              key: database-url
        - name: CELERY_BROKER_URL
          value: "redis://redis-service:6379/0"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collexa-celery-beat
spec:
  replicas: 1
  selector:
    matchLabels:
      app: collexa-celery-beat
  template:
    metadata:
      labels:
        app: collexa-celery-beat
    spec:
      containers:
      - name: celery-beat
        image: collexa/api:latest
        command: ["celery", "-A", "app.services.billing.async_webhook_service", "beat", "--loglevel=info"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: collexa-secrets
              key: database-url
        - name: CELERY_BROKER_URL
          value: "redis://redis-service:6379/0"
```

## Configuration

### Notification Channels

#### Email (SMTP)
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourcompany.com
SMTP_PASS=your_app_password
SMTP_TO=admin@yourcompany.com
```

#### Slack
1. Create a Slack app at https://api.slack.com/apps
2. Add Incoming Webhooks feature
3. Create webhook for your channel
4. Set `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...`

#### Discord
1. Go to your Discord server settings
2. Navigate to Integrations > Webhooks
3. Create a new webhook
4. Set `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`

#### Microsoft Teams
1. Go to your Teams channel
2. Click "..." > Connectors
3. Add "Incoming Webhook"
4. Set `TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...`

### Scheduler Configuration

The scheduler runs these jobs automatically:

- **Budget Violations**: Every 15 minutes
- **Budget Warnings**: Every hour  
- **Daily Budget Reset**: Daily at midnight UTC
- **Weekly Budget Reset**: Monday at midnight UTC
- **Monthly Budget Reset**: 1st of month at midnight UTC
- **Monthly Reports**: 2nd of month at 2 AM UTC
- **Cleanup**: Weekly on Sunday at 3 AM UTC

## Monitoring & Health Checks

### API Endpoints

```bash
# System health
GET /v1/admin/system/health

# Scheduler status
GET /v1/admin/scheduler/status

# Celery status
GET /v1/admin/celery/status

# Notification channels
GET /v1/admin/notifications/channels

# Test notifications
POST /v1/admin/notifications/test
```

### Monitoring Dashboards

#### Celery Monitoring with Flower

```bash
pip install flower
celery -A app.services.billing.async_webhook_service flower
```

Access at http://localhost:5555

#### Custom Monitoring

```python
# Monitor budget violations
import requests

response = requests.get("http://localhost:8000/v1/admin/system/health")
health = response.json()

if health["status"] != "healthy":
    # Send alert to monitoring system
    pass
```

## Troubleshooting

### Common Issues

#### Celery Worker Not Starting
```bash
# Check Redis connection
redis-cli ping

# Check Celery configuration
celery -A app.services.billing.async_webhook_service inspect ping
```

#### Scheduler Not Running
```bash
# Check scheduler status
curl http://localhost:8000/v1/admin/scheduler/status

# Manually start scheduler
curl -X POST http://localhost:8000/v1/admin/scheduler/start
```

#### Notifications Not Sending
```bash
# Test notification channels
curl -X POST http://localhost:8000/v1/admin/notifications/test

# Check configured channels
curl http://localhost:8000/v1/admin/notifications/channels
```

### Logs

```bash
# Application logs
tail -f logs/billing_system.log

# Celery worker logs
celery -A app.services.billing.async_webhook_service worker --loglevel=debug

# Scheduler logs
tail -f logs/scheduler.log
```

## Performance Tuning

### Celery Optimization

```python
# In async_webhook_service.py
celery_app.conf.update(
    worker_prefetch_multiplier=1,  # Reduce for better load balancing
    task_acks_late=True,          # Ensure task completion
    worker_max_tasks_per_child=1000,  # Restart workers periodically
)
```

### Database Optimization

```sql
-- Add indexes for better query performance
CREATE INDEX CONCURRENTLY idx_usage_records_org_period 
ON usage_records(org_id, billing_period);

CREATE INDEX CONCURRENTLY idx_budgets_active 
ON budgets(org_id, status) WHERE status = 'active';
```

### Redis Optimization

```bash
# In redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
```

This deployment guide ensures a production-ready, scalable billing system with automated monitoring, reliable task processing, and comprehensive alerting.

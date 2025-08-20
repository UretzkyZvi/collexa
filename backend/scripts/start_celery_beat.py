#!/usr/bin/env python3
"""
Celery beat scheduler startup script.

This script starts the Celery beat scheduler for periodic billing tasks
such as budget monitoring and monthly report generation.
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.billing.async_webhook_service import celery_app

if __name__ == "__main__":
    # Start Celery beat scheduler
    celery_app.start([
        'beat',
        '--loglevel=info',
        '--schedule=/tmp/celerybeat-schedule',
        '--pidfile=/tmp/celerybeat.pid'
    ])

#!/usr/bin/env python3
"""
Celery worker startup script for billing tasks.

This script starts a Celery worker to process billing-related tasks
such as webhook processing, budget monitoring, and usage reporting.
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.billing.async_webhook_service import celery_app

if __name__ == "__main__":
    # Start Celery worker
    celery_app.start(
        [
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--queues=celery",
            "--hostname=billing-worker@%h",
        ]
    )

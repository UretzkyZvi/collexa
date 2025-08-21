"""
Application startup and shutdown handlers.

This module handles initialization and cleanup of background services
like the budget scheduler and notification system.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from app.services.scheduling.budget_scheduler_service import budget_scheduler
from app.services.notifications.alert_service import alert_service
from app.services.http_client import close_http_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """
    Application lifespan manager.

    Handles startup and shutdown of background services.
    """
    # Startup
    logger.info("Starting Collexa billing system...")

    try:
        # Initialize and start the budget scheduler
        await budget_scheduler.start()
        logger.info("Budget scheduler started successfully")

        # Test notification channels
        channels = alert_service.get_configured_channels()
        if channels:
            logger.info(f"Notification channels configured: {', '.join(channels)}")
        else:
            logger.warning("No notification channels configured")

        # Send startup notification
        try:
            await alert_service.send_system_alert(
                title="System Startup",
                message="Collexa billing system has started successfully",
                metadata={
                    "scheduler_running": budget_scheduler.scheduler.running,
                    "notification_channels": len(channels),
                    "version": "1.0.0",
                },
            )
        except Exception as e:
            logger.warning(f"Failed to send startup notification: {e}")

        logger.info("Collexa billing system startup completed")

    except Exception as e:
        logger.error(f"Failed to start background services: {e}")
        # Don't fail the entire application startup

    yield

    # Shutdown
    logger.info("Shutting down Collexa billing system...")

    try:
        # Send shutdown notification
        try:
            await alert_service.send_system_alert(
                title="System Shutdown",
                message="Collexa billing system is shutting down",
                metadata={"timestamp": "2025-01-19T12:00:00Z"},
            )
        except Exception as e:
            logger.warning(f"Failed to send shutdown notification: {e}")

        # Stop the budget scheduler
        await budget_scheduler.stop()
        logger.info("Budget scheduler stopped successfully")

        # Close shared HTTP client
        await close_http_client()
        logger.info("HTTP client closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

    logger.info("Collexa billing system shutdown completed")


async def initialize_services():
    """
    Initialize background services manually.

    This can be called separately if not using the lifespan manager.
    """
    try:
        # Start scheduler
        await budget_scheduler.start()

        # Test notifications
        channels = alert_service.get_configured_channels()
        logger.info(
            f"Initialized services - Scheduler: running, Notifications: {len(channels)} channels"
        )

        return True
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return False


async def shutdown_services():
    """
    Shutdown background services manually.

    This can be called separately if not using the lifespan manager.
    """
    try:
        await budget_scheduler.stop()
        logger.info("Services shutdown completed")
        return True
    except Exception as e:
        logger.error(f"Failed to shutdown services: {e}")
        return False


def setup_logging():
    """Setup logging configuration for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/billing_system.log", mode="a"),
        ],
    )

    # Set specific log levels for different components
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("apprise").setLevel(logging.WARNING)


if __name__ == "__main__":
    # For testing the startup/shutdown process
    async def test_lifecycle():
        setup_logging()

        logger.info("Testing service lifecycle...")

        # Initialize
        success = await initialize_services()
        if success:
            logger.info("Services initialized successfully")

            # Wait a bit
            await asyncio.sleep(5)

            # Shutdown
            await shutdown_services()
        else:
            logger.error("Failed to initialize services")

    asyncio.run(test_lifecycle())

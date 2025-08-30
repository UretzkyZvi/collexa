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
from app.services.compression.dictionary_trainer import ZstdDictionaryTrainer
from app.services.compression.basic_engine import BasicCompressionEngine

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

        # Train a small zstd dictionary from a seed corpus and attach engine to app.state
        try:
            seed_samples = [
                b"L47:FastAPI{routing->L:0.85,DI->D:0.85,async_db->M:0.85,T:8/10,E:auth:3,db_timeout:2}",
                b"L48:FastAPI{routing->L:0.88,DI->M:0.90,async_db->M:0.92,T:9/10,E:auth:1,db_timeout:1}",
                b"L49:FastAPI{routing->M:0.91,DI->M:0.91,async_db->M:0.93,T:10/10,E:auth:0,db_timeout:0}",
                b"AGENT:FS_DEV|CAP:React:5,TS:5,CSS:4,Node:5,Express:5,PG:4,API:5,Docker:4,CICD:4,AWS:4|CON:Security,Scale,Maintain",
                b"CoT:+0.12:step_by_step+format|FS:+0.07:5ex+edge_cases|SC:+0.11:multi_path+consensus",
            ]
            trainer = ZstdDictionaryTrainer(dict_size=1024)
            dictionary = trainer.train(seed_samples * 40)  # replicate to ensure enough data
            compressor = trainer.build_compressor(dictionary)
            app.state.compression_engine = BasicCompressionEngine(
                zstd_compressor=compressor,
                zstd_dict=dictionary,
            )
            logger.info("Compression engine initialized with trained zstd dictionary")
        except Exception as e:
            # Proceed without blocking startup; engine will fall back to msgpack/noop
            app.state.compression_engine = BasicCompressionEngine()
        # Register policy evaluator for tools (OPA adapter) in non-mock modes
        try:
            from app.services.learning.tools.base import set_policy_evaluator
            from app.security.opa import get_opa_engine
            import anyio

            def _sync_opa_tool_gate(tool_name: str, action: str, sandbox_mode: str, context: dict) -> bool:
                # Allow mock mode to follow local allowlist logic (handled in policy_gate)
                if sandbox_mode == "mock":
                    return True

                # Evaluate via OPA for emulated/connected
                async def _eval():
                    engine = get_opa_engine()
                    # Map tool action to a capability string; simple convention for now
                    capability = f"tool:{tool_name}:{action}".lower()
                    user_id = str(context.get("user_id") or "system")
                    org_id = str(context.get("org_id") or context.get("team_id") or "default")
                    agent_id = str(context.get("agent_id") or "unknown")
                    return await engine.can_invoke_capability(
                        user_id=user_id,
                        org_id=org_id,
                        agent_id=agent_id,
                        capability=capability,
                    )

                try:
                    return bool(anyio.run(_eval))  # type: ignore[arg-type]
                except Exception:
                    return False  # fail-closed

            set_policy_evaluator(_sync_opa_tool_gate)
        except Exception:
            # Do not block startup if OPA/tool wiring is not available
            pass

            logger.warning(f"Compression engine initialized without dictionary: {e}")

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

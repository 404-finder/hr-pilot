"""Watchdog timer for long-running operations."""

import time

from telegram.ext import ContextTypes

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def _watchdog_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send periodic status messages during long-running operations."""
    job = context.job
    start_time = job.data["start_time"]
    chat_id = job.data["chat_id"]
    operation_name = job.data["operation_name"]

    elapsed = int((time.time() - start_time) / 60)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"⏳ {operation_name} has been running for {elapsed} minutes. "
                f"Send /cancel to abort and start over."
            ),
        )
    except Exception as e:
        logger.error(f"Watchdog message failed: {e}")


async def start_watchdog(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    operation_name: str,
) -> None:
    """Start a repeating watchdog that alerts the user every 2 minutes.

    Automatically stops any existing watchdog first to prevent duplicates.

    Args:
        context: Telegram context object.
        chat_id: Chat ID to send alerts to.
        operation_name: Human-readable name of the operation.
    """
    stop_watchdog(context)

    job = context.job_queue.run_repeating(
        _watchdog_callback,
        interval=120,
        first=120,
        data={
            "chat_id": chat_id,
            "operation_name": operation_name,
            "start_time": time.time(),
        },
        name=f"watchdog_{chat_id}",
    )
    context.user_data["watchdog_job"] = job
    logger.info(f"Watchdog started for: {operation_name}")


def stop_watchdog(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop the watchdog timer if one is running.

    This is a sync function — safe to call from finally blocks.

    Args:
        context: Telegram context object.
    """
    job = context.user_data.pop("watchdog_job", None)
    if job:
        job.schedule_removal()
        logger.info("Watchdog stopped")

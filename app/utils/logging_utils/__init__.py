"""
Convenience accessors for the structured logging facility.

Usage:
    from app.utils.logging_utils import get_logger
    log = get_logger("registration")
    log.info("user created", extra={"user_id": user.id})
"""

from .manager import (
    LogCategory,
    LoggerManager,
    archive_logs,
    clear_all_logs,
    clear_log,
    get_logger,
    get_log_context,
    init_logger,
    logger_manager,
    log_context,
    register_category,
    set_log_context,
    shutdown_logger,
    update_log_context,
    clear_log_context,
)

__all__ = [
    "LogCategory",
    "LoggerManager",
    "get_logger",
    "get_log_context",
    "set_log_context",
    "update_log_context",
    "clear_log_context",
    "log_context",
    "init_logger",
    "logger_manager",
    "register_category",
    "clear_log",
    "clear_all_logs",
    "archive_logs",
    "shutdown_logger",
]

"""Structured logging configuration using Loguru."""

import sys

from loguru import logger

from app.core.config import get_settings


def setup_logging() -> None:
    """Configure Loguru for structured JSON logging in production."""
    settings = get_settings()

    # Remove default handler
    logger.remove()

    # Console handler — always present
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.DEBUG else "INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # JSON file handler for non-development environments
    if settings.ENV != "development":
        logger.add(
            "logs/app.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
            rotation="10 MB",
            retention="30 days",
            compression="gz",
            serialize=True,
        )

    logger.info("Logging configured for {} environment", settings.ENV)

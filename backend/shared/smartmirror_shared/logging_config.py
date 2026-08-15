"""Structured logging that never records image payloads."""

import logging
from typing import Any


SENSITIVE_KEYS = frozenset(
    {
        "customer_still_data_url",
        "image",
        "image_base64",
        "file",
        "parts_bytes",
    }
)


def configure_service_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """Configure a named logger that redacts image-bearing fields."""
    logger = logging.getLogger(service_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(level.upper())
    return logger


def safe_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop keys that could contain face or cloth image bytes."""
    return {key: value for key, value in payload.items() if key not in SENSITIVE_KEYS}

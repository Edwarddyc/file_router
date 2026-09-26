import logging
from typing import Any


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def event(logger: logging.Logger, name: str, **fields: Any) -> None:
    rendered = " ".join(f"{key}={value}" for key, value in sorted(fields.items()))
    logger.info("event=%s %s", name, rendered)


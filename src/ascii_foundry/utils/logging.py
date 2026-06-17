from __future__ import annotations

import logging

from ascii_foundry.utils.paths import log_dir


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("ascii_foundry")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_dir() / "ascii_foundry.log", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


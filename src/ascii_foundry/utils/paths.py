from __future__ import annotations

from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir, user_log_dir

from ascii_foundry import __app_name__


def config_dir() -> Path:
    path = Path(user_config_dir(__app_name__, appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = Path(user_cache_dir(__app_name__, appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = Path(user_log_dir(__app_name__, appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


import logging
import json
import sys

from logging.handlers import RotatingFileHandler
from pathlib import Path


def _setup_logging(
    app_name: str = "frostel",
    log_level: str = "INFO",
    log_dir: Path = None,
    console_output: bool = False,
):
    if log_dir is None:
        # root dir
        log_dir = Path(__file__).resolve().parent.parent.parent / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # We are adding our own handlers. Clear existing unes to prevent duplication
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt=("%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stdout
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    app_log_file = log_dir / f"{app_name}.log"
    file_handler = RotatingFileHandler(
        filename=app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,  # Keep 5 old versions
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Separate file for errors
    error_log_file = log_dir / f"{app_name}_errors.log"
    error_handler = RotatingFileHandler(
        filename=error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,  # Keep more error logs
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)  # Only ERROR and above
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # werkzeug and pymysql have a lot of noise
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("pymysql").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info(f"Logging initialized for {app_name}")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Logging to stdout: {console_output}")
    logger.info(f"Log directory: {log_dir}")
    logger.info(f"Application log: {app_log_file}")
    logger.info(f"Error log: {error_log_file}")
    logger.info("=" * 80)

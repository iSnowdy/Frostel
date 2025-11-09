import atexit
import logging

from flask import Flask
import os
from flask.cli import load_dotenv

from app.database.connection import (
    init_connection_pool,
    ConnectionPool,
    close_connection_pool,
)
from app.database.connection_config import ConnectionPoolConfig
from app.utils.logger import _setup_logging

app = Flask(__name__)

load_dotenv()
logger = logging.getLogger(__name__)


def _init_database() -> ConnectionPool:
    logger.info("Initialising database")

    try:
        config = ConnectionPoolConfig.from_env()
        pool: ConnectionPool = init_connection_pool(config)

        logger.info("Connection pool initialised correctly")

        return pool

    except Exception as e:
        logger.error(f"Failed to initialise database: {e}", exc_info=True)
        raise


def _register_blueprints(app: Flask):
    from app.api.v1.health import health_bp
    from app.api.v1.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp, url_prefix="/health")

    logger.info("Blueprints registered")


def _register_error_handlers(app: Flask):
    # TODO: Add possible error handlers
    pass


def setup_app():
    logger_level = os.getenv("LOG_LEVEL", "INFO").upper()
    _setup_logging(log_level=logger_level, console_output=True)


    _init_database()
    _register_blueprints(app)
    _register_error_handlers(app)


def cleanup_app():
    logger.info("Cleaning up resources...")

    try:
        logger.info("Closing database connections...")
        close_connection_pool()
        logger.info("Database connections closed")

        # Other resources to clean up here

    except Exception as e:
        logger.error(f"Error during application cleanup: {e}", exc_info=True)


atexit.register(cleanup_app)


@app.teardown_appcontext
def teardown(exception=None):
    if exception:
        logger.error(f"Request failed with exception: {exception}", exc_info=True)
        # This is purely for logging purposes on requests failed that reach this block of code
        # Nothing else is done. Maybe consider removing this even?


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST")
    port = int(os.getenv("FLASK_PORT"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    logger.info(f"Starting Frostel app server on {host}:{port} with debug={debug}")

    try:
        setup_app()
        app.run(host=host, port=port, debug=debug)

    except KeyboardInterrupt:
        logger.error("Received keyboard interrupt, shutting down...")
        cleanup_app()

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        cleanup_app()
        raise

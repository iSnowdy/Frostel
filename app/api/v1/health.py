import logging

from flask import Blueprint, jsonify

from app.database.connection import get_pool, ConnectionPool
from app.models.enums import CircuitState

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


@health_bp.route("/db")
def db_health():
    try:
        pool: ConnectionPool = get_pool()
        health: dict = pool.health_check()
        is_healthy: bool = health["status"] == "healthy"

        if is_healthy:
            return jsonify(health), 200
        return jsonify(health), 503

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify(
            {
                "status": "unhealthy",
                "error": str(e),
            }
        ), 500


@health_bp.route("/pool")
def pool_stats():
    try:
        pool: ConnectionPool = get_pool()
        stats: dict = pool.get_connection_pool_stats()
        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Failed to get pool stats: {e}", exc_info=True)
        return jsonify(
            {
                "status": "unhealthy",
                "error": str(e),
            }
        ), 500


@health_bp.route("/metrics")
def metrics():
    try:
        pool: ConnectionPool = get_pool()
        metrics: dict = pool.get_metrics()
        return jsonify(metrics), 200

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        return jsonify(
            {
                "error": str(e),
            }
        ), 500


# Overall /health status of the application resources
@health_bp.route("/")
def overall_health():
    try:
        pool: ConnectionPool = get_pool()

        # Database health
        db_health: dict = pool.health_check()
        db_status: str = db_health.get("status", "unhealthy")

        # Pool stats
        pool_stats: dict = pool.get_connection_pool_stats()
        pool_status = (
            "healthy" if pool_stats["available_connections"] > 0 else "degraded"
        )

        # Metrics
        metrics: dict = pool.get_metrics()
        metrics_status = (
            "healthy"
            if metrics["circuit_state"] == CircuitState.CLOSED.value
            else "degraded"
        )

        overall_status = (
            "healthy"
            if all(
                [
                    db_status == "healthy",
                    pool_status == "healthy",
                    metrics_status == "healthy",
                ]
            )
            else "degraded"
        )

        response = {
            "status": overall_status,
            "checks": {
                "database": db_status,
                "pool": pool_status,
                "metrics": metrics_status,
            },
            "details": {
                "pool_stats": pool_stats,
                "metrics": metrics,
            },
            "timestamp": db_health.get("timestamp"),
        }
        status_code = 200 if overall_status == "healthy" else 503

        return jsonify(response), status_code

    except Exception as e:
        logger.error(f"Failed to get overall health: {e}", exc_info=True)
        return jsonify(
            {
                "status": "unhealthy",
                "error": str(e),
            }
        ), 503

import logging
import os
import time
from contextlib import contextmanager
from multiprocessing import pool
from threading import Lock
from datetime import datetime, timezone

from queue import Queue, Empty, Full
from typing import Generator

import pymysql
from pymysql import Connection, Error

from app.database.connection_config import ConnectionPoolConfig
from app.database.connection_metrics import ConnectionMetrics
from app.exceptions.base import CircuitBreakerException
from app.models.enums import CircuitState

# TODO: Change to custom logger
# TODO: Change Exceptions to own
logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Thread-safe pure MySQL connection pool with integrated metrics, health checks,
    and a basic circuit breaker mechanism.

    The pool maintains a fixed number of reusable database connections, with
    bounded overflow capacity for temporary load spikes. Connections are
    recycled based on age and validated for liveness before reuse. Metrics are
    tracked for connection usage, errors, and circuit breaker activity.

    Features:
        - Fixed-size pool with bounded overflow connections.
        - Connection recycling based on age (``pool_recycle``).
        - Health checks and usage metrics.
        - Simple circuit breaker to suspend operations after repeated failures.
        - Context manager for safe checkout/commit/rollback/return handling.

    Thread Safety:
        All operations on the pool are thread-safe and use internal locks for
        synchronisation. Connections are not shared between threads.

    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        pool_size: int = 10,
        max_overflow: int = 5,
        pool_recycle: int = 3600,
        connection_timeout: int = 10,
        max_retry_attempts: int = 3,
        circuit_failure_threshold: int = 5,  # Open the circuit after N failures
        circuit_timeout: int = 60,  # Close the circuit after N seconds
        health_check_interval: int = 60,  # Health checks every 60 seconds
    ):
        """
        Initialise and populate the connection pool.

        This constructor sets up the pool parameters, initialises the internal
        data structures (thread-safe queues, locks, metrics), and creates the
        initial batch of pooled connections. If connection creation fails, the
        error is logged and re-raised.

        Environment Variables:
            - ``FROSTEL_MYSQL_HOST``
            - ``FROSTEL_MYSQL_PORT``
            - ``FROSTEL_MYSQL_USER``
            - ``FROSTEL_MYSQL_PASSWORD``
            - ``FROSTEL_MYSQL_DATABASE``

        Args:
            host (str): Database host or IP address.
            port (int): Database port (typically 3306).
            user (str): Database user name.
            password (str): Password for authentication.
            database (str): Default database/schema to use.
            pool_size (int, optional): Maximum number of idle pooled connections.
            max_overflow (int, optional): Number of additional temporary connections
                allowed when the pool is empty.
            pool_recycle (int, optional): Maximum connection age in seconds before
                recycling. Defaults to 3600.
            connection_timeout (int, optional): Timeout (seconds) for establishing
                a new connection. Defaults to 10.
            max_retry_attempts (int, optional): Maximum retry attempts for failed
                connection creations. Defaults to 3.
            circuit_failure_threshold (int, optional): Number of consecutive failures
                before opening the circuit. Defaults to 5.
            circuit_timeout (int, optional): Time in seconds before circuit breaker
                attempts half-open recovery. Defaults to 60.
            health_check_interval (int, optional): Interval between background
                health checks in seconds. Defaults to 60.

        Raises:
            Exception: If the initial pool creation fails due to connection errors.
        """

        self.host = host or os.getenv("FROSTEL_MYSQL_HOST")
        self.port = port or int(os.getenv("FROSTEL_MYSQL_PORT"))
        self.user = user or os.getenv("FROSTEL_MYSQL_USER")
        self._password = password or os.getenv("FROSTEL_MYSQL_PASSWORD")
        self.database = database or os.getenv("FROSTEL_MYSQL_DATABASE")
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.connection_timeout = connection_timeout
        self.max_retry_attempts = max_retry_attempts
        self.health_check_interval = health_check_interval

        # Thread-safe connection pool
        self._pool: Queue = Queue(maxsize=pool_size)  # Producer-Consumer pattern
        self._overflow_count = 0
        self._overflow_lock = Lock()

        self._connection_timestamps = {}  # For recycling the connection

        self.metrics = ConnectionMetrics()
        self._metrics_lock = Lock()

        # Circuit breaker
        self._circuit_failure_threshold = circuit_failure_threshold
        self._circuit_timeout = circuit_timeout
        self._circuit_breaker_lock = Lock()

        self._initialise_pool()

        logger.info(
            f"Connection pool initialised: {pool_size} connections to "
            f"{self.host}:{self.port}/{self.database}"
        )

    def _initialise_pool(self):
        """
        Populate the connection pool with the initial set of database connections.

        Each connection is created using `_create_connection_with_retry()` and
        added to the internal pool queue. Errors encountered during creation are
        logged and counted in metrics before being re-raised.

        Raises:
            Exception: If a connection cannot be created after retries.
        """

        for _ in range(self.pool_size):
            try:
                connection = self._create_connection_with_retry()
                self._pool.put(connection)
            except Exception as e:
                with self._metrics_lock:
                    self.metrics.total_errors += 1

                logger.error(f"Failed to create connection: {e}")
                raise

    def _create_connection_with_retry(self) -> Connection:
        """
        Attempt to create a new MySQL database connection with retry logic.

        This method will retry up to ``max_retry_attempts`` times using
        exponential backoff before giving up and triggering the circuit breaker.
        Upon success, the connection is timestamped, tracked in metrics, and
        returned.

        Returns:
            Connection: A live and initialised PyMySQL connection instance.

        Raises:
            pymysql.err.Error: If connection creation fails after all retries.
        """

        last_error = None
        for attempt in range(self.max_retry_attempts):
            try:
                connection = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self._password,
                    database=self.database,
                    connect_timeout=self.connection_timeout,
                    cursorclass=pymysql.cursors.DictCursor,
                    charset="utf8mb4",
                    autocommit=False,  # We specify when we want transactions to be committed
                )

                # Stores when the connection was created. Useful for future recycling of it
                self._connection_timestamps[id(connection)] = time.time()

                with self._metrics_lock:
                    self.metrics.total_connections_created += 1
                    self.metrics.idle_connections += 1

                if attempt > 0:
                    with self._metrics_lock:
                        self.metrics.total_retries += attempt
                    logger.warning(
                        f"Connection created after {attempt}/{self.max_retry_attempts} retries"
                    )

                logger.debug(f"Created a new database connection: {id(connection)}")
                return connection

            except Error as e:
                last_error = e

                if attempt < self.max_retry_attempts - 1:
                    # Exponential backoff
                    delay = self._calculate_backoff_delay(attempt)
                    logger.warning(
                        f"Connection attempt {attempt + 1}/{self.max_retry_attempts} failed. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)

        # If we reach this block, max retries have been reached
        with self._metrics_lock:
            self.metrics.total_errors += 1

        logger.error(
            f"Failed to create connection after {self.max_retry_attempts} retries"
        )

        self._record_circuit_failure()
        raise last_error

    def _calculate_backoff_delay(self, attempt: int, base_delay: float = 0.5) -> float:
        """
        Compute an exponential backoff delay between retry attempts.

        This delay grows exponentially with each failed attempt to avoid
        overwhelming the database with repeated rapid reconnection attempts.

        Formula:
            delay = base_delay * (2 ** attempt)

        Args:
            attempt (int): Zero-based retry attempt number.
            base_delay (float, optional): Base delay in seconds for the first retry.
                Defaults to 0.5 seconds.

        Returns:
            float: Computed delay time in seconds.
        """

        return base_delay * (2**attempt)

    def _record_circuit_failure(self):
        """
        Record a database connection failure and evaluate circuit breaker state.

        Each failure increments the internal failure counter. When the number of
        failures reaches or exceeds ``_circuit_failure_threshold``, the circuit
        enters the **OPEN** state, temporarily blocking new connection attempts
        until ``_circuit_timeout`` expires.

        This mechanism prevents cascading failures when the database is
        unreachable or unhealthy.

        Side Effects:
            - Updates ``metrics.circuit_failures`` and ``metrics.circuit_state``.
            - Sets ``metrics.circuit_opened_at`` when the circuit transitions to OPEN.
        """

        with self._circuit_breaker_lock:
            self.metrics.circuit_failures += 1

            if self.metrics.circuit_failures >= self._circuit_failure_threshold:
                if self.metrics.circuit_state != CircuitState.OPEN:
                    logger.warning(
                        f"Circuit breaker opened after {self.metrics.circuit_failures} failures"
                    )
                    self.metrics.circuit_state = CircuitState.OPEN
                    self.metrics.circuit_opened_at = datetime.now(timezone.utc)

    def _check_circuit(self):
        """
        Evaluate whether the circuit breaker currently allows database operations.

        If the circuit is in the **OPEN** state, this method checks how much time
        has passed since the circuit was opened:

        - If less than ``_circuit_timeout`` seconds have elapsed, a
          ``CircuitBreakerException`` is raised.
        - If more time has passed, the circuit transitions to **HALF_OPEN**,
          allowing a single trial operation to test recovery.

        Raises:
            CircuitBreakerException: If the circuit is open and not ready to retry.
        """

        with self._circuit_breaker_lock:
            if self.metrics.circuit_state == CircuitState.OPEN:
                # The circuit is opened. Check how much time has elapsed since
                elapsed = (
                    datetime.now(timezone.utc) - self.metrics.circuit_opened_at
                ).total_seconds()

                if elapsed > self._circuit_timeout:
                    # In the half-open state we can try one more time after N seconds (timeout)
                    # and if it succeeds, we close the circuit again. Else, raise the exception
                    logger.warning("Circuit breaker entering half-open state")
                    self.metrics.circuit_state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerException(
                        f"Circuit breaker is open. Database appears to be down. "
                        f"Retry in {self._circuit_timeout - elapsed:.0f}s"
                    )

    def _reset_circuit(self):
        """
        Reset the circuit breaker after successful database interaction.

        When a database operation succeeds while the circuit is **HALF_OPEN**,
        this method restores it to the **CLOSED** state and resets related metrics.

        Side Effects:
            - Resets ``metrics.circuit_failures`` and ``metrics.circuit_opened_at``.
            - Updates ``metrics.circuit_state`` to CLOSED.
        """

        with self._circuit_breaker_lock:
            if self.metrics.circuit_state != CircuitState.CLOSED:
                logger.warning("Circuit breaker closed. Database has recovered")
                self.metrics.circuit_state = CircuitState.CLOSED
                self.metrics.circuit_failures = 0 # TODO: Should we reset this?
                self.metrics.circuit_opened_at = None

    def _is_connection_stale(self, connection: Connection) -> bool:
        """
        Determine if a connection has exceeded its allowed lifetime.

        Each connection is timestamped when created. If the current age of the
        connection exceeds ``pool_recycle`` seconds, it is considered stale and
        should be replaced with a new one.

        Args:
            connection (Connection): The connection object to evaluate.

        Returns:
            bool: ``True`` if the connection is stale or lacks a timestamp, ``False`` otherwise.
        """

        connection_id = id(connection)
        if connection_id not in self._connection_timestamps:
            return True  # Connection has never been used before

        connection_age = time.time() - self._connection_timestamps[connection_id]
        return connection_age > self.pool_recycle

    def _is_connection_alive(self, connection: Connection) -> bool:
        """
        Verify whether a database connection is still active and usable.

        Uses ``connection.ping(reconnect=False)`` to check if the connection
        responds without re-establishing itself. This prevents using broken or
        disconnected sockets.

        Args:
            connection (Connection): The PyMySQL connection to test.

        Returns:
            bool: ``True`` if the connection responds successfully, ``False`` otherwise.
        """

        try:
            connection.ping(
                reconnect=False
            )  # reconnect=False prevents reconnecting if the connection is closed
            return True
        except:  # Broader on purpose
            logger.error("Failed to ping connection")
            return False

    def _get_connection(self) -> Connection:
        """
        Retrieve an available connection from the pool or create a temporary overflow connection.

        The method performs the following:
            1. Attempts to get a connection from the queue.
            2. If the connection is stale or dead, it is replaced.
            3. If the pool is empty, a temporary overflow connection may be created.
            4. If overflow limit is reached, it waits up to 10 seconds for one to become available.

        Thread-safe and non-blocking except when waiting for an available slot.

        Returns:
            Connection: A live and usable database connection.

        Raises:
            queue.Empty: If no connection becomes available within the timeout.
            Exception: For unexpected errors during connection retrieval.
        """

        try:
            connection = self._pool.get(block=False)

            # Check if the connection is usable
            if self._is_connection_stale(connection) or not self._is_connection_alive(
                connection
            ):
                logger.debug(f"Recycling stale connection: {id(connection)}")
                connection.close()

                with self._metrics_lock:
                    self.metrics.total_connections_closed += 1

                self._connection_timestamps.pop(
                    id(connection), None
                )  # Defensive since it might not exist

                # Create a fresh connection
                connection = self._create_connection_with_retry()

            return connection

        except Empty:
            logger.debug("Connection pool is empty, creating a new overflow connection")
            # Since the pool is empty, we create a new connection to use as overflow
            with self._overflow_lock:
                if self._overflow_count < self.max_overflow:
                    self._overflow_count += 1
                    with self._metrics_lock:
                        self.metrics.overflow_connections = self._overflow_count

                    logger.debug(
                        f"Creating an overflow connection ({self._overflow_count}/{self.max_overflow})"
                    )
                    return self._create_connection_with_retry()
                else:
                    timeout = 10
                    logger.warning(
                        f"Connection pool overflowed, cannot create a new connection. Waiting {timeout} seconds"
                    )
                    connection = self._pool.get(block=True, timeout=timeout)
                    return connection

        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
            with self._metrics_lock:
                self.metrics.total_errors += 1

            raise

    def _return_connection(self, connection: Connection):
        """
        Return a database connection to the pool after use.

        This method ensures proper clean-up and resource management:
            - Rolls back any uncommitted transactions to avoid leakage.
            - Returns idle connections to the pool if space is available.
            - Closes and discards overflow connections instead of reusing them.

        Args:
            connection (Connection): The connection to return.

        Raises:
            Exception: If returning or closing the connection fails.
        """

        try:
            if connection.open:
                # Clean the connection state by rolling back anything still uncommited in it
                # We take this defensive approach because we don't know what exists inside the connection
                connection.rollback()

            try:
                self._pool.put(connection, block=False)
            except Full:
                # If the pool is full, means we are trying to put back an overflow connection
                # So we simply close it without actually returning it to the pool
                with self._overflow_lock:
                    self._overflow_count -= 1
                    with self._metrics_lock:
                        self.metrics.overflow_connections = self._overflow_count

                connection.close()

                with self._metrics_lock:
                    self.metrics.total_connections_closed += 1
                    self.metrics.idle_connections -= 1

                self._connection_timestamps.pop(id(connection), None)
                logger.debug(
                    f"Closed overflow connection {id(connection)} ({self._overflow_count}/{self.max_overflow})"
                )

        except Exception as e:
            with self._metrics_lock:
                self.metrics.total_errors += 1

            logger.error(f"Failed to return connection: {e}")
            raise

    @contextmanager
    def get_connection(self) -> Generator[Connection, None, None]:
        """
        Context manager that provides a managed database connection from the pool.

        This method yields an active connection that is automatically managed:
            - Checks the circuit breaker before allocating a connection.
            - Retrieves a connection from the pool and updates usage metrics.
            - Commits the transaction on successful block exit.
            - Rolls back the transaction on any raised exception.
            - Returns the connection to the pool after usage.
            - Resets the circuit breaker if the operation succeeds.

        This ensures safe transactional boundaries and maintains accurate metrics for
        pool utilisation, checkout latency, and error tracking.

        Yields:
            Connection: An active database connection ready for executing queries.

        Raises:
            Exception: Propagates any exception raised during query execution or commit/rollback.
        """

        self._check_circuit()

        checkout_start_time = time.time()
        connection = None

        try:
            connection = self._get_connection()

            checkout_time_ms = (time.time() - checkout_start_time) * 1000

            # Update usage metrics
            with self._metrics_lock:
                self.metrics.total_checkouts += 1
                self.metrics.active_connections += 1
                self.metrics.idle_connections -= 1

                n = self.metrics.total_checkouts
                self.metrics.avg_checkout_time_ms = (
                    self.metrics.avg_checkout_time_ms * (n - 1) + checkout_time_ms
                ) / n
                self.metrics.max_checkout_time_ms = max(
                    self.metrics.max_checkout_time_ms, checkout_time_ms
                )

            yield connection
            connection.commit()

            self._reset_circuit()  # Successfully committed, reset the circuit breaker
        except Exception as e:
            if connection:
                connection.rollback()

            with self._metrics_lock:
                self.metrics.total_errors += 1

            logger.error(f"Exception occurred while executing query: {e}")
            raise
        finally:
            if connection:
                self._return_connection(connection)

            with self._metrics_lock:
                self.metrics.active_connections -= 1
                self.metrics.total_checkins += 1
                self.metrics.idle_connections += 1

    def close_all_connections(self):
        """
        Closes and removes all active and idle connections from the pool.

        This method iterates through the internal queue of pooled connections, closing
        each one gracefully and removing its timestamp record. It is typically called
        during service shutdown, maintenance, or when a database reset is required.

        The pool is emptied after this call, and all connections are properly closed
        at the driver level.

        Returns:
            None
        """

        while not self._pool.empty():
            try:
                connection = self._pool.get(block=False)
                connection.close()
                self._connection_timestamps.pop(id(connection), None)
            except Empty:
                break
        logging.info("Closed all database connections")

    def get_connection_pool_stats(self) -> dict:
        """
        Returns a summary of the current connection pool state.

        The returned information reflects both static configuration parameters
        (such as pool size and overflow limit) and dynamic usage statistics
        (such as the number of available or in-use connections).

        Returns:
            dict: A dictionary containing:
                - pool_size (int): Total size of the connection pool.
                - available_connections (int): Number of idle connections currently in the pool.
                - in_use_connections (int): Number of active connections checked out by clients.
                - overflow_connections (int): Number of overflow connections created beyond the pool size.
                - overflow_limit (int): Maximum number of overflow connections allowed.
        """

        return {
            "pool_size": self.pool_size,
            "available_connections": self._pool.qsize(),
            "in_use_connections": self.pool_size - self._pool.qsize(),
            "overflow_connections": self._overflow_count,
            "overflow_limit": self.max_overflow,
        }

    def health_check(self) -> dict:
        """
        Performs a direct health check against the database server.

        This method establishes a temporary connection (not from the pool) and
        executes a lightweight `SELECT 1` query to verify database availability
        and responsiveness. It measures query latency and updates internal health
        metrics accordingly.

        On success, the circuit metrics are refreshed and the pool statistics are included
        in the response. On failure, the method increments the failure counter and returns
        diagnostic details.

        Returns:
            dict: A structured health report containing:
                - status (str): "healthy" or "unhealthy".
                - latency_ms (float, optional): Query latency in milliseconds (if healthy).
                - pool_stats (dict, optional): Current pool utilisation statistics.
                - connection_metrics (dict, optional): Internal connection and circuit metrics.
                - error (str, optional): Description of the failure cause (if unhealthy).
                - failures (int, optional): Consecutive health check failure count.
                - timestamp (str): ISO 8601 timestamp of the health check result.
        """

        start_time = time.time()

        try:
            # Use a direct connection to the DB
            # This way we won't consume a pool connection

            health_connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self._password,
                database=self.database,
                connect_timeout=5,
            )

            try:
                with health_connection.cursor() as cursor:
                    cursor.execute("SELECT 1 as health_check;")
                    row = cursor.fetchone()

                # Success path
                latency_ms = (time.time() - start_time) * 1000

                metrics: dict
                with self._metrics_lock:
                    self.metrics.last_health_check = datetime.now(timezone.utc)
                    self.metrics.health_check_failures = 0
                    metrics = self.metrics.to_dict()

                return {
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                    "pool_stats": self.get_connection_pool_stats(),
                    "connection_metrics": metrics,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            finally:
                health_connection.close()

        except Exception as e:
            with self._metrics_lock:
                self.metrics.health_check_failures += 1

            return {
                "status": "unhealthy",
                "error": str(e),
                "failures": self.metrics.health_check_failures,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_metrics(self) -> dict:
        logger.debug("Getting connection metrics")
        with self._metrics_lock:
            return self.metrics.to_dict()


# Singleton to use when initialising the application
_pool: ConnectionPool = None


def init_connection_pool(
    config: ConnectionPoolConfig | None = None,
    **kwargs,
):
    """
    Initialise the global connection pool.

    Args:
        config: ConnectionPoolConfig object
        **kwargs: Individual parameters (alternative to config)

           host: Database host
           port: Database port
           user: Database user
           password: Database password
           database: Database name
           **kwargs: Optional parameters (pool_size, max_overflow, etc.)
               - pool_size (int): Number of permanent connections (default: 10)
               - max_overflow (int): Additional connections under load (default: 5)
               - pool_recycle (int): Recycle connections after N seconds (default: 3600)
               - connection_timeout (int): Connection timeout in seconds (default: 10)
               - max_retry_attempts (int): Max retry attempts (default: 3)
               - circuit_failure_threshold (int): Failures before opening circuit (default: 5)
               - circuit_timeout (int): Seconds before testing recovery (default: 60)
               - health_check_interval (int): Health check frequency (default: 60)

       Returns:
           Initialized connection pool
    """
    global _pool

    if _pool is not None:
        logger.warning("Connection pool already initialised")
        return _pool

    # Either use the config dict or the individual parameters passed as kwargs
    if config is not None:
        _pool = ConnectionPool(**config.to_dict())
    else:
        _pool = ConnectionPool(**kwargs)

    return _pool


def get_pool() -> ConnectionPool:
    if pool is None:
        raise RuntimeError(
            "Connection pool not initialised. Call init_connection_pool() during application startup"
        )
    return _pool


def close_connection_pool():
    global _pool
    if _pool is not None:
        _pool.close_all_connections()
        _pool = None

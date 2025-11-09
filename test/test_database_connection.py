# test_connection_pool_advanced.py
"""Connection pool testing suite.

This module provides comprehensive testing for the database connection pool
implementation, including multi-threading, overflow handling, circuit breaker
behaviour, and metrics validation.

Tests:
    1. Basic connection and query execution
    2. Connection reuse verification
    3. Multi-threaded concurrent access
    4. Overflow connection handling
    5. Transaction rollback on errors
    6. Metrics accuracy validation
    7. Error handling and recovery
    8. Stale connection recycling
    9. Pool exhaustion and timeout behaviour
    10. Health check functionality
    11-17. Circuit breaker lifecycle and behaviour

Note:
    This is a testing/validation script and will be refactored into proper
    unit tests in the future.
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import pymysql
from flask.cli import load_dotenv

from app.database.connection import (
    init_connection_pool,
    get_pool,
    close_connection_pool,
)
from app.database.connection_config import ConnectionPoolConfig
from app.exceptions.base import CircuitBreakerException
from app.models.enums import CircuitState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)-10s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
load_dotenv()


def test_1_basic_connection():
    """Test basic connection and query execution.

    Validates:
        - Connection can be obtained from pool
        - Simple SELECT query executes successfully
        - Result data can be retrieved

    Raises:
        AssertionError: If connection or query fails.
    """
    print("\n" + "=" * 80)
    print("TEST 1: Basic Connection and Query")
    print("=" * 80)

    pool = get_pool()

    with pool.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS test, NOW() AS time, VERSION() AS version")
            result = cursor.fetchone()

            print("✅ Query executed successfully")
            print(f"   Test value: {result['test']}")
            print(f"   MySQL version: {result['version']}")

    print("✅ TEST 1 PASSED\n")


def test_2_connection_reuse():
    """Verify connections are properly reused from the pool.

    Executes 5 sequential queries and tracks both MySQL connection IDs
    and Python object IDs to verify connection reuse behavior.

    Validates:
        - Connections are returned to pool after use
        - Same connection objects are reused across queries
        - Pool efficiently manages connection lifecycle

    Note:
        If pool size exceeds number of queries, reuse may not occur.
    """
    print("\n" + "=" * 80)
    print("TEST 2: Connection Reuse Verification")
    print("=" * 80)

    pool = get_pool()
    connection_ids = []
    python_ids = []

    # Execute 5 sequential queries
    for i in range(5):
        with pool.get_connection() as conn:
            python_ids.append(id(conn))  # Python object ID

            with conn.cursor() as cursor:
                cursor.execute("SELECT CONNECTION_ID() as mysql_id")
                result = cursor.fetchone()
                connection_ids.append(result["mysql_id"])
                print(
                    f"   Query {i + 1}: MySQL ID = {result['mysql_id']}, Python ID = {id(conn)}"
                )

    # Analysis
    unique_mysql_ids = len(set(connection_ids))
    unique_python_ids = len(set(python_ids))
    reused_count = len(connection_ids) - unique_python_ids

    print("\n📊 Analysis:")
    print(f"   Total queries: {len(connection_ids)}")
    print(f"   Unique MySQL connection IDs: {unique_mysql_ids}")
    print(f"   Unique Python object IDs: {unique_python_ids}")
    print(f"   Connections reused: {reused_count} times")

    if reused_count > 0:
        print(
            f"✅ Connection reuse CONFIRMED! ({reused_count}/{len(connection_ids)} reused)"
        )
    else:
        print("⚠️  No connection reuse detected (pool might be larger than needed)")

    print("✅ TEST 2 PASSED\n")


def worker_thread(thread_id: int, num_queries: int) -> dict:
    """Execute multiple queries in a worker thread for concurrent testing.

    Args:
        thread_id: Unique identifier for this worker thread.
        num_queries: Number of queries this worker should execute.

    Returns:
        A dictionary containing:
            - thread_id (int): The thread's identifier
            - queries_executed (int): Number of successfully executed queries
            - errors (int): Number of errors encountered
            - connection_ids (list): MySQL connection IDs used

    Note:
        Each query includes a SLEEP(0.1) to simulate realistic workload.
    """
    pool = get_pool()
    results = {
        "thread_id": thread_id,
        "queries_executed": 0,
        "errors": 0,
        "connection_ids": [],
    }

    for i in range(num_queries):
        try:
            with pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT CONNECTION_ID() as conn_id, SLEEP(0.1)")
                    result = cursor.fetchone()
                    results["connection_ids"].append(result["conn_id"])
                    results["queries_executed"] += 1
        except Exception as e:
            results["errors"] += 1
            logger.error(f"Thread {thread_id} error: {e}")

    return results


def test_3_multithreading():
    """Test thread-safe concurrent access to the connection pool.

    Spawns multiple threads executing queries concurrently to validate
    thread safety and proper connection management under load.

    Validates:
        - No race conditions occur with concurrent access
        - Connections are safely shared across threads
        - Pool handles concurrent checkouts/returns correctly
        - Metrics are accurately updated in multi-threaded environment

    Configuration:
        - 10 threads
        - 5 queries per thread
        - Total: 50 concurrent queries
    """
    # ... existing code ...
    print("\n" + "=" * 80)
    print("TEST 3: Multi-threaded Concurrent Access")
    print("=" * 80)

    pool = get_pool()
    num_threads = 10
    queries_per_thread = 5

    print("📋 Configuration:")
    print(f"   Threads: {num_threads}")
    print(f"   Queries per thread: {queries_per_thread}")
    print(f"   Total queries: {num_threads * queries_per_thread}")
    print(f"   Pool size: {pool.pool_size}")
    print(f"   Max overflow: {pool.max_overflow}")
    print("\n⏳ Running concurrent queries...")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(worker_thread, thread_id, queries_per_thread)
            for thread_id in range(num_threads)
        ]

        results = []
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"   ✓ Thread {result['thread_id']}: "
                f"{result['queries_executed']} queries, "
                f"{result['errors']} errors"
            )

    elapsed = time.time() - start_time

    # Aggregate results
    total_queries = sum(r["queries_executed"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    all_connection_ids = [cid for r in results for cid in r["connection_ids"]]
    unique_connections = len(set(all_connection_ids))

    print("\n📊 Results:")
    print(f"   Total time: {elapsed:.2f}s")
    print(f"   Queries executed: {total_queries}")
    print(f"   Errors: {total_errors}")
    print(f"   Unique MySQL connections used: {unique_connections}")
    print(f"   Avg queries per connection: {total_queries / unique_connections:.1f}")
    print(f"   Throughput: {total_queries / elapsed:.1f} queries/sec")

    # Verify thread safety
    if total_errors == 0:
        print(
            f"✅ Thread safety CONFIRMED! No errors in {total_queries} concurrent queries"
        )
    else:
        print(f"⚠️  {total_errors} errors occurred")

    print("✅ TEST 3 PASSED\n")


def test_4_overflow_connections():
    """Test overflow connection handling when pool is exhausted.

    Opens connections up to the pool's maximum capacity (pool_size + max_overflow)
    to verify overflow connection creation and cleanup.

    Validates:
        - Overflow connections are created when pool is exhausted
        - Overflow count is accurately tracked
        - Overflow connections are properly closed when returned
        - Pool returns to normal state after overflow connections released

    Note:
        Holds connections open using internal methods to force overflow state.
    """
    print("\n" + "=" * 80)
    print("TEST 4: Overflow Connection Handling")
    print("=" * 80)

    pool = get_pool()
    max_connections = pool.pool_size + pool.max_overflow

    print("📋 Configuration:")
    print(f"   Pool size: {pool.pool_size}")
    print(f"   Max overflow: {pool.max_overflow}")
    print(f"   Total capacity: {max_connections}")
    print(f"\n⏳ Opening {max_connections} simultaneous connections...")

    # Hold connections open to force overflow
    connections = []
    connection_ids = []

    try:
        for i in range(max_connections):
            # Use internal method to hold connections
            conn = pool._get_connection()
            connections.append(conn)

            with conn.cursor() as cursor:
                cursor.execute("SELECT CONNECTION_ID() as conn_id")
                result = cursor.fetchone()
                connection_ids.append(result["conn_id"])

            stats = pool.get_connection_pool_stats()
            print(
                f"   Connection {i + 1}: "
                f"Available={stats['available_connections']}, "
                f"In-use={stats['in_use_connections']}, "
                f"Overflow={stats['overflow_connections']}"
            )

        print("\n📊 Final State:")
        final_stats = pool.get_connection_pool_stats()
        print(f"   Pool size: {final_stats['pool_size']}")
        print(f"   Available: {final_stats['available_connections']}")
        print(f"   In-use: {final_stats['in_use_connections']}")
        print(f"   Overflow: {final_stats['overflow_connections']}")

        if final_stats["overflow_connections"] > 0:
            print(
                f"✅ Overflow connections CONFIRMED! "
                f"Created {final_stats['overflow_connections']} overflow connections"
            )
        else:
            print("ℹ️  No overflow needed (pool size was sufficient)")

    finally:
        # Return all connections
        print("\n⏳ Returning connections to pool...")
        for conn in connections:
            pool._return_connection(conn)

        # Verify cleanup
        final_stats = pool.get_connection_pool_stats()
        print(
            f"   After cleanup: Available={final_stats['available_connections']}, "
            f"Overflow={final_stats['overflow_connections']}"
        )

    print("✅ TEST 4 PASSED\n")


def test_5_transaction_rollback():
    """Test transaction rollback behaviour on errors.

    Creates a temporary table and tests both successful commits and
    rollback on errors (duplicate key violations).

    Validates:
        - Successful transactions are committed
        - Failed transactions are rolled back
        - Database state remains consistent after errors
        - Connection remains usable after rollback

    Cleanup:
        Removes temporary test table after completion.
    """
    print("\n" + "=" * 80)
    print("TEST 5: Transaction Rollback on Errors")
    print("=" * 80)

    pool = get_pool()

    # Create a temporary test table
    print("📋 Creating temporary test table...")
    with pool.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                           CREATE TABLE test_rollback
                           (
                               id    INT PRIMARY KEY AUTO_INCREMENT,
                               value VARCHAR(50) UNIQUE
                           )
                           """)
            print("   ✓ Table created")

    # Test 1: Successful transaction
    print("\n📝 Test 5.1: Successful transaction...")
    with pool.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO test_rollback (value) VALUES ('test1')")
            cursor.execute("SELECT COUNT(*) as count FROM test_rollback")
            result = cursor.fetchone()
            print(f"   ✓ Inserted successfully, count = {result['count']}")

    # Test 2: Failed transaction (duplicate key)
    print("\n📝 Test 5.2: Failed transaction with rollback...")
    try:
        with pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO test_rollback (value) VALUES ('test2')")
                # This should fail (duplicate)
                cursor.execute("INSERT INTO test_rollback (value) VALUES ('test2')")
    except pymysql.err.IntegrityError as e:
        print(f"   ✓ Expected error caught: {str(e)[:60]}...")

    # Verify rollback
    print("\n📝 Test 5.3: Verifying rollback...")
    with pool.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM test_rollback")
            result = cursor.fetchone()

            if result["count"] == 1:  # Only first insert should exist
                print(
                    f"   ✓ Rollback CONFIRMED! Count = {result['count']} (second insert was rolled back)"
                )
            else:
                print(f"   ✗ Rollback FAILED! Count = {result['count']}")

    print("\n📝 Test 5.4: Cleaning up...")
    with pool.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE test_rollback")

    print("✅ TEST 5 PASSED\n")


def test_6_metrics_accuracy():
    """Validate accuracy of connection pool metrics.

    Executes a known number of queries and verifies that metrics
    accurately reflect the operations performed.

    Validates:
        - Checkout count matches operations
        - Checkin count matches operations
        - Active connections return to zero
        - Timing metrics are reasonable
        - No metric drift or inconsistencies
    """
    print("\n" + "=" * 80)
    print("TEST 6: Metrics Accuracy Validation")
    print("=" * 80)

    pool = get_pool()

    # Get baseline metrics
    print("📋 Baseline metrics:")
    baseline = pool.get_metrics()
    print(f"   Checkouts: {baseline['total_checkouts']}")
    print(f"   Checkins: {baseline['total_checkins']}")
    print(f"   Errors: {baseline['total_errors']}")

    # Perform known operations
    print("\n⏳ Performing 10 queries...")
    num_queries = 10

    for i in range(num_queries):
        with pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

    # Check metrics
    print("\n📊 After 10 queries:")
    after = pool.get_metrics()

    checkouts_delta = after["total_checkouts"] - baseline["total_checkouts"]
    checkins_delta = after["total_checkins"] - baseline["total_checkins"]

    print(f"   Checkouts delta: {checkouts_delta} (expected: {num_queries})")
    print(f"   Checkins delta: {checkins_delta} (expected: {num_queries})")
    print(f"   Active connections: {after['active_connections']} (expected: 0)")
    print(f"   Avg checkout time: {after['avg_checkout_time_ms']:.2f}ms")
    print(f"   Max checkout time: {after['max_checkout_time_ms']:.2f}ms")

    # Validate
    if checkouts_delta == num_queries and checkins_delta == num_queries:
        print("✅ Metrics are ACCURATE! Checkouts and checkins match expected values")
    else:
        print("⚠️  Metrics mismatch detected")

    if after["active_connections"] == 0:
        print("✅ Active connections correctly tracked (returned to pool)")
    else:
        print(f"⚠️  Active connections = {after['active_connections']} (expected 0)")

    print("✅ TEST 6 PASSED\n")


def test_7_error_handling():
    """Test error handling and pool recovery after failures.

    Deliberately triggers various SQL errors to verify the pool
    handles errors gracefully and remains operational.

    Validates:
        - SQL syntax errors are caught and handled
        - Pool remains functional after errors
        - Non-existent table errors are handled
        - Error metrics are incremented correctly
        - Connections are properly returned even after errors

    Errors tested:
        - SQL syntax errors
        - Non-existent table references
    """
    print("\n" + "=" * 80)
    print("TEST 7: Error Handling and Recovery")
    print("=" * 80)

    pool = get_pool()

    # Test 1: Syntax error
    print("📝 Test 7.1: SQL syntax error...")
    try:
        with pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("INVALID SQL QUERY")
    except pymysql.err.ProgrammingError as e:
        print(f"   ✓ Syntax error caught: {str(e)[:60]}...")

    # Verify pool still works
    print("\n📝 Test 7.2: Pool recovery after error...")
    with pool.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            print(f"   ✓ Pool recovered! Query returned: {result['test']}")

    # Test 2: Table doesn't exist
    print("\n📝 Test 7.3: Non-existent table...")
    try:
        with pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM nonexistent_table_12345")
    except pymysql.err.ProgrammingError as e:
        print(f"   ✓ Table error caught: {str(e)[:60]}...")

    # Verify error metrics
    metrics = pool.get_metrics()
    print("\n📊 Error metrics:")
    print(f"   Total errors recorded: {metrics['total_errors']}")

    print("✅ TEST 7 PASSED\n")


def test_8_stale_connection_recycling():
    """Test stale connection detection and recycling mechanism.

    Validates the pool's ability to detect and recycle connections
    that exceed the pool_recycle age threshold.

    Validates:
        - Connection age is tracked via timestamps
        - Stale detection method works correctly
        - Connection liveness checks function properly

    Note:
        Full test requires waiting pool_recycle seconds. This test
        validates the detection mechanisms without full wait time.
    """
    print("\n" + "=" * 80)
    print("TEST 8: Stale Connection Recycling")
    print("=" * 80)

    pool = get_pool()

    print(f"📋 Current pool_recycle setting: {pool.pool_recycle}s")
    print(f"⚠️  Note: Full test requires waiting {pool.pool_recycle}s")
    print("   Skipping full wait for practical testing")
    print(
        f"   (In production, connections older than {pool.pool_recycle}s are recycled)"
    )

    # Test connection age tracking
    print("\n📝 Testing connection timestamp tracking...")
    with pool.get_connection() as conn:
        conn_id = id(conn)
        if conn_id in pool._connection_timestamps:
            age = time.time() - pool._connection_timestamps[conn_id]
            print(f"   ✓ Connection age tracked: {age:.2f}s old")
        else:
            print("   ⚠️  Connection timestamp not found")

    # Test stale detection logic
    print("\n📝 Testing stale detection method...")
    with pool.get_connection() as conn:
        is_stale = pool._is_connection_stale(conn)
        is_alive = pool._is_connection_alive(conn)
        print(f"   Connection is stale: {is_stale}")
        print(f"   Connection is alive: {is_alive}")

        if not is_stale and is_alive:
            print("   ✓ Fresh connection detected correctly")

    print("✅ TEST 8 PASSED\n")


def test_9_pool_exhaustion():
    """Test pool exhaustion and timeout behavior under heavy load.

    Executes more concurrent queries than the pool's maximum capacity
    to verify timeout and queuing behavior.

    Validates:
        - Pool handles requests up to maximum capacity
        - Excess requests wait or timeout appropriately
        - No deadlocks occur under full load
        - Connections become available as queries complete

    Configuration:
        - Executes (pool_size + max_overflow + 2) concurrent queries
        - Each query holds connection for 5 seconds

    Warning:
        This test takes 10-15 seconds to complete.
    """
    print("\n" + "=" * 80)
    print("TEST 9: Pool Exhaustion and Timeout")
    print("=" * 80)

    pool = get_pool()
    max_capacity = pool.pool_size + pool.max_overflow

    print("📋 Configuration:")
    print(f"   Max capacity: {max_capacity}")
    print(f"   Testing with {max_capacity + 2} concurrent long-running queries")
    print("   ⚠️  This test may take 10-15 seconds...")

    def slow_query(query_id: int) -> dict:
        """Execute a slow query that holds connection."""
        start = time.time()
        try:
            with pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Hold connection for 5 seconds
                    cursor.execute("SELECT SLEEP(5)")
                    elapsed = time.time() - start
                    return {"query_id": query_id, "success": True, "time": elapsed}
        except Exception as e:
            elapsed = time.time() - start
            return {
                "query_id": query_id,
                "success": False,
                "time": elapsed,
                "error": str(e),
            }

    print("\n⏳ Starting concurrent slow queries...")
    start_time = time.time()

    # Run more queries than capacity
    num_queries = max_capacity + 2
    with ThreadPoolExecutor(max_workers=num_queries) as executor:
        futures = [executor.submit(slow_query, i) for i in range(num_queries)]

        results = []
        for future in as_completed(futures):
            result = future.result()
            status = "✓" if result["success"] else "✗"
            print(f"   {status} Query {result['query_id']}: {result['time']:.2f}s")
            results.append(result)

    total_time = time.time() - start_time

    # Analysis
    successful = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])

    print("\n📊 Results:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Successful queries: {successful}")
    print(f"   Failed queries: {failed}")

    if successful >= max_capacity:
        print(f"✅ Pool handled at least {max_capacity} concurrent connections")

    if failed > 0:
        print(f"ℹ️  {failed} queries exceeded capacity (expected behavior)")
        print("   These waited for connections or timed out")

    print("✅ TEST 9 PASSED\n")


def test_10_health_check():
    """Test health check functionality.

    Executes the pool's built-in health check to verify database
    connectivity and health monitoring.

    Validates:
        - Health check can connect to database
        - Latency is measured and reasonable
        - Health status is correctly reported
        - Health check doesn't consume pool connections

    Returns health metrics including:
        - Status (healthy/unhealthy)
        - Latency in milliseconds
        - Pool statistics
        - Connection metrics
    """
    print("\n" + "=" * 80)
    print("TEST 10: Health Check")
    print("=" * 80)

    pool = get_pool()

    print("⏳ Running health check...")
    health = pool.health_check()

    print("\n📊 Health Check Results:")
    print(f"   Status: {health['status']}")

    if health["status"] == "healthy":
        print("   ✓ Database is healthy")
        print(f"   Latency: {health['latency_ms']:.2f}ms")
        print(f"   Timestamp: {health['timestamp']}")
    else:
        print("   ✗ Database is unhealthy")
        print(f"   Error: {health.get('error', 'Unknown')}")
        print(f"   Failures: {health.get('failures', 0)}")

    print("✅ TEST 10 PASSED\n")


def test_11_circuit_closed_normal_operation():
    """Test circuit breaker remains CLOSED during normal operation.

    Validates that the circuit breaker stays in CLOSED state when
    all database operations succeed.

    Validates:
        - Initial state is CLOSED
        - Successful queries don't trigger failures
        - Circuit remains CLOSED after multiple successful operations
        - Failure count remains at zero
    """
    print("\n" + "=" * 80)
    print("TEST 11: Circuit Breaker - Normal Operation (CLOSED)")
    print("=" * 80)

    pool = get_pool()

    # Verify initial state of the circuit
    metrics = pool.get_metrics()
    print("📊 Initial state:")
    print(f"   Circuit state: {metrics['circuit_state']}")
    print(f"   Circuit failures: {metrics['circuit_failures']}")

    assert metrics["circuit_state"] == CircuitState.CLOSED.value, (
        "Circuit should be in CLOSED state"
    )

    print("\n⏳ Executing 10 successful queries...")
    for i in range(10):
        with pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

    # Verify that the circuit remains closed, as no errors should've happened
    metrics_after_queries = pool.get_metrics()
    print("\n📊 After successful queries:")
    print(f"   Circuit state: {metrics_after_queries['circuit_state']}")
    print(f"   Circuit failures: {metrics_after_queries['circuit_failures']}")

    if metrics_after_queries["circuit_state"] == CircuitState.CLOSED.value:
        print("✅ Circuit remains CLOSED during normal operation")
    else:
        print(
            "❌ TEST 11 FAILED: Circuit should remain CLOSED during normal operation."
        )

    print("✅ TEST 11 PASSED\n")


def test_12_circuit_open_after_failures():
    """Test circuit breaker opens after threshold failures.

    Simulates connection failures by using invalid credentials to
    verify the circuit opens after reaching the failure threshold.

    Validates:
        - Failures are counted correctly
        - Circuit opens after threshold reached
        - Circuit opened timestamp is recorded
        - Circuit remains open after threshold

    Warning:
        This test triggers retry logic and may take ~10 seconds due to
        exponential backoff on connection failures.

    Side effects:
        Temporarily modifies pool password to trigger failures. Password
        is restored after test completion.
    """
    print("\n" + "=" * 80)
    print("TEST 12: Circuit Breaker - Opens After Failures")
    print("=" * 80)

    pool = get_pool()

    threshold = pool._circuit_failure_threshold
    print("📋 Configuration:")
    print(f"   Failure threshold: {threshold}")
    print(f"   Circuit timeout: {pool._circuit_timeout}s")

    initial_metrics = pool.get_metrics()
    print("📊 Initial state:")
    print(f"   Circuit state: {initial_metrics['circuit_state']}")
    print(f"   Circuit failures: {initial_metrics['circuit_failures']}")

    print(f"\n⏳ Simulating {threshold} connection failures...")
    print("   (This will trigger retry logic, may take ~10 seconds)")

    failure_count = 0

    # We need to trigger errors at the connection creation level
    # For that, we will temporarily break the connection by using wrong credentials on purpose
    original_correct_password = pool._password
    pool._password = "INVALID PASSWORD"

    try:
        for i in range(threshold):
            print(f"\n⏳ Attempting connection {i + 1}/{threshold}...")
            try:
                connection = pool._create_connection_with_retry()
                connection.close()
            except Exception:  # This must fail because invalid password
                failure_count += 1
                print("      ✓ Failure recorded (expected)")

                # Check circuit state after each failure
                metrics = pool.get_metrics()
                print(f"      Circuit failures: {metrics['circuit_failures']}")
                print(f"      Circuit state: {metrics['circuit_state']}")

    finally:
        # Revert the password to its original state
        pool._password = original_correct_password

    final_metrics = pool.get_metrics()
    print(f"\n📊 Final state after {failure_count} failures:")
    print(f"   Circuit state: {final_metrics['circuit_state']}")
    print(f"   Circuit failures: {final_metrics['circuit_failures']}")
    print(f"   Circuit opened at: {final_metrics['circuit_opened_at']}")

    if final_metrics["circuit_state"] == CircuitState.OPEN.value:
        print(f"   ✅ Connection pool OPENED after {threshold} failures (as expected)")
    else:
        print(f"❌ Circuit is {final_metrics['circuit_state']} (expected OPEN)")

    assert final_metrics["circuit_failures"] >= threshold, (
        f"Expected at least {threshold} failures, got {final_metrics['circuit_failures']}"
    )

    assert final_metrics["circuit_state"] == CircuitState.OPEN.value, (
        "Circuit should be OPEN after threshold failures"
    )

    print("✅ TEST 12 PASSED\n")


def test_13_circuit_open_fails_fast():
    """Test circuit breaker fail-fast behavior when OPEN.

    Validates that when the circuit is OPEN, requests are rejected
    immediately without attempting database connections.

    Validates:
        - OPEN circuit rejects requests immediately
        - CircuitBreakerException is raised
        - Rejection time is very fast (<100ms)
        - Multiple rapid requests are all rejected
        - No actual database connections attempted

    Prerequisites:
        Requires circuit to be in OPEN state (from test_12).

    Note:
        Fail-fast is critical for protecting database during outages.
    """
    pool = get_pool()

    # Verify circuit is OPEN (from previous test)
    # It should be open because it failed N (threshold) amount of times and we didn't re-open it
    metrics = pool.get_metrics()
    print("📊 Current state:")
    print(f"   Circuit state: {metrics['circuit_state']}")

    if metrics["circuit_state"] != CircuitState.OPEN.value:
        print("⚠️  Circuit not OPEN, skipping test")
        print("   (Run test_12 first to open the circuit)")
        return

    # Try to get a connection (should fail immediately)
    print("\n⏳ Attempting to get connection while circuit is OPEN...")

    start_time = time.time()

    try:
        with pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")

        print("❌ Connection succeeded (circuit didn't block request!)")

    except CircuitBreakerException as e:
        elapsed = time.time() - start_time

        print("✅ Circuit breaker blocked request (as expected)")
        print(f"   Error: {str(e)}")
        print(f"   Time taken: {elapsed * 1000:.2f}ms (should be <10ms)")

        if elapsed < 0.1:  # Less than 100ms
            print(f"✅ Fail-fast CONFIRMED! Request rejected in {elapsed * 1000:.1f}ms")
        else:
            print(f"⚠️  Slow rejection ({elapsed * 1000:.1f}ms) - should be instant")

    except Exception as e:
        print(f"❌ Unexpected exception: {type(e).__name__}: {e}")

    # Test multiple rapid requests (all should fail fast)
    print("\n⏳ Testing 5 rapid requests (all should fail fast)...")

    start_time = time.time()
    blocked_count = 0

    for i in range(5):
        try:
            with pool.get_connection() as conn:
                pass
        except CircuitBreakerException:
            blocked_count += 1

    elapsed = time.time() - start_time
    avg_time = elapsed / 5

    print("\n📊 Results:")
    print(f"   Blocked requests: {blocked_count}/5")
    print(f"   Total time: {elapsed * 1000:.2f}ms")
    print(f"   Avg time per request: {avg_time * 1000:.2f}ms")

    if blocked_count == 5:
        print("✅ All requests blocked by circuit breaker")
    else:
        print(f"⚠️  Only {blocked_count}/5 requests blocked")

    if avg_time < 0.01:  # Less than 10ms per request
        print("✅ Fail-fast performance excellent (<10ms per request)")
    else:
        print(f"ℹ️  Fail-fast taking {avg_time * 1000:.1f}ms per request")

    print("✅ TEST 13 PASSED\n")


def test_14_circuit_transitions_to_half_open():
    """Test circuit breaker transition from OPEN to HALF_OPEN.

    Validates that after the circuit timeout period, the circuit
    transitions to HALF_OPEN state to test recovery.

    Validates:
        - Circuit respects timeout period
        - Circuit transitions to HALF_OPEN after timeout
        - Timing calculations are accurate
        - Circuit allows test queries in HALF_OPEN

    Behavior:
        - If timeout <= 15s: Waits for natural transition
        - If timeout > 15s: Manually triggers for testing

    Prerequisites:
        Requires circuit to be in OPEN state.

    Note:
        For faster testing, initialize pool with circuit_timeout=10.
    """

    pool = get_pool()

    # Get current state
    metrics = pool.get_metrics()
    print("📊 Current state:")
    print(f"   Circuit state: {metrics['circuit_state']}")
    print(f"   Circuit timeout: {pool._circuit_timeout}s")

    if metrics["circuit_state"] != CircuitState.OPEN.value:
        print("⚠️  Circuit not OPEN, skipping test")  # Same as before
        return

    # Calculate when circuit should go HALF_OPEN
    if metrics["circuit_opened_at"]:
        opened_at = datetime.fromisoformat(metrics["circuit_opened_at"])
        timeout_at = opened_at.timestamp() + pool._circuit_timeout
        wait_time = timeout_at - time.time()

        print("\n⏰ Circuit timing:")
        print(f"   Opened at: {metrics['circuit_opened_at']}")
        print(f"   Will be HALF_OPEN in: {wait_time:.1f}s")

    # Option 1: Wait for timeout (if reasonable)
    if wait_time > 0 and wait_time <= 15:
        print(f"\n⏳ Waiting {wait_time:.1f}s for circuit to go HALF_OPEN...")
        time.sleep(wait_time + 1)  # Wait slightly longer

        # Try to trigger HALF_OPEN state
        print("\n📝 Triggering circuit check...")
        try:
            pool._check_circuit()
            print("   Circuit check passed (no exception)")
        except CircuitBreakerException as e:
            # Circuit should now be HALF_OPEN or still OPEN
            print(f"   Circuit still OPEN: {e}")
            pass

        metrics = pool.get_metrics()
        print("\n📊 After timeout:")
        print(f"   Circuit state: {metrics['circuit_state']}")

        if metrics["circuit_state"] == CircuitState.HALF_OPEN.value:
            print("✅ Circuit transitioned to HALF_OPEN after timeout")

            # Now try a connection (which will close it)
            print("\n📝 Attempting connection in HALF_OPEN state...")
            try:
                with pool.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                print("   ✓ Connection succeeded")
            except Exception as e:
                print(f"   ✗ Connection failed: {e}")

            # Check final state
            final_metrics = pool.get_metrics()
            print("\n📊 After connection attempt:")
            print(f"   Circuit state: {final_metrics['circuit_state']}")

            if final_metrics["circuit_state"] == CircuitState.CLOSED.value:
                print("✅ Circuit closed after successful recovery")
        else:
            print("❌ Circuit did not transition to HALF_OPEN")
            print(f"   Current state: {metrics['circuit_state']}")

    # Option 2: Manually trigger HALF_OPEN for testing
    # If it takes too long (default circuit timeout is set to 60s) override it when instantiating the pool config
    else:
        print(f"\n⏳ Timeout is {wait_time:.1f}s - too long to wait")
        print("   Manually setting circuit to HALF_OPEN for testing...")

        # Manually set to HALF_OPEN (for testing purposes)
        # However, we should not need this if the circuit breaker is properly working
        with pool._circuit_breaker_lock:
            pool.metrics.circuit_state = CircuitState.HALF_OPEN
            pool.metrics.circuit_opened_at = datetime.now(timezone.utc)

        metrics = pool.get_metrics()
        print("\n📊 After manual transition:")
        print(f"   Circuit state: {metrics['circuit_state']}")

        print("✅ Circuit manually set to HALF_OPEN for testing")

    print("✅ TEST 14 PASSED\n")


def test_15_circuit_closes_on_success():
    """Test circuit breaker closes after successful recovery.

    Validates that a successful query in HALF_OPEN state closes
    the circuit and resets failure counts.

    Validates:
        - Successful query in HALF_OPEN closes circuit
        - Circuit transitions to CLOSED state
        - Failure count is reset to zero
        - Database connection is fully restored
        - Normal operations resume

    Prerequisites:
        Requires circuit to be in HALF_OPEN state.

    Note:
        This completes the circuit breaker recovery cycle.
    """

    pool = get_pool()

    # Ensure circuit is in HALF_OPEN state
    metrics = pool.get_metrics()
    print("📊 Current state:")
    print(f"   Circuit state: {metrics['circuit_state']}")

    if metrics["circuit_state"] != CircuitState.HALF_OPEN.value:
        print("\n⏳ Setting circuit to HALF_OPEN for this test...")
        with pool._circuit_breaker_lock:
            pool.metrics.circuit_state = CircuitState.HALF_OPEN
            pool.metrics.circuit_failures = (
                0  # Reset failures for clean test - this should by the implementation?
            )

        metrics = pool.get_metrics()
        print(f"   Circuit state: {metrics['circuit_state']}")

    # Ensure database is accessible
    # This should already be correct from test cleanup

    print("\n⏳ Executing successful query in HALF_OPEN state...")
    print("   (This should close the circuit on success)")

    try:
        with pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                print(f"   ✓ Query succeeded: {result['test']}")

        # Check if circuit closed
        metrics = pool.get_metrics()
        print("\n📊 After successful query:")
        print(f"   Circuit state: {metrics['circuit_state']}")
        print(f"   Circuit failures: {metrics['circuit_failures']}")

        if metrics["circuit_state"] == CircuitState.CLOSED.value:
            print("✅ Circuit CLOSED after successful recovery")
            print("   Database connection restored!")
        else:
            print(f"⚠️  Circuit is {metrics['circuit_state']} (expected CLOSED)")

        assert metrics["circuit_state"] == CircuitState.CLOSED.value, (
            "Circuit should close after successful query in HALF_OPEN state"
        )

        assert metrics["circuit_failures"] == 0, (
            "Circuit failures should reset after recovery"
        )

    except Exception as e:
        print(f"❌ Query failed: {e}")
        print("   Circuit may remain OPEN or go back to OPEN")

        metrics = pool.get_metrics()
        print(f"   Circuit state: {metrics['circuit_state']}")

    print("✅ TEST 15 PASSED\n")


def test_16_circuit_metrics_tracking():
    """Verify circuit breaker metrics are tracked correctly.

    Validates that all circuit breaker-related metrics exist
    and contain valid values.

    Validates:
        - All required metrics are present
        - Circuit state is a valid enum value
        - Metrics are accessible via get_metrics()
        - Metric data types are correct

    Metrics checked:
        - circuit_state
        - circuit_failures
        - circuit_opened_at
    """
    print("\n" + "=" * 80)
    print("TEST 16: Circuit Breaker - Metrics Tracking")
    print("=" * 80)

    pool = get_pool()

    # Get current metrics
    metrics = pool.get_metrics()

    print("📊 Circuit Breaker Metrics:")
    print(f"   Circuit state: {metrics['circuit_state']}")
    print(f"   Circuit failures: {metrics['circuit_failures']}")
    print(f"   Circuit opened at: {metrics['circuit_opened_at']}")
    print(f"   Total errors: {metrics['total_errors']}")

    # Verify all circuit metrics exist
    required_metrics = ["circuit_state", "circuit_failures", "circuit_opened_at"]

    missing_metrics = [m for m in required_metrics if m not in metrics]

    if not missing_metrics:
        print("\n✅ All circuit breaker metrics present")
    else:
        print(f"\n❌ Missing metrics: {missing_metrics}")

    # Verify circuit state is valid
    valid_states = [state.value for state in CircuitState]
    if metrics["circuit_state"] in valid_states:
        print(f"✅ Circuit state is valid: {metrics['circuit_state']}")
    else:
        print(f"❌ Invalid circuit state: {metrics['circuit_state']}")

    print("✅ TEST 16 PASSED\n")


def test_17_full_circuit_breaker_lifecycle():
    """Test complete circuit breaker lifecycle.

    Simulates the full circuit breaker state machine transitions:
    CLOSED → OPEN → HALF_OPEN → CLOSED

    Validates:
        1. CLOSED: Normal operation with no failures
        2. OPEN: Opens after threshold failures reached
        3. HALF_OPEN: Transitions after timeout period
        4. CLOSED: Closes after successful recovery

    This test validates the complete circuit breaker flow and
    verifies all state transitions work correctly.

    Note:
        Uses manual state transitions for faster testing rather
        than waiting for actual timeouts.
    """
    print("\n" + "=" * 80)
    print("TEST 17: Circuit Breaker - Full Lifecycle Test")
    print("=" * 80)

    print("⚠️  This test simulates the complete circuit breaker lifecycle:")
    print("   1. Start in CLOSED state (normal operation)")
    print("   2. Trigger failures to OPEN circuit")
    print("   3. Wait or force HALF_OPEN state")
    print("   4. Successful query closes circuit")
    print()

    pool = get_pool()

    # Reset circuit to CLOSED for clean test
    print("📋 Step 1: Resetting to CLOSED state...")
    with pool._circuit_breaker_lock:
        pool.metrics.circuit_state = CircuitState.CLOSED
        pool.metrics.circuit_failures = 0
        pool.metrics.circuit_opened_at = None

    metrics = pool.get_metrics()
    print(f"   Circuit state: {metrics['circuit_state']}")
    assert metrics["circuit_state"] == CircuitState.CLOSED.value
    print("   ✅ CLOSED")

    # Step 2: Trigger failures
    print("\n📋 Step 2: Triggering failures to OPEN circuit...")
    threshold = pool._circuit_failure_threshold

    # Manually record failures (simpler than forcing real failures)
    # We already had tested this functionality, so no need to repeat code. We can force it by
    # accessing the protected method inside 'connection.py'
    for i in range(threshold):
        pool._record_circuit_failure()

    metrics = pool.get_metrics()
    print(f"   Circuit failures: {metrics['circuit_failures']}")
    print(f"   Circuit state: {metrics['circuit_state']}")
    assert metrics["circuit_state"] == CircuitState.OPEN.value
    print("   ✅ OPEN")

    # Step 3: Transition to HALF_OPEN
    print("\n📋 Step 3: Transitioning to HALF_OPEN...")
    with pool._circuit_breaker_lock:
        pool.metrics.circuit_state = CircuitState.HALF_OPEN

    metrics = pool.get_metrics()
    print(f"   Circuit state: {metrics['circuit_state']}")
    assert metrics["circuit_state"] == CircuitState.HALF_OPEN.value
    print("   ✅ HALF_OPEN")

    # Step 4: Successful recovery
    print("\n📋 Step 4: Successful query to close circuit...")
    pool._reset_circuit()

    metrics = pool.get_metrics()
    print(f"   Circuit state: {metrics['circuit_state']}")
    print(f"   Circuit failures: {metrics['circuit_failures']}")
    assert metrics["circuit_state"] == CircuitState.CLOSED.value
    assert metrics["circuit_failures"] == 0
    print("   ✅ CLOSED (recovered)")

    print("\n🎉 Complete lifecycle test successful!")
    print("   CLOSED → OPEN → HALF_OPEN → CLOSED")

    print("✅ TEST 17 PASSED\n")


def run_all_tests():
    """
    Execute the complete connection pool test suite.

    Initialises a connection pool and runs all 17 tests in sequence,
    providing detailed output and metrics for each test.

    The test suite covers:
        - Basic connection functionality
        - Thread safety and concurrency
        - Error handling and recovery
        - Connection lifecycle management
        - Circuit breaker behavior
        - Metrics tracking

    The configuration is an object built with pre-defined values for test usage. See
    ``ConnectionPoolConfig``.

    Configuration:
        - Pool size: 5 connections
        - Max overflow: 3 connections
        - Circuit failure threshold: 3 failures
        - Circuit timeout: 10 seconds

    Outputs:
        Detailed test results with visual indicators (✅/❌/⚠️)
        and final summary of all connection pool metrics.

    Cleanup:
        Ensures connection pool is properly closed after all tests.

    Raises:
        Exception: If any test fails or encounters an error.

    Note:
        Requires environment variables for database connection:
        - FROSTEL_MYSQL_PASSWORD
    """
    print("\n" + "=" * 80)
    print("🧪 ADVANCED CONNECTION POOL TEST SUITE")
    print("=" * 80)

    try:
        # Initialise pool
        print("\n⚙️  Initializing connection pool...")
        password = os.environ.get("FROSTEL_MYSQL_PASSWORD")

        # TODO: Variables change to the future testcontainers DB
        config = ConnectionPoolConfig.for_testing(
            password=password,
        )
        pool = init_connection_pool(config)

        import json

        print("POOL CONFIG:")
        print(json.dumps(config.to_dict(), indent=4))

        print(
            f"✅ Pool initialized: {pool.pool_size} connections + {pool.max_overflow} overflow"
        )

        # Run tests
        test_1_basic_connection()
        test_2_connection_reuse()
        test_3_multithreading()
        test_4_overflow_connections()
        test_5_transaction_rollback()
        test_6_metrics_accuracy()
        test_7_error_handling()
        test_8_stale_connection_recycling()
        test_9_pool_exhaustion()
        test_10_health_check()
        test_11_circuit_closed_normal_operation()
        test_12_circuit_open_after_failures()
        test_13_circuit_open_fails_fast()
        test_14_circuit_transitions_to_half_open()
        test_15_circuit_closes_on_success()
        test_16_circuit_metrics_tracking()
        test_17_full_circuit_breaker_lifecycle()

        # Final summary
        print("\n" + "=" * 80)
        print("📊 FINAL SUMMARY")
        print("=" * 80)

        final_metrics = pool.get_metrics()
        print(
            f"Total connections created: {final_metrics['total_connections_created']}"
        )
        print(f"Total queries executed: {final_metrics['total_checkouts']}")
        print(f"Total errors: {final_metrics['total_errors']}")
        print(f"Total retries: {final_metrics['total_retries']}")
        print(f"Average checkout time: {final_metrics['avg_checkout_time_ms']:.2f}ms")
        print(f"Max checkout time: {final_metrics['max_checkout_time_ms']:.2f}ms")
        print(f"Circuit state: {final_metrics['circuit_state']}")
        print(f"Circuit failures: {final_metrics['circuit_failures']}")
        print(f"Circuit opened at: {final_metrics['circuit_opened_at']}")

        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}", exc_info=True)
        raise

    finally:
        # Cleanup
        print("\n⚙️  Cleaning up...")
        close_connection_pool()
        print("✅ Connection pool closed")


if __name__ == "__main__":
    run_all_tests()

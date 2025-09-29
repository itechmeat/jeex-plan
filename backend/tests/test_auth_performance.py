"""
Authentication performance and load testing.
"""

import asyncio
import time
import uuid
from statistics import mean, median
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class PerformanceMetrics:
    """Helper class to collect and analyze performance metrics."""

    def __init__(self):
        self.response_times: list[float] = []
        self.status_codes: list[int] = []
        self.errors: list[str] = []
        self.start_time: float = 0
        self.end_time: float = 0

    def start_test(self):
        """Mark the start of a performance test."""
        self.start_time = time.time()

    def end_test(self):
        """Mark the end of a performance test."""
        self.end_time = time.time()

    def record_response(
        self, response_time: float, status_code: int, error: str = None
    ):
        """Record a single response metric."""
        self.response_times.append(response_time)
        self.status_codes.append(status_code)
        if error:
            self.errors.append(error)

    def get_summary(self) -> dict[str, Any]:
        """Get performance test summary."""
        total_time = self.end_time - self.start_time
        total_requests = len(self.response_times)

        return {
            "total_requests": total_requests,
            "total_time": total_time,
            "requests_per_second": total_requests / total_time if total_time > 0 else 0,
            "avg_response_time": mean(self.response_times)
            if self.response_times
            else 0,
            "median_response_time": median(self.response_times)
            if self.response_times
            else 0,
            "min_response_time": min(self.response_times) if self.response_times else 0,
            "max_response_time": max(self.response_times) if self.response_times else 0,
            "p95_response_time": self._percentile(self.response_times, 95)
            if self.response_times
            else 0,
            "p99_response_time": self._percentile(self.response_times, 99)
            if self.response_times
            else 0,
            "success_rate": self._calculate_success_rate(),
            "error_count": len(self.errors),
            "status_code_distribution": self._get_status_distribution(),
        }

    def _percentile(self, data: list[float], percentile: int) -> float:
        """Calculate percentile of response times."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _calculate_success_rate(self) -> float:
        """Calculate success rate (2xx status codes)."""
        if not self.status_codes:
            return 0
        success_count = sum(1 for code in self.status_codes if 200 <= code < 300)
        return success_count / len(self.status_codes)

    def _get_status_distribution(self) -> dict[int, int]:
        """Get distribution of status codes."""
        distribution = {}
        for code in self.status_codes:
            distribution[code] = distribution.get(code, 0) + 1
        return distribution


class TestAuthenticationPerformance:
    """Test authentication endpoint performance under load."""

    @pytest.mark.asyncio
    async def test_login_endpoint_response_time(self, async_client: AsyncClient):
        """Test login endpoint response time under normal load."""
        metrics = PerformanceMetrics()
        metrics.start_test()

        # Test with 10 sequential requests
        for i in range(10):
            start_time = time.time()
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": f"test{i}@example.com", "password": "password123"},
            )
            end_time = time.time()

            metrics.record_response(
                response_time=end_time - start_time, status_code=response.status_code
            )

        metrics.end_test()
        summary = metrics.get_summary()

        # Performance assertions
        assert summary["avg_response_time"] < 2.0, (
            f"Average response time too high: {summary['avg_response_time']}s"
        )
        assert summary["p95_response_time"] < 5.0, (
            f"95th percentile too high: {summary['p95_response_time']}s"
        )
        assert summary["max_response_time"] < 10.0, (
            f"Max response time too high: {summary['max_response_time']}s"
        )

        print(f"Login Performance Summary: {summary}")

    @pytest.mark.asyncio
    async def test_registration_endpoint_response_time(self, async_client: AsyncClient):
        """Test registration endpoint response time."""
        metrics = PerformanceMetrics()
        metrics.start_test()

        # Test with 5 registration requests (more expensive operation)
        for i in range(5):
            start_time = time.time()
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"perf_test_{uuid.uuid4().hex[:8]}@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "name": f"Performance Test User {i}",
                },
            )
            end_time = time.time()

            metrics.record_response(
                response_time=end_time - start_time, status_code=response.status_code
            )

        metrics.end_test()
        summary = metrics.get_summary()

        # Registration is more expensive, so allow higher response times
        assert summary["avg_response_time"] < 5.0, (
            f"Average registration time too high: {summary['avg_response_time']}s"
        )
        assert summary["p95_response_time"] < 10.0, (
            f"95th percentile too high: {summary['p95_response_time']}s"
        )

        print(f"Registration Performance Summary: {summary}")

    @pytest.mark.asyncio
    async def test_concurrent_authentication_requests(self, async_client: AsyncClient):
        """Test authentication performance with concurrent requests."""
        metrics = PerformanceMetrics()

        async def authenticate_user(user_id: int):
            """Single authentication request."""
            start_time = time.time()
            try:
                response = await async_client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": f"concurrent_test_{user_id}@example.com",
                        "password": "password123",
                    },
                )
                end_time = time.time()
                metrics.record_response(
                    response_time=end_time - start_time,
                    status_code=response.status_code,
                )
            except Exception as e:
                end_time = time.time()
                metrics.record_response(
                    response_time=end_time - start_time, status_code=500, error=str(e)
                )

        metrics.start_test()

        # Run 20 concurrent authentication requests
        tasks = [authenticate_user(i) for i in range(20)]
        await asyncio.gather(*tasks, return_exceptions=True)

        metrics.end_test()
        summary = metrics.get_summary()

        # Concurrent requests should maintain reasonable performance
        assert summary["avg_response_time"] < 3.0, (
            f"Concurrent avg response time too high: {summary['avg_response_time']}s"
        )
        assert summary["requests_per_second"] > 5, (
            f"Too few requests per second: {summary['requests_per_second']}"
        )
        assert summary["error_count"] < 5, f"Too many errors: {summary['error_count']}"

        print(f"Concurrent Authentication Performance: {summary}")

    @pytest.mark.asyncio
    async def test_token_validation_performance(self, async_client: AsyncClient):
        """Test token validation endpoint performance."""
        metrics = PerformanceMetrics()
        metrics.start_test()

        # Test token validation with invalid tokens (should be fast)
        for i in range(20):
            start_time = time.time()
            response = await async_client.post(
                "/api/v1/auth/validate-token",
                headers={"Authorization": f"Bearer fake_token_{i}"},
            )
            end_time = time.time()

            metrics.record_response(
                response_time=end_time - start_time, status_code=response.status_code
            )

        metrics.end_test()
        summary = metrics.get_summary()

        # Token validation should be very fast
        assert summary["avg_response_time"] < 0.5, (
            f"Token validation too slow: {summary['avg_response_time']}s"
        )
        assert summary["p95_response_time"] < 1.0, (
            f"Token validation p95 too high: {summary['p95_response_time']}s"
        )

        print(f"Token Validation Performance: {summary}")

    @pytest.mark.asyncio
    async def test_password_hashing_performance(self, test_session: AsyncSession):
        """Test password hashing performance."""
        from app.core.password_service import PasswordService

        password_service = PasswordService()
        metrics = PerformanceMetrics()
        metrics.start_test()

        # Test password hashing (expensive operation)
        for i in range(10):
            start_time = time.time()
            try:
                password = f"password123_{i}"
                hashed = password_service.get_password_hash(password)
                end_time = time.time()
                metrics.record_response(
                    response_time=end_time - start_time,
                    status_code=200,  # Success
                )
                assert hashed != password  # Should be hashed
                assert hashed is not None
                # Verify hash can be verified
                assert password_service.verify_password(password, hashed)
            except Exception as e:
                end_time = time.time()
                metrics.record_response(
                    response_time=end_time - start_time, status_code=500, error=str(e)
                )

        metrics.end_test()
        summary = metrics.get_summary()

        # Password hashing should be reasonably fast but secure
        assert summary["avg_response_time"] < 2.0, (
            f"Password hashing too slow: {summary['avg_response_time']}s"
        )
        assert summary["error_count"] == 0, (
            f"Password hashing errors: {summary['error_count']}"
        )

        print(f"Password Hashing Performance: {summary}")


class TestLoadTesting:
    """Load testing for authentication endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.slow  # Mark as slow test
    async def test_sustained_load_authentication(self, async_client: AsyncClient):
        """Test authentication under sustained load."""
        metrics = PerformanceMetrics()

        async def continuous_auth_load(duration_seconds: int = 30):
            """Generate continuous authentication load."""
            end_time = time.time() + duration_seconds
            request_count = 0

            while time.time() < end_time:
                start_time = time.time()
                try:
                    response = await async_client.post(
                        "/api/v1/auth/login",
                        json={
                            "email": f"load_test_{request_count}@example.com",
                            "password": "password123",
                        },
                    )
                    response_time = time.time() - start_time
                    metrics.record_response(
                        response_time=response_time, status_code=response.status_code
                    )
                except Exception as e:
                    response_time = time.time() - start_time
                    metrics.record_response(
                        response_time=response_time, status_code=500, error=str(e)
                    )

                request_count += 1
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.1)

        metrics.start_test()

        # Run sustained load for 10 seconds (reduced for testing)
        await continuous_auth_load(duration_seconds=10)

        metrics.end_test()
        summary = metrics.get_summary()

        # Under sustained load, should maintain reasonable performance
        assert summary["requests_per_second"] > 3, (
            f"Sustained load RPS too low: {summary['requests_per_second']}"
        )
        assert summary["avg_response_time"] < 5.0, (
            f"Sustained load avg response time too high: {summary['avg_response_time']}s"
        )
        assert summary["error_count"] < summary["total_requests"] * 0.1, (
            "Too many errors under load"
        )

        print(f"Sustained Load Performance: {summary}")

    @pytest.mark.asyncio
    async def test_burst_load_handling(self, async_client: AsyncClient):
        """Test handling of sudden burst of requests."""
        metrics = PerformanceMetrics()

        async def burst_request():
            """Single burst request."""
            start_time = time.time()
            try:
                response = await async_client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": f"burst_{uuid.uuid4().hex[:8]}@example.com",
                        "password": "password123",
                    },
                )
                end_time = time.time()
                metrics.record_response(
                    response_time=end_time - start_time,
                    status_code=response.status_code,
                )
            except Exception as e:
                end_time = time.time()
                metrics.record_response(
                    response_time=end_time - start_time, status_code=500, error=str(e)
                )

        metrics.start_test()

        # Create sudden burst of 50 concurrent requests
        tasks = [burst_request() for _ in range(50)]
        await asyncio.gather(*tasks, return_exceptions=True)

        metrics.end_test()
        summary = metrics.get_summary()

        # Should handle burst load gracefully
        assert summary["error_count"] < summary["total_requests"] * 0.2, (
            "Too many errors in burst"
        )
        assert summary["avg_response_time"] < 10.0, (
            f"Burst avg response time too high: {summary['avg_response_time']}s"
        )

        print(f"Burst Load Performance: {summary}")


class TestResourceUsage:
    """Test resource usage patterns during authentication."""

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, async_client: AsyncClient):
        """Test memory usage patterns during authentication load."""
        import os

        import psutil

        # Get current process
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate load
        for i in range(100):
            await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": f"memory_test_{i}@example.com",
                    "password": "password123",
                },
            )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory usage should not increase dramatically
        assert memory_increase < 100, (
            f"Memory usage increased too much: {memory_increase}MB"
        )

        print(
            f"Memory usage: Initial={initial_memory:.2f}MB, Final={final_memory:.2f}MB, Increase={memory_increase:.2f}MB"
        )

    @pytest.mark.asyncio
    async def test_database_connection_efficiency(self, async_client: AsyncClient):
        """Test that database connections are used efficiently."""
        # This test ensures that authentication doesn't exhaust DB connections

        # Make many concurrent requests that would require DB access
        async def db_intensive_request(request_id: int):
            try:
                response = await async_client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": f"db_test_{request_id}_{uuid.uuid4().hex[:6]}@example.com",
                        "password": "password123",
                        "confirm_password": "password123",
                        "name": f"DB Test User {request_id}",
                    },
                )
                return response
            except Exception as e:
                # Return a mock response object for failed requests
                class MockResponse:
                    def __init__(self, status_code: int, error: str):
                        self.status_code = status_code
                        self.error = error

                return MockResponse(500, str(e))

        # Run 10 concurrent DB-intensive operations (reduced to prevent overwhelming)
        tasks = [db_intensive_request(i) for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Should complete without connection pool exhaustion
        successful_responses = 0
        server_errors = 0
        connection_errors = 0

        for response in responses:
            if isinstance(response, Exception):
                connection_errors += 1
            elif hasattr(response, "status_code"):
                if 200 <= response.status_code < 300:
                    successful_responses += 1
                elif response.status_code in [500, 503]:
                    server_errors += 1

        # At least half should succeed or fail gracefully (not all connection errors)
        assert connection_errors < len(responses) * 0.5, (
            f"Too many connection errors: {connection_errors}/{len(responses)}"
        )

        # Should have some successful responses or graceful failures
        assert (successful_responses + server_errors) > 0, (
            "All requests failed - possible connection pool exhaustion"
        )

        print(
            f"DB Connection Test: {successful_responses} successful, {server_errors} server errors, {connection_errors} connection errors out of {len(responses)} total"
        )


class TestPerformanceRegression:
    """Test for performance regressions."""

    @pytest.mark.asyncio
    async def test_baseline_performance_metrics(self, async_client: AsyncClient):
        """Establish baseline performance metrics for regression testing."""
        # This test establishes performance baselines that can be used
        # to detect regressions in future versions

        baseline_metrics = {}

        # Test login performance
        login_metrics = PerformanceMetrics()
        login_metrics.start_test()

        for i in range(10):
            start_time = time.time()
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": f"baseline_login_{i}@example.com",
                    "password": "password123",
                },
            )
            end_time = time.time()
            login_metrics.record_response(end_time - start_time, response.status_code)

        login_metrics.end_test()
        baseline_metrics["login"] = login_metrics.get_summary()

        # Test registration performance
        reg_metrics = PerformanceMetrics()
        reg_metrics.start_test()

        for i in range(5):
            start_time = time.time()
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"baseline_reg_{uuid.uuid4().hex[:8]}@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "name": f"Baseline User {i}",
                },
            )
            end_time = time.time()
            reg_metrics.record_response(end_time - start_time, response.status_code)

        reg_metrics.end_test()
        baseline_metrics["registration"] = reg_metrics.get_summary()

        # Store baseline metrics (in real implementation, would save to file/DB)
        print("Baseline Performance Metrics:")
        for endpoint, metrics in baseline_metrics.items():
            print(
                f"{endpoint}: avg={metrics['avg_response_time']:.3f}s, p95={metrics['p95_response_time']:.3f}s"
            )

        # Basic performance assertions
        assert baseline_metrics["login"]["avg_response_time"] < 2.0
        assert baseline_metrics["registration"]["avg_response_time"] < 5.0

    @pytest.mark.asyncio
    async def test_performance_under_different_loads(self, async_client: AsyncClient):
        """Test performance characteristics under different load patterns."""
        load_patterns = [
            {"name": "light_load", "concurrent_users": 5, "requests_per_user": 5},
            {"name": "medium_load", "concurrent_users": 10, "requests_per_user": 10},
            {"name": "heavy_load", "concurrent_users": 20, "requests_per_user": 5},
        ]

        results = {}

        for pattern in load_patterns:
            metrics = PerformanceMetrics()

            async def user_simulation(user_id: int, requests: int):
                """Simulate a user making multiple requests."""
                for req_id in range(requests):
                    start_time = time.time()
                    try:
                        response = await async_client.post(
                            "/api/v1/auth/login",
                            json={
                                "email": f"load_{pattern['name']}_user_{user_id}_req_{req_id}@example.com",
                                "password": "password123",
                            },
                        )
                        end_time = time.time()
                        metrics.record_response(
                            end_time - start_time, response.status_code
                        )
                    except Exception as e:
                        end_time = time.time()
                        metrics.record_response(end_time - start_time, 500, str(e))

                    # Small delay between requests from same user
                    await asyncio.sleep(0.1)

            metrics.start_test()

            # Run concurrent user simulations
            tasks = [
                user_simulation(user_id, pattern["requests_per_user"])
                for user_id in range(pattern["concurrent_users"])
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_test()
            results[pattern["name"]] = metrics.get_summary()

        # Analyze performance under different loads
        for pattern_name, summary in results.items():
            print(f"Load Pattern {pattern_name}: {summary}")

            # Performance should degrade gracefully under load
            if pattern_name == "heavy_load":
                assert summary["avg_response_time"] < 10.0, (
                    f"Heavy load response time too high: {summary['avg_response_time']}s"
                )
            else:
                assert summary["avg_response_time"] < 5.0, (
                    f"{pattern_name} response time too high: {summary['avg_response_time']}s"
                )

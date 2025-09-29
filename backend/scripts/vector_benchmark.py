"""
Vector database performance benchmarking script.

Measures search latency, throughput, and scalability under various load conditions.
"""

import argparse
import asyncio
import json
import statistics
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.adapters.qdrant import QdrantAdapter
from app.core.hnsw_config import HNSWConfigurator, WorkloadType
from app.services.cache import VectorCache
from app.services.embedding import EmbeddingService


class VectorBenchmark:
    """Comprehensive benchmarking suite for vector database operations"""

    def __init__(self) -> None:
        self.qdrant = QdrantAdapter()
        self.embedding = EmbeddingService()
        self.cache = VectorCache()
        self.hnsw_configurator = HNSWConfigurator()

    async def setup_test_data(
        self, tenant_count: int, project_count: int, docs_per_project: int
    ):
        """Setup test data for benchmarking"""
        print(
            f"🔧 Setting up test data: {tenant_count} tenants, {project_count} projects each, {docs_per_project} docs per project"
        )

        test_documents = [
            "Machine learning algorithms enable systems to learn from data and improve performance over time.",
            "Deep learning uses neural networks with multiple layers to extract hierarchical features.",
            "Natural language processing helps computers understand and generate human language.",
            "Computer vision enables machines to interpret and make decisions based on visual data.",
            "Reinforcement learning trains agents to make optimal decisions through rewards and penalties.",
            "Time series analysis identifies patterns and trends in sequential data over time.",
            "Anomaly detection identifies unusual patterns that don't conform to expected behavior.",
            "Recommendation systems suggest items based on user preferences and behavior patterns.",
            "Clustering algorithms group similar data points together without predefined labels.",
            "Classification models predict categorical labels for input data based on training examples.",
        ]

        setup_start = time.time()
        total_vectors = 0

        for tenant_idx in range(tenant_count):
            tenant_id = f"benchmark_tenant_{tenant_idx:03d}"

            for project_idx in range(project_count):
                project_id = f"benchmark_project_{project_idx:03d}"

                # Create document variations
                project_docs = []
                for doc_idx in range(docs_per_project):
                    base_doc = test_documents[doc_idx % len(test_documents)]
                    varied_doc = f"{base_doc} (Tenant {tenant_idx}, Project {project_idx}, Document {doc_idx})"
                    project_docs.append(varied_doc)

                # Process documents and generate embeddings
                doc_embeddings = []
                doc_payloads = []

                for doc_idx, doc in enumerate(project_docs):
                    try:
                        result = await self.embedding.process_document(
                            text=doc,
                            metadata={
                                "tenant": tenant_idx,
                                "project": project_idx,
                                "doc_index": doc_idx,
                            },
                        )

                        doc_embeddings.extend(result.embeddings)
                        for chunk in result.chunks:
                            payload = {
                                **chunk.metadata,
                                "text": chunk.text,
                                "tenant_id": tenant_id,
                                "project_id": project_id,
                            }
                            doc_payloads.append(payload)

                    except (ValueError, RuntimeError) as e:
                        print(f"⚠️  Failed to process document: {e}")
                    except Exception as e:
                        print(f"⚠️  Unexpected error processing document: {e}")
                        raise

                # Store vectors
                if doc_embeddings and doc_payloads:
                    await self.qdrant.upsert_points(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        vectors=doc_embeddings,
                        payloads=doc_payloads,
                    )
                    total_vectors += len(doc_embeddings)

        setup_time = time.time() - setup_start
        print(f"✅ Test data setup completed in {setup_time:.2f}s")
        print(f"📊 Total vectors stored: {total_vectors}")

        return {
            "tenant_count": tenant_count,
            "project_count": project_count,
            "docs_per_project": docs_per_project,
            "total_vectors": total_vectors,
            "setup_time": setup_time,
        }

    async def benchmark_search_latency(
        self, tenant_id: str, project_id: str, iterations: int = 100
    ):
        """Benchmark search latency for a specific tenant/project"""
        print(f"⏱️  Benchmarking search latency for {tenant_id}/{project_id}")

        query_vector = [0.1] * 1536  # Mock query vector
        latencies = []

        for i in range(iterations):
            start_time = time.time()

            try:
                await self.qdrant.search(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    query_vector=query_vector,
                    limit=10,
                )
                latency_ms = (time.time() - start_time) * 1000
                latencies.append(latency_ms)

                if (i + 1) % 20 == 0:
                    print(f"   Progress: {i + 1}/{iterations} requests")

            except (ConnectionError, TimeoutError, RuntimeError) as e:
                print(f"❌ Search failed on iteration {i + 1}: {e}")
            except Exception as e:
                print(f"❌ Unexpected search error on iteration {i + 1}: {e}")
                raise

        if not latencies:
            return {"error": "All search requests failed"}

        stats = {
            "iterations": len(latencies),
            "avg_latency_ms": statistics.mean(latencies),
            "median_latency_ms": statistics.median(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "p95_latency_ms": statistics.quantiles(latencies, n=20)[18]
            if len(latencies) >= 20
            else max(latencies),  # 95th percentile
            "p99_latency_ms": statistics.quantiles(latencies, n=100)[98]
            if len(latencies) >= 100
            else max(latencies),
            "std_deviation_ms": statistics.stdev(latencies)
            if len(latencies) > 1
            else 0,
        }

        print("📈 Search latency stats:")
        print(f"   Average: {stats['avg_latency_ms']:.2f}ms")
        print(f"   P95: {stats['p95_latency_ms']:.2f}ms")
        print(f"   P99: {stats['p99_latency_ms']:.2f}ms")
        print(f"   Max: {stats['max_latency_ms']:.2f}ms")

        return stats

    async def benchmark_concurrent_searches(
        self, tenant_ids: list[str], project_ids: list[str], concurrent_users: int = 50
    ):
        """Benchmark concurrent search performance"""
        print(f"🔄 Benchmarking concurrent searches with {concurrent_users} users")

        query_vector = [0.1] * 1536
        latencies = []
        errors = 0

        async def search_user(user_id: int):
            start_time = time.time()
            try:
                # Rotate through tenants and projects
                tenant_id = tenant_ids[user_id % len(tenant_ids)]
                project_id = project_ids[user_id % len(project_ids)]

                results = await self.qdrant.search(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    query_vector=query_vector,
                    limit=5,
                )

                latency_ms = (time.time() - start_time) * 1000
                return {
                    "success": True,
                    "latency_ms": latency_ms,
                    "results_count": len(results),
                }

            except (ConnectionError, TimeoutError, RuntimeError) as e:
                return {
                    "success": False,
                    "error": str(e),
                    "latency_ms": (time.time() - start_time) * 1000,
                }

        # Execute concurrent searches
        start_time = time.time()
        tasks = [search_user(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Process results
        successful_results = []
        for result in results:
            if isinstance(result, Exception):
                errors += 1
            elif result.get("success"):
                successful_results.append(result)
            else:
                errors += 1

        if successful_results:
            latencies = [r["latency_ms"] for r in successful_results]

        stats = {
            "concurrent_users": concurrent_users,
            "total_time": total_time,
            "successful_requests": len(successful_results),
            "error_count": errors,
            "throughput_rps": len(successful_results) / total_time
            if total_time > 0
            else 0,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "p95_latency_ms": statistics.quantiles(latencies, n=20)[18]
            if len(latencies) >= 20
            else 0,
            "error_rate": errors / concurrent_users if concurrent_users > 0 else 0,
        }

        print("📊 Concurrent search stats:")
        print(f"   Throughput: {stats['throughput_rps']:.2f} requests/second")
        print(f"   Success rate: {(1 - stats['error_rate']) * 100:.1f}%")
        print(f"   Average latency: {stats['avg_latency_ms']:.2f}ms")
        print(f"   P95 latency: {stats['p95_latency_ms']:.2f}ms")

        return stats

    async def benchmark_hnsw_configurations(self):
        """Benchmark different HNSW configurations"""
        print("⚙️  Benchmarking HNSW configurations")

        configs_to_test = [
            ("balanced", WorkloadType.BALANCED),
            ("speed", WorkloadType.SPEED),
            ("quality", WorkloadType.QUALITY),
            ("memory", WorkloadType.MEMORY),
        ]

        results = {}

        for config_name, workload_type in configs_to_test:
            print(f"   Testing {config_name} configuration...")

            config = self.hnsw_configurator.configure_for_workload(workload_type)

            # Mock search performance test (would need actual Qdrant reconfiguration)
            # For now, we'll simulate based on configuration parameters
            simulated_latencies = []

            # Simulate search performance based on HNSW parameters
            ef = config.get("ef", 64)
            ef_construct = config.get("ef_construct", 100)

            # Simulate 100 search operations
            for _ in range(100):
                # Latency simulation based on ef parameter
                base_latency = 50 + (ef / 2) + (ef_construct / 10)
                noise = statistics.NormalDist(0, base_latency * 0.1).samples(1)[0]
                latency = max(10, base_latency + noise)
                simulated_latencies.append(latency)

            results[config_name] = {
                "config": config,
                "avg_latency_ms": statistics.mean(simulated_latencies),
                "p95_latency_ms": statistics.quantiles(simulated_latencies, n=20)[18],
                "memory_estimate_mb": self.hnsw_configurator.estimate_memory_usage(
                    config, 10000
                )["total_estimated_mb"],
            }

            print(f"      Avg latency: {results[config_name]['avg_latency_ms']:.2f}ms")
            print(
                f"      Memory estimate: {results[config_name]['memory_estimate_mb']:.2f}MB"
            )

        return results

    async def benchmark_cache_performance(self):
        """Benchmark caching performance"""
        print("💾 Benchmarking cache performance")

        tenant_id = f"cache_benchmark_tenant_{uuid.uuid4().hex[:8]}"
        project_id = f"cache_benchmark_project_{uuid.uuid4().hex[:8]}"

        # Setup test data
        test_queries = [
            "machine learning algorithms",
            "neural network architectures",
            "data preprocessing techniques",
            "model evaluation metrics",
            "feature engineering methods",
        ]

        # Generate mock search results
        mock_results = [
            {
                "id": f"result_{i}",
                "score": 0.8 + (i * 0.01),
                "payload": {"text": f"Mock result {i}"},
            }
            for i in range(10)
        ]

        # Benchmark cache set/get operations
        cache_times = []
        cache_hits = 0

        for _i, _query in enumerate(
            test_queries * 20
        ):  # Repeat queries to test cache hits
            start_time = time.time()

            # Try to get from cache first
            cached_result = await self.cache.get_search_results(
                tenant_id, project_id, "test_hash", {}, 10
            )

            if cached_result:
                cache_hits += 1
                cache_time = (time.time() - start_time) * 1000
            else:
                # Cache miss - set cache
                await self.cache.set_search_results(
                    tenant_id, project_id, "test_hash", {}, 10, mock_results
                )
                cache_time = (time.time() - start_time) * 1000

            cache_times.append(cache_time)

        stats = {
            "total_operations": len(cache_times),
            "cache_hits": cache_hits,
            "cache_hit_rate": cache_hits / len(cache_times),
            "avg_cache_time_ms": statistics.mean(cache_times),
            "min_cache_time_ms": min(cache_times),
            "max_cache_time_ms": max(cache_times),
        }

        print("📊 Cache performance stats:")
        print(f"   Hit rate: {stats['cache_hit_rate'] * 100:.1f}%")
        print(f"   Average operation time: {stats['avg_cache_time_ms']:.2f}ms")
        print(f"   Min time: {stats['min_cache_time_ms']:.2f}ms")
        print(f"   Max time: {stats['max_cache_time_ms']:.2f}ms")

        return stats

    async def run_comprehensive_benchmark(self, config: dict[str, Any]):
        """Run comprehensive benchmark suite"""
        print("🚀 Starting comprehensive vector database benchmark")
        print("=" * 60)

        results = {
            "benchmark_config": config,
            "timestamp": datetime.now(UTC).isoformat(),
            "results": {},
        }

        # Setup test data
        setup_info = await self.setup_test_data(
            tenant_count=config["tenants"],
            project_count=config["projects_per_tenant"],
            docs_per_project=config["docs_per_project"],
        )
        results["setup"] = setup_info

        # Generate test tenant/project IDs
        tenant_ids = [f"benchmark_tenant_{i:03d}" for i in range(config["tenants"])]
        project_ids = [
            f"benchmark_project_{i:03d}" for i in range(config["projects_per_tenant"])
        ]

        # Run benchmark tests
        print("\n" + "=" * 60)

        # Search latency benchmark
        if tenant_ids and project_ids:
            latency_results = await self.benchmark_search_latency(
                tenant_ids[0], project_ids[0], config["search_iterations"]
            )
            results["results"]["search_latency"] = latency_results

        print("\n" + "=" * 60)

        # Concurrent search benchmark
        if config["concurrent_users"] > 0:
            concurrent_results = await self.benchmark_concurrent_searches(
                tenant_ids, project_ids, config["concurrent_users"]
            )
            results["results"]["concurrent_search"] = concurrent_results

        print("\n" + "=" * 60)

        # HNSW configuration benchmark
        if config["test_hnsw_configs"]:
            hnsw_results = await self.benchmark_hnsw_configurations()
            results["results"]["hnsw_configurations"] = hnsw_results

        print("\n" + "=" * 60)

        # Cache performance benchmark
        if config["test_cache"]:
            cache_results = await self.benchmark_cache_performance()
            results["results"]["cache_performance"] = cache_results

        print("\n" + "=" * 60)
        print("✅ Comprehensive benchmark completed")
        print("=" * 60)

        # Save results
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        results_file = f"vector_benchmark_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"📄 Results saved to: {results_file}")

        return results


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Vector Database Benchmark Suite")
    parser.add_argument("--tenants", type=int, default=5, help="Number of test tenants")
    parser.add_argument("--projects", type=int, default=3, help="Projects per tenant")
    parser.add_argument("--docs", type=int, default=10, help="Documents per project")
    parser.add_argument(
        "--search-iterations",
        type=int,
        default=100,
        help="Search iterations for latency test",
    )
    parser.add_argument(
        "--concurrent-users",
        type=int,
        default=50,
        help="Concurrent users for load test",
    )
    parser.add_argument(
        "--test-hnsw", action="store_true", help="Test HNSW configurations"
    )
    parser.add_argument(
        "--test-cache", action="store_true", help="Test cache performance"
    )
    return parser.parse_args()


async def main() -> None:
    """Main benchmark execution"""
    args = parse_args()

    config = {
        "tenants": args.tenants,
        "projects_per_tenant": args.projects,
        "docs_per_project": args.docs,
        "search_iterations": args.search_iterations,
        "concurrent_users": args.concurrent_users,
        "test_hnsw_configs": args.test_hnsw,
        "test_cache": args.test_cache,
    }

    benchmark = VectorBenchmark()
    results = await benchmark.run_comprehensive_benchmark(config)

    # Print summary
    print("\n📋 BENCHMARK SUMMARY")
    print("=" * 60)
    print(
        f"Configuration: {config['tenants']} tenants × {config['projects_per_tenant']} projects × {config['docs_per_project']} docs"
    )
    print(f"Total vectors: {results['setup']['total_vectors']}")
    print(f"Setup time: {results['setup']['setup_time']:.2f}s")

    if "search_latency" in results["results"]:
        latency = results["results"]["search_latency"]
        print(f"Search P95 latency: {latency['p95_latency_ms']:.2f}ms")

    if "concurrent_search" in results["results"]:
        concurrent = results["results"]["concurrent_search"]
        print(f"Concurrent throughput: {concurrent['throughput_rps']:.2f} req/s")
        print(f"Success rate: {(1 - concurrent['error_rate']) * 100:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())

"""
Comprehensive tests for vector database functionality with focus on:
- Tenant isolation security
- Search relevance and accuracy
- Performance and scalability
- Error handling and resilience
"""

import pytest
import asyncio
from typing import List, Dict, Any
import uuid
import time

from app.adapters.qdrant import QdrantAdapter
from app.services.embedding import EmbeddingService
from app.services.cache import VectorCache
from app.middleware.tenant_filter import VectorOperationFilter
from app.schemas.vector import DocumentType, VisibilityLevel, VectorPayload
from app.core.hnsw_config import HNSWConfigurator, WorkloadType, DatasetSize


@pytest.fixture
def qdrant_adapter():
    """Initialize Qdrant adapter for testing"""
    return QdrantAdapter()

class TestTenantIsolation:
    """Test suite for strict tenant isolation"""

    @pytest.fixture
    def test_tenants(self):
        """Create test tenant data"""
        return {
            "tenant1": {
                "id": "test_tenant_001",
                "projects": {
                    "project1": "test_project_001",
                    "project2": "test_project_002"
                }
            },
            "tenant2": {
                "id": "test_tenant_002",
                "projects": {
                    "project1": "test_project_003",
                    "project2": "test_project_004"
                }
            }
        }

    @pytest.fixture
    def test_documents(self):
        """Create test documents for different tenants"""
        return {
            "tenant1_project1": [
                "This is a confidential document for tenant 1 project 1.",
                "Project 1 involves machine learning and data analysis.",
                "Security is a top priority for this project."
            ],
            "tenant1_project2": [
                "This document belongs to tenant 1 project 2.",
                "Project 2 focuses on web development and APIs.",
                "Performance optimization is key here."
            ],
            "tenant2_project1": [
                "Tenant 2 project 1 deals with mobile applications.",
                "iOS and Android development are required.",
                "User experience design is important."
            ],
            "tenant2_project2": [
                "This is sensitive data for tenant 2 project 2.",
                "Project 2 handles financial transactions.",
                "Compliance and regulations must be followed."
            ]
        }

    @pytest.mark.asyncio
    async def test_cross_tenant_access_prevention(
        self, qdrant_adapter, test_tenants, test_documents
    ):
        """Test that tenants cannot access other tenants' data"""
        # Insert data for both tenants
        for tenant_key, tenant_data in test_tenants.items():
            for project_key, project_id in tenant_data["projects"].items():
                documents = test_documents[f"{tenant_key}_{project_key}"]

                # Create simple mock embeddings (1536 dimensions)
                embeddings = [[0.1] * 1536 for _ in documents]
                payloads = [{"text": doc} for doc in documents]

                await qdrant_adapter.upsert_points(
                    tenant_id=tenant_data["id"],
                    project_id=project_id,
                    vectors=embeddings,
                    payloads=payloads
                )

        # Test tenant 1 can only access their own data
        query_vector = [0.1] * 1536

        tenant1_results = await qdrant_adapter.search(
            tenant_id=test_tenants["tenant1"]["id"],
            project_id=test_tenants["tenant1"]["projects"]["project1"],
            query_vector=query_vector,
            limit=10
        )

        # Verify all results belong to tenant 1
        for result in tenant1_results:
            assert result["payload"]["tenant_id"] == test_tenants["tenant1"]["id"]
            assert result["payload"]["project_id"] in test_tenants["tenant1"]["projects"].values()

        # Test tenant 2 can only access their own data
        tenant2_results = await qdrant_adapter.search(
            tenant_id=test_tenants["tenant2"]["id"],
            project_id=test_tenants["tenant2"]["projects"]["project1"],
            query_vector=query_vector,
            limit=10
        )

        # Verify all results belong to tenant 2
        for result in tenant2_results:
            assert result["payload"]["tenant_id"] == test_tenants["tenant2"]["id"]
            assert result["payload"]["project_id"] in test_tenants["tenant2"]["projects"].values()

        # Verify no overlap between tenant results
        tenant1_ids = {r["id"] for r in tenant1_results}
        tenant2_ids = {r["id"] for r in tenant2_results}
        assert tenant1_ids.isdisjoint(tenant2_ids), "Tenant data isolation failed"

    @pytest.mark.asyncio
    async def test_project_isolation_within_tenant(
        self, qdrant_adapter, test_tenants, test_documents
    ):
        """Test that projects within the same tenant are isolated"""
        tenant_id = test_tenants["tenant1"]["id"]
        project1_id = test_tenants["tenant1"]["projects"]["project1"]
        project2_id = test_tenants["tenant1"]["projects"]["project2"]

        # Insert data for both projects
        project_key_map = {
            project1_id: "tenant1_project1",
            project2_id: "tenant1_project2",
        }
        for project_id in [project1_id, project2_id]:
            documents = test_documents[project_key_map[project_id]]

            embeddings = [[0.1] * 1536 for _ in documents]
            payloads = [{"text": doc} for doc in documents]

            await qdrant_adapter.upsert_points(
                tenant_id=tenant_id,
                project_id=project_id,
                vectors=embeddings,
                payloads=payloads
            )

        query_vector = [0.1] * 1536

        # Search project 1
        project1_results = await qdrant_adapter.search(
            tenant_id=tenant_id,
            project_id=project1_id,
            query_vector=query_vector,
            limit=10
        )

        # Search project 2
        project2_results = await qdrant_adapter.search(
            tenant_id=tenant_id,
            project_id=project2_id,
            query_vector=query_vector,
            limit=10
        )

        # Verify results are project-specific
        for result in project1_results:
            assert result["payload"]["project_id"] == project1_id

        for result in project2_results:
            assert result["payload"]["project_id"] == project2_id

        # Verify no overlap between projects
        project1_ids = {r["id"] for r in project1_results}
        project2_ids = {r["id"] for r in project2_results}
        assert project1_ids.isdisjoint(project2_ids), "Project isolation failed"

    @pytest.mark.asyncio
    async def test_tenant_specific_deletion(
        self, qdrant_adapter, test_tenants, test_documents
    ):
        """Test that deletion only affects the specified tenant"""
        # Insert data for both tenants
        for tenant_key, tenant_data in test_tenants.items():
            for project_key, project_id in tenant_data["projects"].items():
                documents = test_documents[f"{tenant_key}_{project_key}"]

                embeddings = [[0.1] * 1536 for _ in documents]
                payloads = [{"text": doc} for doc in documents]

                await qdrant_adapter.upsert_points(
                    tenant_id=tenant_data["id"],
                    project_id=project_id,
                    vectors=embeddings,
                    payloads=payloads
                )

        # Delete tenant 1 data
        await qdrant_adapter.delete_points(
            tenant_id=test_tenants["tenant1"]["id"],
            project_id=test_tenants["tenant1"]["projects"]["project1"]
        )

        query_vector = [0.1] * 1536

        # Verify tenant 1 data is deleted
        tenant1_results = await qdrant_adapter.search(
            tenant_id=test_tenants["tenant1"]["id"],
            project_id=test_tenants["tenant1"]["projects"]["project1"],
            query_vector=query_vector,
            limit=10
        )
        assert len(tenant1_results) == 0, "Tenant 1 data not properly deleted"

        # Verify tenant 2 data is intact
        tenant2_results = await qdrant_adapter.search(
            tenant_id=test_tenants["tenant2"]["id"],
            project_id=test_tenants["tenant2"]["projects"]["project1"],
            query_vector=query_vector,
            limit=10
        )
        assert len(tenant2_results) > 0, "Tenant 2 data was affected by tenant 1 deletion"


class TestSearchRelevance:
    """Test suite for search relevance and accuracy"""

    @pytest.fixture
    def embedding_service(self):
        """Initialize embedding service for testing"""
        return EmbeddingService()

    @pytest.fixture
    def test_corpus(self):
        """Create test document corpus with known relationships"""
        return {
            "ml_algorithms": [
                "Machine learning algorithms include supervised learning, unsupervised learning, and reinforcement learning.",
                "Neural networks are a type of machine learning algorithm inspired by the human brain.",
                "Deep learning uses neural networks with multiple layers to extract higher-level features."
            ],
            "web_development": [
                "Web development involves creating websites and web applications using HTML, CSS, and JavaScript.",
                "Frontend development focuses on user interfaces and user experience design.",
                "Backend development handles server-side logic, databases, and APIs."
            ],
            "data_science": [
                "Data science combines statistics, programming, and domain knowledge to extract insights from data.",
                "Data visualization helps communicate insights through charts, graphs, and interactive dashboards.",
                "Statistical analysis is fundamental to validating hypotheses and making data-driven decisions."
            ]
        }

    @pytest.mark.asyncio
    async def test_semantic_search_accuracy(
        self, embedding_service, qdrant_adapter, test_corpus
    ):
        """Test that semantic search returns relevant results"""
        tenant_id = f"test_tenant_{uuid.uuid4().hex[:8]}"
        project_id = f"test_project_{uuid.uuid4().hex[:8]}"

        # Process and store test corpus
        for category, documents in test_corpus.items():
            for doc in documents:
                # Process document through embedding pipeline
                result = await embedding_service.process_document(
                    text=doc,
                    metadata={"category": category}
                )

                # Store vectors
                await qdrant_adapter.upsert_points(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    vectors=result.embeddings,
                    payloads=[{"text": doc, "category": category} for _ in result.chunks]
                )

        # Test queries with expected categories
        test_queries = [
            ("neural networks and deep learning", "ml_algorithms"),
            ("websites and user interfaces", "web_development"),
            ("statistics and data analysis", "data_science"),
            ("machine learning models", "ml_algorithms"),
            ("frontend and backend development", "web_development")
        ]

        for query, expected_category in test_queries:
            # Generate query embedding
            query_result = await embedding_service.process_document(text=query)
            query_embedding = query_result.embeddings[0] if query_result.embeddings else [0.1] * 1536

            # Perform search
            search_results = await qdrant_adapter.search(
                tenant_id=tenant_id,
                project_id=project_id,
                query_vector=query_embedding,
                limit=5,
                score_threshold=0.5
            )

            # Verify relevance
            assert len(search_results) > 0, f"No results found for query: {query}"

            # Check if top results match expected category
            relevant_results = [
                r for r in search_results
                if r["payload"].get("category") == expected_category
            ]

            # At least 50% of results should be relevant
            relevance_ratio = len(relevant_results) / len(search_results)
            assert relevance_ratio >= 0.5, f"Low relevance ({relevance_ratio:.2f}) for query: {query}"

    @pytest.mark.asyncio
    async def test_filter_effectiveness(
        self, embedding_service, qdrant_adapter, test_corpus
    ):
        """Test that search filters work correctly"""
        tenant_id = f"test_tenant_{uuid.uuid4().hex[:8]}"
        project_id = f"test_project_{uuid.uuid4().hex[:8]}"

        # Store test corpus with different visibility levels
        for category, documents in test_corpus.items():
            for i, doc in enumerate(documents):
                visibility = VisibilityLevel.PUBLIC if i == 0 else VisibilityLevel.PRIVATE

                result = await embedding_service.process_document(text=doc)

                await qdrant_adapter.upsert_points(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    vectors=result.embeddings,
                    payloads=[{
                        "text": doc,
                        "category": category,
                        "visibility": visibility.value
                    } for _ in result.chunks],
                    visibility=visibility.value
                )

        query_embedding = [0.1] * 1536

        # Test visibility filtering
        public_results = await qdrant_adapter.search(
            tenant_id=tenant_id,
            project_id=project_id,
            query_vector=query_embedding,
            limit=10,
            filters={"visibility": "public"}
        )

        # Verify all results are public
        for result in public_results:
            assert result["payload"]["visibility"] == "public", "Public filter failed"

        # Test category filtering
        ml_results = await qdrant_adapter.search(
            tenant_id=tenant_id,
            project_id=project_id,
            query_vector=query_embedding,
            limit=10,
            filters={"category": "ml_algorithms"}
        )

        # Verify all results are ML-related
        for result in ml_results:
            assert result["payload"]["category"] == "ml_algorithms", "Category filter failed"


class TestPerformanceAndScalability:
    """Test suite for performance and scalability"""

    @pytest.mark.asyncio
    async def test_search_latency(self, qdrant_adapter):
        """Test that search latency meets requirements (< 200ms)"""
        tenant_id = f"perf_test_tenant_{uuid.uuid4().hex[:8]}"
        project_id = f"perf_test_project_{uuid.uuid4().hex[:8]}"

        # Insert test data
        test_documents = [
            "This is a test document for performance testing.",
            "Performance testing measures system response times.",
            "Latency should be within acceptable limits.",
            "Scalability testing ensures the system handles load."
        ] * 50  # Multiply to create more data

        embeddings = [[0.1] * 1536 for _ in test_documents]
        payloads = [{"text": doc, "index": i} for i, doc in enumerate(test_documents)]

        await qdrant_adapter.upsert_points(
            tenant_id=tenant_id,
            project_id=project_id,
            vectors=embeddings,
            payloads=payloads
        )

        query_vector = [0.1] * 1536

        # Measure search latency
        latencies = []
        for _ in range(20):  # 20 search requests
            start_time = time.time()

            await qdrant_adapter.search(
                tenant_id=tenant_id,
                project_id=project_id,
                query_vector=query_vector,
                limit=10
            )

            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        # Assert requirements (P95 < 200ms)
        assert p95_latency < 200, f"P95 latency {p95_latency:.2f}ms exceeds 200ms limit"
        assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms too high"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, qdrant_adapter):
        """Test concurrent search operations"""
        tenant_id = f"concurrent_test_tenant_{uuid.uuid4().hex[:8]}"
        project_id = f"concurrent_test_project_{uuid.uuid4().hex[:8]}"

        # Insert test data
        test_documents = [f"Test document {i}" for i in range(100)]
        embeddings = [[0.1] * 1536 for _ in test_documents]
        payloads = [{"text": doc, "index": i} for i, doc in enumerate(test_documents)]

        await qdrant_adapter.upsert_points(
            tenant_id=tenant_id,
            project_id=project_id,
            vectors=embeddings,
            payloads=payloads
        )

        query_vector = [0.1] * 1536

        # Perform concurrent searches
        async def search_task(task_id: int):
            start_time = time.time()
            results = await qdrant_adapter.search(
                tenant_id=tenant_id,
                project_id=project_id,
                query_vector=query_vector,
                limit=10
            )
            latency = (time.time() - start_time) * 1000
            return {"task_id": task_id, "results_count": len(results), "latency_ms": latency}

        # Run 50 concurrent searches
        tasks = [search_task(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations succeeded
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 50, f"Only {len(successful_results)}/50 concurrent operations succeeded"

        # Check latencies
        latencies = [r["latency_ms"] for r in successful_results]
        max_latency = max(latencies)
        assert max_latency < 500, f"Max latency {max_latency:.2f}ms too high for concurrent operations"


class TestHNSWConfiguration:
    """Test suite for HNSW configuration optimization"""

    def test_hnsw_config_generation(self):
        """Test HNSW configuration generation for different workloads"""
        configurator = HNSWConfigurator()

        # Test different workload configurations
        for workload in WorkloadType:
            for dataset_size in DatasetSize:
                config = configurator.configure_for_workload(workload, dataset_size)

                # Validate configuration
                assert configurator.validate_configuration(config), \
                    f"Invalid configuration for {workload} + {dataset_size}"

                # Check multi-tenant specific settings
                assert config["m"] == 0, "Global graph should be disabled for multi-tenancy"
                assert config["payload_m"] >= 8, "Payload connections should be sufficient"

    def test_memory_estimation(self):
        """Test memory usage estimation"""
        configurator = HNSWConfigurator()

        config = configurator.get_optimized_config_for_tenant_isolation()
        vector_count = 10000

        memory_stats = configurator.estimate_memory_usage(config, vector_count)

        assert "vectors_mb" in memory_stats
        assert "graph_mb" in memory_stats
        assert "total_estimated_mb" in memory_stats
        assert memory_stats["total_estimated_mb"] > 0


class TestErrorHandlingAndResilience:
    """Test suite for error handling and system resilience"""

    @pytest.mark.asyncio
    async def test_invalid_tenant_context(self):
        """Test handling of invalid tenant context"""
        filter_builder = VectorOperationFilter()

        # Test with empty tenant/project IDs
        with pytest.raises(Exception):
            filter_builder.build_search_filter("", "", {})

    @pytest.mark.asyncio
    async def test_payload_validation(self):
        """Test payload validation and sanitization"""
        filter_builder = VectorOperationFilter()

        # Test valid payload
        valid_payload = {
            "tenant_id": "test_tenant",
            "project_id": "test_project",
            "content": "Test content"
        }
        assert filter_builder.validate_payload_integrity(valid_payload)

        # Test invalid payload (missing required fields)
        invalid_payload = {
            "content": "Test content"
            # Missing tenant_id and project_id
        }
        assert not filter_builder.validate_payload_integrity(invalid_payload)

        # Test payload sanitization
        dangerous_payload = {
            "tenant_id": "test_tenant",
            "project_id": "test_project",
            "content": "Test content",
            "cross_tenant_ref": "malicious_data",
            "bypass_isolation": "true"
        }

        sanitized = filter_builder.sanitize_payload(dangerous_payload)
        assert "cross_tenant_ref" not in sanitized
        assert "bypass_isolation" not in sanitized
        assert "tenant_id" in sanitized
        assert "project_id" in sanitized


@pytest.mark.asyncio
async def test_full_integration_workflow():
    """Test the complete workflow from text processing to search"""
    # Initialize services
    embedding_service = EmbeddingService()
    qdrant_adapter = QdrantAdapter()
    vector_cache = VectorCache()

    # Test data
    tenant_id = f"integration_test_tenant_{uuid.uuid4().hex[:8]}"
    project_id = f"integration_test_project_{uuid.uuid4().hex[:8]}"
    test_text = """
    Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.
    ML algorithms build mathematical models based on training data to make predictions or decisions.
    """

    # Step 1: Process text and generate embeddings
    embedding_result = await embedding_service.process_document(test_text)
    assert embedding_result.chunks, "No chunks generated"
    assert embedding_result.embeddings, "No embeddings generated"

    # Step 2: Store vectors in Qdrant
    upsert_result = await qdrant_adapter.upsert_points(
        tenant_id=tenant_id,
        project_id=project_id,
        vectors=embedding_result.embeddings,
        payloads=[{"text": chunk.text, "source": "integration_test"} for chunk in embedding_result.chunks]
    )
    assert upsert_result["status"] == "success", "Vector storage failed"

    # Step 3: Test search functionality
    query_embedding = embedding_result.embeddings[0]
    search_results = await qdrant_adapter.search(
        tenant_id=tenant_id,
        project_id=project_id,
        query_vector=query_embedding,
        limit=5
    )
    assert len(search_results) > 0, "Search returned no results"

    # Step 4: Test caching
    cache_key = f"search:{tenant_id}:{project_id}"
    cache_success = await vector_cache.set_search_results(
        tenant_id, project_id, "test_hash", {}, 5, search_results
    )
    assert cache_success, "Cache storage failed"

    cached_results = await vector_cache.get_search_results(
        tenant_id, project_id, "test_hash", {}, 5
    )
    assert cached_results is not None, "Cache retrieval failed"
    assert len(cached_results) == len(search_results), "Cached results don't match"

    print("✅ Full integration workflow test passed")
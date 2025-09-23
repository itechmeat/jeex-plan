"""
HNSW configuration optimizer for multi-tenant Qdrant collections.
Provides specialized configurations for different use cases and workloads.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class WorkloadType(str, Enum):
    """Types of workload patterns for HNSW optimization"""
    BALANCED = "balanced"          # General purpose - good search quality and speed
    SPEED = "speed"                 # Fast search, moderate recall
    QUALITY = "quality"             # High recall, slower search
    MEMORY = "memory"               # Memory efficient for large datasets


class DatasetSize(str, Enum):
    """Dataset size categories for configuration tuning"""
    SMALL = "small"                 # < 10K vectors
    MEDIUM = "medium"               # 10K - 100K vectors
    LARGE = "large"                 # 100K - 1M vectors
    EXTRA_LARGE = "extra_large"     # > 1M vectors


@dataclass
class HNSWParams:
    """HNSW parameters optimized for multi-tenancy"""
    m: int                           # Number of bi-directional links
    ef_construct: int                # Size of dynamic candidate list during construction
    ef: int                         # Size of dynamic candidate list during search
    max_indexing_threads: int       # Number of threads for indexing
    full_scan_threshold: int         # Threshold for switching to full scan
    payload_m: Optional[int] = None  # Payload-specific connections for multi-tenancy


class HNSWConfigurator:
    """Configures HNSW parameters for multi-tenant workloads"""

    # Multi-tenant optimized base configurations
    MULTI_TENANT_BASE = {
        "m": 0,  # Disable global graph for multi-tenancy
        "payload_m": 16,  # Create payload-specific connections
        "max_indexing_threads": 0,  # Use all available threads
        "full_scan_threshold": 10000,
    }

    # Workload-specific configurations
    WORKLOAD_CONFIGS = {
        WorkloadType.BALANCED: {
            "ef_construct": 100,
            "ef": 64,
        },
        WorkloadType.SPEED: {
            "ef_construct": 64,
            "ef": 32,
        },
        WorkloadType.QUALITY: {
            "ef_construct": 200,
            "ef": 128,
        },
        WorkloadType.MEMORY: {
            "ef_construct": 80,
            "ef": 40,
        }
    }

    # Dataset size adjustments
    SIZE_ADJUSTMENTS = {
        DatasetSize.SMALL: {
            "full_scan_threshold": 1000,
            "ef_construct_multiplier": 0.8,
        },
        DatasetSize.MEDIUM: {
            "full_scan_threshold": 5000,
            "ef_construct_multiplier": 1.0,
        },
        DatasetSize.LARGE: {
            "full_scan_threshold": 20000,
            "ef_construct_multiplier": 1.2,
        },
        DatasetSize.EXTRA_LARGE: {
            "full_scan_threshold": 50000,
            "ef_construct_multiplier": 1.5,
        }
    }

    def __init__(self):
        self.workload_type = WorkloadType.BALANCED
        self.dataset_size = DatasetSize.MEDIUM

    def configure_for_workload(
        self,
        workload_type: WorkloadType,
        dataset_size: DatasetSize = DatasetSize.MEDIUM,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate HNSW configuration for specific workload and dataset size.

        Args:
            workload_type: Type of workload pattern
            dataset_size: Expected dataset size category
            custom_params: Optional custom parameter overrides

        Returns:
            Complete HNSW configuration dictionary
        """
        self.workload_type = workload_type
        self.dataset_size = dataset_size

        # Start with multi-tenant base configuration
        config = self.MULTI_TENANT_BASE.copy()

        # Apply workload-specific settings
        workload_config = self.WORKLOAD_CONFIGS[workload_type].copy()
        size_adjustments = self.SIZE_ADJUSTMENTS[dataset_size]

        # Adjust ef_construct based on dataset size
        base_ef_construct = workload_config["ef_construct"]
        multiplier = size_adjustments["ef_construct_multiplier"]
        config["ef_construct"] = int(base_ef_construct * multiplier)

        # Apply other workload settings
        config["ef"] = workload_config["ef"]
        config["full_scan_threshold"] = size_adjustments["full_scan_threshold"]

        # Apply custom overrides
        if custom_params:
            config.update(custom_params)

        return config

    def get_optimized_config_for_tenant_isolation(self) -> Dict[str, Any]:
        """
        Get HNSW configuration optimized for strict tenant isolation.

        Returns:
            Configuration optimized for multi-tenant filtering
        """
        return self.configure_for_workload(
            workload_type=WorkloadType.BALANCED,
            dataset_size=DatasetSize.MEDIUM,
            custom_params={
                "m": 0,  # Critical: disable global graph
                "payload_m": 24,  # Increase payload connections for better isolation
                "ef_construct": 120,  # Slightly higher construction quality
                "ef": 80,  # Better search within tenant scope
            }
        )

    def get_memory_efficient_config(self) -> Dict[str, Any]:
        """
        Get memory-efficient configuration for large multi-tenant deployments.

        Returns:
            Configuration optimized for memory usage
        """
        return self.configure_for_workload(
            workload_type=WorkloadType.MEMORY,
            dataset_size=DatasetSize.LARGE,
            custom_params={
                "m": 0,
                "payload_m": 12,  # Reduce payload connections
                "ef_construct": 60,
                "ef": 32,
            }
        )

    def get_high_quality_config(self) -> Dict[str, Any]:
        """
        Get high-quality search configuration for critical applications.

        Returns:
            Configuration optimized for search quality
        """
        return self.configure_for_workload(
            workload_type=WorkloadType.QUALITY,
            dataset_size=DatasetSize.MEDIUM,
            custom_params={
                "m": 0,
                "payload_m": 20,
                "ef_construct": 200,
                "ef": 128,
            }
        )

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate HNSW configuration for multi-tenant compatibility.

        Args:
            config: HNSW configuration dictionary

        Returns:
            True if configuration is valid for multi-tenancy
        """
        required_params = ["m", "ef_construct", "ef", "payload_m"]

        for param in required_params:
            if param not in config:
                return False

        # Multi-tenant specific validations
        if config["m"] != 0:
            # Global graph should be disabled for multi-tenancy
            return False

        if config["payload_m"] < 8:
            # Payload connections should be sufficient for isolation
            return False

        if config["ef_construct"] < config["ef"]:
            # Construction ef should be >= search ef
            return False

        return True

    def estimate_memory_usage(self, config: Dict[str, Any], vector_count: int) -> Dict[str, float]:
        """
        Estimate memory usage for HNSW configuration.

        Args:
            config: HNSW configuration
            vector_count: Expected number of vectors

        Returns:
            Memory usage estimates in MB
        """
        # Base estimates (simplified)
        vector_size_mb = vector_count * 1536 * 4 / (1024 * 1024)  # 1536 dimensions, float32

        # Graph memory (very rough estimate)
        m = config.get("m", 16)
        payload_m = config.get("payload_m", 16)
        graph_connections = vector_count * (m + payload_m) * 8 / (1024 * 1024)  # 64-bit pointers

        # Index overhead
        index_overhead = vector_count * 0.1  # 10% overhead estimate

        return {
            "vectors_mb": vector_size_mb,
            "graph_mb": graph_connections,
            "index_overhead_mb": index_overhead,
            "total_estimated_mb": vector_size_mb + graph_connections + index_overhead
        }

    def get_configuration_summary(self, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Get human-readable summary of HNSW configuration.

        Args:
            config: HNSW configuration dictionary

        Returns:
            Configuration summary with descriptions
        """
        return {
            "global_graph": "Disabled (multi-tenant optimized)" if config.get("m") == 0 else f"Enabled (m={config.get('m')})",
            "payload_connections": f"m={config.get('payload_m')} connections",
            "construction_quality": f"ef_construct={config.get('ef_construct')}",
            "search_quality": f"ef={config.get('ef')}",
            "indexing_threads": "All available" if config.get("max_indexing_threads") == 0 else f"{config.get('max_indexing_threads')} threads",
            "full_scan_threshold": f"{config.get('full_scan_threshold')} vectors",
        }


# Singleton instance for application-wide use
hnsw_configurator = HNSWConfigurator()
"""
Object Storage Analysis utilities for Vultr Object Storage.

This module provides custom analysis functionality that is separate from
the core Vultr API implementation. It uses the Vultr API to gather data
but performs S3 configuration analysis and validation locally.
"""

from typing import Any


class ObjectStorageAnalyzer:
    """Custom object storage analysis functionality for Vultr object storage management."""

    def __init__(self, vultr_client):
        """Initialize with a Vultr object storage client."""
        self.vultr_client = vultr_client

    async def get_s3_config(self, object_storage_id: str) -> dict[str, Any]:
        """Get S3-compatible configuration details for an Object Storage instance.

        Args:
            object_storage_id: The Object Storage ID or label

        Returns:
            S3 configuration details including endpoint, credentials, and examples
        """
        try:
            # Get object storage details
            storage_info = await self.vultr_client.get_object_storage(object_storage_id)

            # Get cluster information for S3 endpoint
            cluster_id = storage_info.get("cluster_id")
            clusters = await self.vultr_client.list_clusters()
            cluster_info = next((c for c in clusters if c.get("id") == cluster_id), {})

            s3_config = {
                "storage_id": storage_info.get("id"),
                "label": storage_info.get("label"),
                "region": storage_info.get("region"),
                "status": storage_info.get("status"),
                "s3_credentials": {
                    "endpoint": f"https://{cluster_info.get('hostname', 'unknown-cluster')}",
                    "region": cluster_info.get("region", storage_info.get("region")),
                    "access_key": storage_info.get("s3_access_key"),
                    "secret_key": storage_info.get("s3_secret_key"),
                    "bucket_url_format": f"https://{cluster_info.get('hostname', 'unknown-cluster')}/{{bucket_name}}",
                },
                "configuration_examples": {
                    "aws_cli": {
                        "configure": f"aws configure set aws_access_key_id {storage_info.get('s3_access_key')}",
                        "endpoint": f"--endpoint-url https://{cluster_info.get('hostname', 'unknown-cluster')}",
                        "list_buckets": f"aws s3 ls --endpoint-url https://{cluster_info.get('hostname', 'unknown-cluster')}",
                        "create_bucket": f"aws s3 mb s3://my-bucket --endpoint-url https://{cluster_info.get('hostname', 'unknown-cluster')}",
                    },
                    "python_boto3": {
                        "import": "import boto3",
                        "client_setup": f"""
s3_client = boto3.client(
    's3',
    endpoint_url='https://{cluster_info.get("hostname", "unknown-cluster")}',
    aws_access_key_id='{storage_info.get("s3_access_key")}',
    aws_secret_access_key='{storage_info.get("s3_secret_key")}',
    region_name='{cluster_info.get("region", storage_info.get("region"))}'
)""",
                        "list_buckets": "response = s3_client.list_buckets()",
                        "upload_file": "s3_client.upload_file('local_file.txt', 'my-bucket', 'remote_file.txt')",
                    },
                    "nodejs": {
                        "install": "npm install aws-sdk",
                        "setup": f"""
const AWS = require('aws-sdk');
const s3 = new AWS.S3({{
    endpoint: 'https://{cluster_info.get("hostname", "unknown-cluster")}',
    accessKeyId: '{storage_info.get("s3_access_key")}',
    secretAccessKey: '{storage_info.get("s3_secret_key")}',
    region: '{cluster_info.get("region", storage_info.get("region"))}'
}});""",
                        "list_buckets": "s3.listBuckets((err, data) => { console.log(data.Buckets); });",
                    },
                },
                "cluster_info": {
                    "cluster_id": cluster_id,
                    "hostname": cluster_info.get("hostname"),
                    "region": cluster_info.get("region"),
                    "deployment_status": cluster_info.get("deploy"),
                },
                "usage_recommendations": [
                    "Use versioning for important data to protect against accidental deletion",
                    "Implement lifecycle policies to automatically delete old versions",
                    "Use multipart uploads for files larger than 100MB",
                    "Consider implementing client-side encryption for sensitive data",
                    "Monitor storage usage and costs regularly",
                ],
            }

            return s3_config

        except Exception as e:
            return {
                "object_storage_id": object_storage_id,
                "error": str(e),
                "recommendations": [
                    "Unable to generate S3 configuration - check if object storage exists"
                ],
            }

    async def validate_s3_access(self, object_storage_id: str) -> dict[str, Any]:
        """Validate that an Object Storage instance has valid S3 credentials.

        Args:
            object_storage_id: The Object Storage ID or label

        Returns:
            Validation results with configuration suggestions
        """
        try:
            # Get object storage details
            storage_info = await self.vultr_client.get_object_storage(object_storage_id)

            validation = {
                "storage_id": storage_info.get("id"),
                "label": storage_info.get("label"),
                "status": storage_info.get("status"),
                "validation_results": {
                    "credentials_present": False,
                    "endpoint_accessible": "unknown",
                    "configuration_valid": False,
                },
                "configuration_issues": [],
                "recommendations": [],
            }

            # Check if credentials are present
            access_key = storage_info.get("s3_access_key")
            secret_key = storage_info.get("s3_secret_key")

            if access_key and secret_key:
                validation["validation_results"]["credentials_present"] = True
            else:
                validation["configuration_issues"].append("Missing S3 credentials")
                validation["recommendations"].append(
                    "Regenerate S3 access keys if missing"
                )

            # Check storage status
            storage_status = storage_info.get("status", "").lower()
            if storage_status == "active":
                validation["validation_results"]["endpoint_accessible"] = "likely"
            elif storage_status in ["pending", "installing"]:
                validation["validation_results"]["endpoint_accessible"] = "not_ready"
                validation["configuration_issues"].append(
                    "Object storage is not yet active"
                )
                validation["recommendations"].append(
                    "Wait for object storage to finish provisioning"
                )
            else:
                validation["validation_results"]["endpoint_accessible"] = "unknown"
                validation["configuration_issues"].append(
                    f"Unexpected storage status: {storage_status}"
                )

            # Overall configuration assessment
            if (
                validation["validation_results"]["credentials_present"]
                and validation["validation_results"]["endpoint_accessible"] == "likely"
            ):
                validation["validation_results"]["configuration_valid"] = True
                validation["recommendations"].append(
                    "S3 configuration appears valid and ready to use"
                )
            else:
                validation["recommendations"].extend(
                    [
                        "Address configuration issues before attempting to use S3 API",
                        "Test connectivity with a simple operation like listing buckets",
                    ]
                )

            # Add general recommendations
            validation["recommendations"].extend(
                [
                    "Store credentials securely and never commit them to version control",
                    "Consider using IAM roles or temporary credentials for applications",
                    "Implement proper error handling for S3 operations in your applications",
                    "Monitor storage usage and set up billing alerts",
                ]
            )

            return validation

        except Exception as e:
            return {
                "object_storage_id": object_storage_id,
                "error": str(e),
                "recommendations": [
                    "Unable to validate S3 access - check if object storage exists"
                ],
            }

    async def get_storage_summary(self) -> dict[str, Any]:
        """Get a summary of all Object Storage instances.

        Returns:
            Summary information including total instances, regions, and status breakdown
        """
        try:
            # Get all object storage instances
            storage_instances = await self.vultr_client.list_object_storage()

            summary = {
                "total_instances": len(storage_instances),
                "regions": {},
                "status_breakdown": {},
                "cluster_usage": {},
                "total_storage_allocated": 0,
                "estimated_monthly_cost": 0.0,
                "recommendations": [],
            }

            # Analyze instances
            for instance in storage_instances:
                region = instance.get("region", "unknown")
                status = instance.get("status", "unknown")
                cluster_id = instance.get("cluster_id")

                # Count by region
                summary["regions"][region] = summary["regions"].get(region, 0) + 1

                # Count by status
                summary["status_breakdown"][status] = (
                    summary["status_breakdown"].get(status, 0) + 1
                )

                # Count by cluster
                if cluster_id:
                    summary["cluster_usage"][cluster_id] = (
                        summary["cluster_usage"].get(cluster_id, 0) + 1
                    )

                # Estimate costs (simplified - would need actual pricing)
                summary["estimated_monthly_cost"] += 5.0  # Basic estimate

            # Generate insights and recommendations
            summary["recommendations"] = self._generate_storage_recommendations(
                summary, storage_instances
            )

            return summary

        except Exception as e:
            return {
                "error": str(e),
                "recommendations": [
                    "Unable to generate storage summary - check account access"
                ],
            }

    async def find_by_region(self, region: str) -> dict[str, Any]:
        """Find all Object Storage instances in a specific region.

        Args:
            region: Region code to filter by

        Returns:
            List of Object Storage instances in the specified region with analysis
        """
        try:
            # Get all object storage instances
            all_storage = await self.vultr_client.list_object_storage()

            # Filter by region
            region_storage = [
                storage
                for storage in all_storage
                if storage.get("region", "").lower() == region.lower()
            ]

            analysis = {
                "region": region,
                "total_instances": len(region_storage),
                "instances": region_storage,
                "status_breakdown": {},
                "cluster_distribution": {},
                "regional_recommendations": [],
            }

            # Analyze regional distribution
            for storage in region_storage:
                status = storage.get("status", "unknown")
                cluster_id = storage.get("cluster_id")

                analysis["status_breakdown"][status] = (
                    analysis["status_breakdown"].get(status, 0) + 1
                )
                if cluster_id:
                    analysis["cluster_distribution"][cluster_id] = (
                        analysis["cluster_distribution"].get(cluster_id, 0) + 1
                    )

            # Generate regional recommendations
            if len(region_storage) == 0:
                analysis["regional_recommendations"].append(
                    f"No object storage instances found in {region}"
                )
            elif len(region_storage) == 1:
                analysis["regional_recommendations"].append(
                    "Single storage instance - consider redundancy for critical data"
                )
            else:
                analysis["regional_recommendations"].append(
                    f"Multiple storage instances in {region} - good for redundancy"
                )

            if len(analysis["cluster_distribution"]) > 1:
                analysis["regional_recommendations"].append(
                    "Using multiple clusters provides good availability"
                )

            return analysis

        except Exception as e:
            return {
                "region": region,
                "error": str(e),
                "recommendations": [f"Unable to analyze storage in region {region}"],
            }

    def _generate_storage_recommendations(
        self, summary: dict[str, Any], instances: list[dict[str, Any]]
    ) -> list[str]:
        """Generate recommendations based on storage usage analysis."""
        recommendations = []

        total_instances = summary["total_instances"]

        if total_instances == 0:
            recommendations.append(
                "No object storage instances found - consider creating storage for backup/archival needs"
            )
        elif total_instances == 1:
            recommendations.append(
                "Single storage instance - consider multi-region redundancy for critical data"
            )

        # Status analysis
        status_breakdown = summary["status_breakdown"]
        active_instances = status_breakdown.get("active", 0)

        if active_instances < total_instances:
            recommendations.append(
                "Some storage instances are not active - check provisioning status"
            )

        # Regional distribution analysis
        regions = summary["regions"]
        if len(regions) == 1:
            recommendations.append(
                "All storage in single region - consider multi-region setup for disaster recovery"
            )
        elif len(regions) > 3:
            recommendations.append(
                "Storage spread across many regions - verify this aligns with your data locality needs"
            )

        # Cluster usage analysis
        cluster_usage = summary["cluster_usage"]
        if len(cluster_usage) == 1:
            recommendations.append(
                "All storage using single cluster - consider multiple clusters for availability"
            )

        # Cost optimization
        estimated_cost = summary["estimated_monthly_cost"]
        if estimated_cost > 100:
            recommendations.append(
                "High storage costs - review usage patterns and consider lifecycle policies"
            )

        # General recommendations
        recommendations.extend(
            [
                "Regularly review and clean up unused buckets and objects",
                "Implement proper backup and versioning strategies",
                "Monitor storage usage trends and plan capacity accordingly",
                "Use appropriate storage classes for different access patterns",
            ]
        )

        return recommendations

    async def analyze_storage_optimization(
        self, object_storage_id: str
    ) -> dict[str, Any]:
        """Analyze storage configuration and provide optimization recommendations.

        Args:
            object_storage_id: The Object Storage ID or label

        Returns:
            Optimization analysis with cost and performance recommendations
        """
        try:
            # Get storage details
            storage_info = await self.vultr_client.get_object_storage(object_storage_id)

            optimization = {
                "storage_id": storage_info.get("id"),
                "label": storage_info.get("label"),
                "current_configuration": {
                    "region": storage_info.get("region"),
                    "cluster_id": storage_info.get("cluster_id"),
                    "status": storage_info.get("status"),
                },
                "optimization_opportunities": [],
                "cost_optimization": [],
                "performance_optimization": [],
                "security_recommendations": [],
            }

            # Analyze current configuration
            storage_info.get("region")
            status = storage_info.get("status")

            # Generate optimization opportunities
            if status == "active":
                optimization["optimization_opportunities"].extend(
                    [
                        "Storage is active and ready for optimization",
                        "Consider implementing lifecycle policies for cost savings",
                        "Review access patterns to optimize performance",
                    ]
                )
            else:
                optimization["optimization_opportunities"].append(
                    "Complete storage provisioning before optimization"
                )

            # Cost optimization recommendations
            optimization["cost_optimization"] = [
                "Implement lifecycle policies to automatically delete old versions",
                "Use appropriate storage classes for different access frequencies",
                "Monitor storage usage and set up billing alerts",
                "Clean up unused buckets and incomplete multipart uploads",
                "Consider compression for archival data",
            ]

            # Performance optimization recommendations
            optimization["performance_optimization"] = [
                "Use multipart uploads for files larger than 100MB",
                "Implement proper retry logic with exponential backoff",
                "Use parallel uploads/downloads for better throughput",
                "Consider using CloudFront or CDN for frequently accessed content",
                "Optimize bucket and object naming for better performance",
            ]

            # Security recommendations
            optimization["security_recommendations"] = [
                "Enable versioning for important buckets",
                "Implement bucket policies to control access",
                "Use IAM roles instead of hardcoded credentials",
                "Enable server-side encryption for sensitive data",
                "Regularly rotate access keys",
                "Monitor access logs for suspicious activity",
            ]

            return optimization

        except Exception as e:
            return {
                "object_storage_id": object_storage_id,
                "error": str(e),
                "recommendations": [
                    "Unable to analyze storage optimization - check storage access"
                ],
            }

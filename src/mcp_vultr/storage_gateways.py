"""
Vultr Storage Gateways FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr storage gateways.
Storage Gateways allow access to Vultr File System via the NFS v4.2 protocol.
"""

from typing import Any

from fastmcp import FastMCP


def create_storage_gateways_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr storage gateways management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with storage gateway management tools
    """
    mcp = FastMCP(name="vultr-storage-gateways")

    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    # Helper function to get storage gateway ID from label or ID
    async def get_storage_gateway_id(identifier: str) -> str:
        """
        Get the storage gateway ID from label or existing ID.

        Args:
            identifier: Storage gateway label or ID

        Returns:
            The storage gateway ID

        Raises:
            ValueError: If the storage gateway is not found
        """
        # If it looks like a UUID, return as-is
        if is_uuid_format(identifier):
            return identifier

        # Search by label
        gateways = await vultr_client.list_storage_gateways()
        for gateway in gateways:
            if gateway.get("label") == identifier:
                return gateway["id"]

        raise ValueError(f"Storage gateway '{identifier}' not found")

    # Storage Gateway resources
    @mcp.resource("storage-gateways://list")
    async def list_gateways_resource() -> list[dict[str, Any]]:
        """List all storage gateways."""
        try:
            return await vultr_client.list_storage_gateways()
        except Exception:
            # If the API returns an error when no storage gateways exist, return empty list
            return []

    @mcp.resource("storage-gateways://{gateway_identifier}")
    async def get_gateway_resource(gateway_identifier: str) -> dict[str, Any]:
        """Get details of a specific storage gateway.

        Args:
            gateway_identifier: The gateway label or ID
        """
        gateway_id = await get_storage_gateway_id(gateway_identifier)
        return await vultr_client.get_storage_gateway(gateway_id)

    @mcp.resource("storage-gateways://{gateway_identifier}/status")
    async def get_gateway_status_resource(gateway_identifier: str) -> dict[str, Any]:
        """Get comprehensive status of a storage gateway.

        Args:
            gateway_identifier: The gateway label or ID
        """
        await get_storage_gateway_id(gateway_identifier)
        return await get_gateway_status(gateway_identifier)

    # Storage Gateway management tools

    @mcp.tool
    async def create(
        label: str,
        gateway_type: str,
        region: str,
        export_config: dict[str, Any],
        network_config: dict[str, Any],
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new storage gateway.

        Args:
            label: Label for the storage gateway (for easy identification)
            gateway_type: Type of storage gateway (e.g., "nfs4")
            region: Region code where the gateway will be created (e.g., "ewr", "lax")
            export_config: Export configuration with keys:
                - label: Export label
                - vfs_uuid: VFS UUID to export
                - pseudo_root_path: Pseudo root path (e.g., "/")
                - allowed_ips: List of allowed IP addresses
            network_config: Network configuration with keys:
                - primary: Dict with ipv4_public_enabled, ipv6_public_enabled, vpc (optional)
            tags: Optional list of tags to apply

        Returns:
            Created storage gateway information
        """
        return await vultr_client.create_storage_gateway(
            label=label,
            gateway_type=gateway_type,
            region=region,
            export_config=export_config,
            network_config=network_config,
            tags=tags,
        )

    @mcp.tool
    async def update(
        gateway_identifier: str,
        label: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, str]:
        """Update storage gateway configuration.

        Smart identifier resolution: Use gateway label or ID.

        Args:
            gateway_identifier: Gateway label or ID to update
            label: New label for the gateway
            tags: New tags for the gateway

        Returns:
            Success confirmation
        """
        gateway_id = await get_storage_gateway_id(gateway_identifier)
        await vultr_client.update_storage_gateway(gateway_id, label, tags)

        changes = []
        if label is not None:
            changes.append(f"label to '{label}'")
        if tags is not None:
            changes.append(f"tags to {tags}")

        return {
            "success": True,
            "message": f"Gateway updated: {', '.join(changes) if changes else 'no changes'}",
            "gateway_id": gateway_id,
        }

    @mcp.tool
    async def delete(gateway_identifier: str) -> dict[str, str]:
        """Delete a storage gateway.

        Smart identifier resolution: Use gateway label or ID.

        Args:
            gateway_identifier: Gateway label or ID to delete

        Returns:
            Success confirmation
        """
        gateway_id = await get_storage_gateway_id(gateway_identifier)
        await vultr_client.delete_storage_gateway(gateway_id)
        return {
            "success": True,
            "message": "Storage gateway deleted successfully",
            "gateway_id": gateway_id,
        }

    @mcp.tool
    async def add_export(
        gateway_identifier: str, export_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Add a new export to a storage gateway.

        Smart identifier resolution: Use gateway label or ID.

        Args:
            gateway_identifier: Gateway label or ID
            export_config: Export configuration with keys:
                - label: Export label
                - vfs_uuid: VFS UUID to export
                - pseudo_root_path: Pseudo root path (e.g., "/")
                - allowed_ips: List of allowed IP addresses

        Returns:
            Created export information
        """
        gateway_id = await get_storage_gateway_id(gateway_identifier)
        return await vultr_client.add_storage_gateway_export(gateway_id, export_config)

    @mcp.tool
    async def delete_export(gateway_identifier: str, export_id: int) -> dict[str, str]:
        """Delete an export from a storage gateway.

        Smart identifier resolution: Use gateway label or ID.

        Args:
            gateway_identifier: Gateway label or ID
            export_id: Export ID to delete

        Returns:
            Success confirmation
        """
        gateway_id = await get_storage_gateway_id(gateway_identifier)
        await vultr_client.delete_storage_gateway_export(gateway_id, export_id)
        return {
            "success": True,
            "message": f"Export {export_id} deleted successfully",
            "gateway_id": gateway_id,
            "export_id": export_id,
        }

    @mcp.tool
    async def list_by_region(region: str) -> list[dict[str, Any]]:
        """List storage gateways in a specific region.

        Args:
            region: Region code to filter by (e.g., "ewr", "lax", "fra")

        Returns:
            List of gateways in the specified region
        """
        gateways = await vultr_client.list_storage_gateways()
        return [gateway for gateway in gateways if gateway.get("region") == region]

    @mcp.tool
    async def list_by_type(gateway_type: str) -> list[dict[str, Any]]:
        """List storage gateways by type.

        Args:
            gateway_type: Gateway type to filter by (e.g., "nfs4")

        Returns:
            List of gateways of the specified type
        """
        gateways = await vultr_client.list_storage_gateways()
        return [gateway for gateway in gateways if gateway.get("type") == gateway_type]

    @mcp.tool
    async def list_by_status(status: str) -> list[dict[str, Any]]:
        """List storage gateways by status.

        Args:
            status: Status to filter by (e.g., "active", "pending")

        Returns:
            List of gateways with the specified status
        """
        gateways = await vultr_client.list_storage_gateways()
        return [gateway for gateway in gateways if gateway.get("status") == status]

    @mcp.tool
    async def get_gateway_status(gateway_identifier: str) -> dict[str, Any]:
        """Get comprehensive status information for a storage gateway.

        Smart identifier resolution: Use gateway label or ID.

        Args:
            gateway_identifier: Gateway label or ID

        Returns:
            Detailed status including health, exports, and network configuration
        """
        gateway_id = await get_storage_gateway_id(gateway_identifier)
        gateway = await vultr_client.get_storage_gateway(gateway_id)

        # Enhanced status information
        status_info = {
            **gateway,
            "operational_status": {
                "is_active": gateway.get("status") == "active",
                "is_healthy": gateway.get("health", "").lower()
                in ["healthy", "good", "ok"],
                "status_summary": f"{gateway.get('status', 'unknown')} / {gateway.get('health', 'unknown')}",
            },
            "export_summary": {
                "total_exports": len(gateway.get("export_config", [])),
                "export_labels": [
                    exp.get("label", "unlabeled")
                    for exp in gateway.get("export_config", [])
                ],
                "vfs_count": len(
                    {
                        exp.get("vfs_uuid")
                        for exp in gateway.get("export_config", [])
                        if exp.get("vfs_uuid")
                    }
                ),
            },
            "network_summary": {
                "has_public_ipv4": gateway.get("network_config", {})
                .get("primary", {})
                .get("ipv4_public_enabled", False),
                "has_public_ipv6": gateway.get("network_config", {})
                .get("primary", {})
                .get("ipv6_public_enabled", False),
                "has_vpc": bool(
                    gateway.get("network_config", {})
                    .get("primary", {})
                    .get("vpc", {})
                    .get("vpc_uuid")
                ),
            },
            "cost_info": {
                "pending_charges": gateway.get("pending_charges", 0),
                "estimated_monthly": gateway.get("pending_charges", 0)
                * 30,  # Rough estimate
            },
        }

        return status_info

    @mcp.tool
    async def get_mount_instructions(gateway_identifier: str) -> dict[str, Any]:
        """Get NFS mount instructions for a storage gateway.

        Smart identifier resolution: Use gateway label or ID.

        Args:
            gateway_identifier: Gateway label or ID

        Returns:
            NFS mounting instructions and configuration examples
        """
        gateway_id = await get_storage_gateway_id(gateway_identifier)
        gateway = await vultr_client.get_storage_gateway(gateway_id)

        # Generate mount instructions for each export
        exports = gateway.get("export_config", [])
        network_config = gateway.get("network_config", {}).get("primary", {})

        instructions = {
            "gateway_info": {
                "id": gateway_id,
                "label": gateway.get("label", "unlabeled"),
                "type": gateway.get("type", "unknown"),
                "status": gateway.get("status", "unknown"),
                "health": gateway.get("health", "unknown"),
            },
            "network_info": {
                "has_public_ipv4": network_config.get("ipv4_public_enabled", False),
                "has_public_ipv6": network_config.get("ipv6_public_enabled", False),
                "vpc_configured": bool(network_config.get("vpc", {}).get("vpc_uuid")),
            },
            "exports": [],
            "prerequisites": [
                "Storage gateway must be in 'active' status",
                "Client must have NFS client installed (nfs-common on Ubuntu/Debian)",
                "Network connectivity to gateway (check firewall rules)",
                "Client IP must be in allowed_ips list for the export",
            ],
            "common_commands": {
                "install_nfs_ubuntu": "sudo apt update && sudo apt install -y nfs-common",
                "install_nfs_rhel": "sudo yum install -y nfs-utils",
                "install_nfs_alpine": "sudo apk add nfs-utils",
                "test_connectivity": "showmount -e <gateway-ip>",
                "check_mounts": "df -h -t nfs4",
            },
        }

        if not exports:
            instructions["warning"] = "No exports configured on this gateway"
            return instructions

        for i, export in enumerate(exports):
            export_label = export.get("label", f"export_{i}")
            pseudo_path = export.get("pseudo_root_path", "/")
            allowed_ips = export.get("allowed_ips", [])

            mount_point = f"/mnt/{export_label}"

            export_info = {
                "export_label": export_label,
                "pseudo_root_path": pseudo_path,
                "allowed_ips": allowed_ips,
                "mount_point": mount_point,
                "commands": {
                    "create_mount_point": f"sudo mkdir -p {mount_point}",
                    "mount_command": f"sudo mount -t nfs4 <gateway-ip>:{pseudo_path} {mount_point}",
                    "mount_with_options": f"sudo mount -t nfs4 -o rsize=1048576,wsize=1048576,hard,intr,timeo=600 <gateway-ip>:{pseudo_path} {mount_point}",
                    "test_mount": f"ls -la {mount_point}",
                    "unmount": f"sudo umount {mount_point}",
                    "fstab_entry": f"<gateway-ip>:{pseudo_path} {mount_point} nfs4 rsize=1048576,wsize=1048576,hard,intr,timeo=600 0 0",
                },
                "full_script": f"""# Mount script for export: {export_label}
sudo mkdir -p {mount_point}
sudo mount -t nfs4 -o rsize=1048576,wsize=1048576,hard,intr,timeo=600 <gateway-ip>:{pseudo_path} {mount_point}
ls -la {mount_point}

# To make persistent, add to /etc/fstab:
echo '<gateway-ip>:{pseudo_path} {mount_point} nfs4 rsize=1048576,wsize=1048576,hard,intr,timeo=600 0 0' | sudo tee -a /etc/fstab""",
            }

            instructions["exports"].append(export_info)

        if gateway.get("status") != "active":
            instructions["warning"] = (
                f"Gateway is not active (status: {gateway.get('status')}). Wait for it to become active before mounting."
            )

        return instructions

    @mcp.tool
    async def optimize_gateway_configuration(gateway_identifier: str) -> dict[str, Any]:
        """Analyze and provide optimization recommendations for a storage gateway.

        Smart identifier resolution: Use gateway label or ID.

        Args:
            gateway_identifier: Gateway label or ID

        Returns:
            Configuration analysis and optimization recommendations
        """
        gateway_id = await get_storage_gateway_id(gateway_identifier)
        gateway = await vultr_client.get_storage_gateway(gateway_id)

        exports = gateway.get("export_config", [])
        network_config = gateway.get("network_config", {}).get("primary", {})

        analysis = {
            "gateway_info": {
                "id": gateway_id,
                "label": gateway.get("label", "unlabeled"),
                "type": gateway.get("type"),
                "status": gateway.get("status"),
                "health": gateway.get("health"),
            },
            "current_configuration": {
                "export_count": len(exports),
                "has_public_ipv4": network_config.get("ipv4_public_enabled", False),
                "has_public_ipv6": network_config.get("ipv6_public_enabled", False),
                "has_vpc": bool(network_config.get("vpc", {}).get("vpc_uuid")),
                "total_vfs": len(
                    {exp.get("vfs_uuid") for exp in exports if exp.get("vfs_uuid")}
                ),
            },
            "recommendations": [],
            "security_considerations": [],
            "performance_tips": [],
            "cost_optimization": [],
        }

        # Security recommendations
        has_unrestricted_exports = any(
            not exp.get("allowed_ips") or "*" in exp.get("allowed_ips", [])
            for exp in exports
        )

        if has_unrestricted_exports:
            analysis["security_considerations"].append(
                {
                    "priority": "HIGH",
                    "issue": "Unrestricted IP access detected",
                    "recommendation": "Restrict allowed_ips to specific IP addresses or subnets",
                    "details": "Open access (*) or empty allowed_ips list poses security risks",
                }
            )

        if network_config.get("ipv4_public_enabled") and not network_config.get(
            "vpc", {}
        ).get("vpc_uuid"):
            analysis["security_considerations"].append(
                {
                    "priority": "MEDIUM",
                    "issue": "Public access without VPC",
                    "recommendation": "Consider using VPC for additional network isolation",
                    "details": "VPC provides better network security and control",
                }
            )

        # Performance recommendations
        if len(exports) > 5:
            analysis["performance_tips"].append(
                {
                    "priority": "MEDIUM",
                    "issue": "Multiple exports on single gateway",
                    "recommendation": "Consider distributing exports across multiple gateways",
                    "details": "Too many exports can impact performance",
                }
            )

        vfs_usage = {}
        for exp in exports:
            vfs_uuid = exp.get("vfs_uuid")
            if vfs_uuid:
                vfs_usage[vfs_uuid] = vfs_usage.get(vfs_uuid, 0) + 1

        duplicated_vfs = {vfs: count for vfs, count in vfs_usage.items() if count > 1}
        if duplicated_vfs:
            analysis["performance_tips"].append(
                {
                    "priority": "LOW",
                    "issue": "Multiple exports for same VFS",
                    "recommendation": "Consolidate exports using different pseudo paths",
                    "details": f"VFS {list(duplicated_vfs.keys())} exported multiple times",
                }
            )

        # Cost optimization
        if network_config.get("ipv6_public_enabled") and not network_config.get(
            "ipv4_public_enabled"
        ):
            analysis["cost_optimization"].append(
                {
                    "priority": "LOW",
                    "tip": "IPv6-only configuration",
                    "benefit": "Using IPv6-only can reduce costs compared to dual-stack",
                    "consideration": "Ensure clients support IPv6 connectivity",
                }
            )

        # General recommendations
        if gateway.get("status") == "active" and gateway.get("health") != "healthy":
            analysis["recommendations"].append(
                {
                    "priority": "HIGH",
                    "category": "Health",
                    "action": "Investigate gateway health issues",
                    "description": f"Gateway health is '{gateway.get('health')}' instead of 'healthy'",
                }
            )

        if not exports:
            analysis["recommendations"].append(
                {
                    "priority": "HIGH",
                    "category": "Configuration",
                    "action": "Add at least one export",
                    "description": "Gateway has no exports configured",
                }
            )

        # Configuration quality score
        score = 100
        if has_unrestricted_exports:
            score -= 30
        if not network_config.get("vpc", {}).get("vpc_uuid"):
            score -= 10
        if len(exports) == 0:
            score -= 40
        if gateway.get("health") != "healthy":
            score -= 20

        analysis["configuration_score"] = {
            "score": max(0, score),
            "rating": "Excellent"
            if score >= 90
            else "Good"
            if score >= 70
            else "Fair"
            if score >= 50
            else "Poor",
            "description": f"Configuration quality score: {max(0, score)}/100",
        }

        return analysis

    @mcp.tool
    async def get_cost_analysis(gateway_identifier: str) -> dict[str, Any]:
        """Get cost analysis and projections for a storage gateway.

        Smart identifier resolution: Use gateway label or ID.

        Args:
            gateway_identifier: Gateway label or ID

        Returns:
            Detailed cost analysis and projections
        """
        gateway_id = await get_storage_gateway_id(gateway_identifier)
        gateway = await vultr_client.get_storage_gateway(gateway_id)

        pending_charges = gateway.get("pending_charges", 0)
        exports = gateway.get("export_config", [])
        network_config = gateway.get("network_config", {}).get("primary", {})

        cost_analysis = {
            "gateway_info": {
                "id": gateway_id,
                "label": gateway.get("label", "unlabeled"),
                "region": gateway.get("region", "unknown"),
                "type": gateway.get("type", "unknown"),
            },
            "current_charges": {
                "pending_charges": pending_charges,
                "currency": "USD",  # Assuming USD
            },
            "projections": {
                "daily_estimate": pending_charges,
                "weekly_estimate": pending_charges * 7,
                "monthly_estimate": pending_charges * 30,
                "yearly_estimate": pending_charges * 365,
            },
            "cost_breakdown": {
                "base_gateway_cost": "Included in pending charges",
                "export_count": len(exports),
                "network_features": {
                    "public_ipv4": network_config.get("ipv4_public_enabled", False),
                    "public_ipv6": network_config.get("ipv6_public_enabled", False),
                    "vpc_enabled": bool(network_config.get("vpc", {}).get("vpc_uuid")),
                },
            },
            "optimization_suggestions": [],
        }

        # Cost optimization suggestions
        if pending_charges > 0:
            if len(exports) == 0:
                cost_analysis["optimization_suggestions"].append(
                    {
                        "category": "Utilization",
                        "suggestion": "No exports configured - consider deleting if unused",
                        "potential_savings": f"${pending_charges * 30:.2f}/month",
                    }
                )

            if network_config.get("ipv4_public_enabled") and network_config.get(
                "ipv6_public_enabled"
            ):
                cost_analysis["optimization_suggestions"].append(
                    {
                        "category": "Network",
                        "suggestion": "Consider IPv6-only if clients support it",
                        "potential_savings": "Potential cost reduction for dual-stack",
                    }
                )

        # Add cost comparison with alternatives
        cost_analysis["cost_comparison"] = {
            "storage_gateway_monthly": pending_charges * 30,
            "note": "Compare with direct VFS access costs and instance-based NFS",
            "considerations": [
                "Storage Gateway provides managed NFS service",
                "Compare with self-managed NFS on compute instances",
                "Factor in management overhead and reliability",
            ],
        }

        return cost_analysis

    return mcp

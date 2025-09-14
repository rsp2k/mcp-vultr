"""
Mock API logging for test debugging and verification.

This module provides logging capabilities for the mock Vultr API
to help with debugging tests and verifying API call patterns.
"""

import asyncio
import functools
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock


class MockAPILogger:
    """Logger for mock API calls during testing."""
    
    def __init__(self, log_file: Optional[Path] = None, console_output: bool = False):
        """
        Initialize the mock API logger.
        
        Args:
            log_file: Optional file path to write logs to
            console_output: Whether to print logs to console
        """
        self.log_file = log_file
        self.console_output = console_output
        self.call_history: List[Dict[str, Any]] = []
        self._call_counter = 0
    
    def log_call(self, method: str, args: tuple, kwargs: dict, result: Any = None, error: Any = None):
        """
        Log a mock API call.
        
        Args:
            method: The API method called
            args: Positional arguments
            kwargs: Keyword arguments
            result: The return value (if successful)
            error: The exception raised (if any)
        """
        self._call_counter += 1
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "call_number": self._call_counter,
            "method": method,
            "args": str(args),
            "kwargs": str(kwargs),
            "result": str(result)[:200] if result else None,
            "error": str(error) if error else None,
        }
        
        self.call_history.append(log_entry)
        
        if self.console_output:
            status = "✅" if not error else "❌"
            print(f"{status} Mock API Call #{self._call_counter}: {method}")
            if args or kwargs:
                print(f"   Args: {args}, Kwargs: {kwargs}")
            if error:
                print(f"   Error: {error}")
        
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
    
    def get_call_summary(self) -> Dict[str, Any]:
        """Get a summary of all API calls."""
        method_counts = {}
        error_count = 0
        domain_stats = {}
        record_types = {}
        
        for call in self.call_history:
            method = call["method"]
            method_counts[method] = method_counts.get(method, 0) + 1
            if call["error"]:
                error_count += 1
            
            # Track domain-specific operations
            if "domain" in method.lower():
                if "args" in call and call["args"]:
                    domain = str(call["args"]).split("'")[1] if "'" in str(call["args"]) else "unknown"
                    domain_stats[domain] = domain_stats.get(domain, 0) + 1
            
            # Track record types for create/update operations
            if "record" in method.lower() and "kwargs" in call:
                kwargs_str = str(call["kwargs"])
                if "'type':" in kwargs_str or "'record_type':" in kwargs_str:
                    import re
                    type_match = re.search(r"'(?:record_)?type':\s*'([^']+)'", kwargs_str)
                    if type_match:
                        rtype = type_match.group(1)
                        record_types[rtype] = record_types.get(rtype, 0) + 1
        
        return {
            "total_calls": len(self.call_history),
            "unique_methods": len(method_counts),
            "method_counts": method_counts,
            "error_count": error_count,
            "success_rate": f"{(1 - error_count/len(self.call_history))*100:.1f}%" if self.call_history else "N/A",
            "domain_stats": domain_stats,
            "record_types": record_types
        }
    
    def clear(self):
        """Clear the call history."""
        self.call_history = []
        self._call_counter = 0
    
    def print_summary(self):
        """Print a summary of API calls to console."""
        summary = self.get_call_summary()
        print("\n" + "="*60)
        print("MOCK API CALL SUMMARY")
        print("="*60)
        print(f"Total Calls: {summary['total_calls']}")
        print(f"Unique Methods: {summary['unique_methods']}")
        print(f"Success Rate: {summary['success_rate']}")
        print(f"Errors: {summary['error_count']}")
        
        if summary['method_counts']:
            print("\nMethod Call Counts:")
            for method, count in sorted(summary['method_counts'].items()):
                print(f"  {method}: {count}")
        
        if summary.get('domain_stats'):
            print("\nDomain Operations:")
            for domain, count in sorted(summary['domain_stats'].items()):
                print(f"  {domain}: {count} operations")
        
        if summary.get('record_types'):
            print("\nRecord Types Created/Updated:")
            for rtype, count in sorted(summary['record_types'].items()):
                print(f"  {rtype}: {count}")
        
        print("="*60 + "\n")


def logged_mock(mock_client: AsyncMock, logger: MockAPILogger):
    """
    Wrap a mock client with logging capabilities.
    
    Args:
        mock_client: The AsyncMock client to wrap
        logger: The MockAPILogger instance
    
    Returns:
        The wrapped mock client with logging
    """
    # Store original side_effect functions
    original_side_effects = {}
    
    # List of methods we want to log - ALL Vultr API methods
    methods_to_log = [
        # DNS Management
        'list_domains', 'get_domain', 'create_domain', 'delete_domain',
        'list_records', 'get_record', 'create_record', 'update_record', 'delete_record',
        'validate_record', 'analyze_domain', 'export_zone_file', 'import_zone_file',
        
        # Instance Management
        'list_instances', 'get_instance', 'create_instance', 'update_instance', 'delete_instance',
        'start_instance', 'stop_instance', 'reboot_instance', 'reinstall_instance',
        'get_instance_bandwidth', 'list_instance_ipv4', 'create_instance_ipv4', 'delete_instance_ipv4',
        'list_instance_ipv6',
        
        # SSH Keys
        'list_ssh_keys', 'get_ssh_key', 'create_ssh_key', 'update_ssh_key', 'delete_ssh_key',
        
        # Backups
        'list_backups', 'get_backup',
        
        # Firewall
        'list_firewall_groups', 'get_firewall_group', 'create_firewall_group', 
        'update_firewall_group', 'delete_firewall_group',
        'list_firewall_rules', 'get_firewall_rule', 'create_firewall_rule', 'delete_firewall_rule',
        
        # Snapshots
        'list_snapshots', 'get_snapshot', 'create_snapshot', 'create_snapshot_from_url',
        'update_snapshot', 'delete_snapshot',
        
        # Regions
        'list_regions', 'list_availability',
        
        # Reserved IPs
        'list_reserved_ips', 'get_reserved_ip', 'create_reserved_ip', 'update_reserved_ip',
        'delete_reserved_ip', 'attach_reserved_ip', 'detach_reserved_ip', 
        'convert_instance_ip_to_reserved',
        
        # Block Storage
        'list_block_storage', 'get_block_storage', 'create_block_storage', 
        'update_block_storage', 'delete_block_storage', 'attach_block_storage', 'detach_block_storage',
        
        # VPCs
        'list_vpcs', 'get_vpc', 'create_vpc', 'update_vpc', 'delete_vpc',
        'list_vpc2s', 'get_vpc2', 'create_vpc2', 'update_vpc2', 'delete_vpc2',
        'attach_vpc_to_instance', 'detach_vpc_from_instance',
        'attach_vpc2_to_instance', 'detach_vpc2_from_instance',
        'list_instance_vpcs', 'list_instance_vpc2s',
        
        # Container Registry
        'list_container_registries', 'get_container_registry', 'create_container_registry',
        'update_container_registry', 'delete_container_registry', 'list_registry_plans',
        'generate_docker_credentials', 'generate_kubernetes_credentials',
        
        # Operating Systems & Plans
        'list_operating_systems', 'get_operating_system', 'list_plans', 'get_plan',
        
        # Kubernetes
        'list_kubernetes_clusters', 'get_kubernetes_cluster', 'create_kubernetes_cluster',
        'update_kubernetes_cluster', 'delete_kubernetes_cluster', 'delete_kubernetes_cluster_with_resources',
        'get_kubernetes_cluster_config', 'get_kubernetes_cluster_resources',
        'get_kubernetes_available_upgrades', 'upgrade_kubernetes_cluster', 'get_kubernetes_versions',
        'list_kubernetes_node_pools', 'get_kubernetes_node_pool', 'create_kubernetes_node_pool',
        'update_kubernetes_node_pool', 'delete_kubernetes_node_pool',
        'list_kubernetes_nodes', 'get_kubernetes_node', 'delete_kubernetes_node', 'recycle_kubernetes_node',
        
        # Managed Databases
        'list_managed_databases', 'get_managed_database', 'create_managed_database',
        'update_managed_database', 'delete_managed_database', 'get_database_usage',
        'list_database_users', 'create_database_user', 'get_database_user',
        'update_database_user', 'delete_database_user', 'update_database_user_access_control',
        'list_logical_databases', 'create_logical_database', 'get_logical_database', 'delete_logical_database',
        'list_connection_pools', 'create_connection_pool', 'get_connection_pool',
        'update_connection_pool', 'delete_connection_pool',
        'list_database_backups', 'restore_database_from_backup', 'fork_database', 'create_read_replica',
        'promote_read_replica', 'list_database_plans', 'list_database_versions',
        'start_version_upgrade', 'get_maintenance_updates', 'start_maintenance',
        'get_migration_status', 'start_migration', 'stop_migration',
        
        # Load Balancers
        'list_load_balancers', 'get_load_balancer', 'create_load_balancer',
        'update_load_balancer', 'delete_load_balancer',
        
        # Billing & Account
        'get_account_info', 'list_billing_history', 'list_invoices', 'get_invoice',
        'list_invoice_items', 'get_current_balance', 'get_monthly_usage_summary',
        
        # Object Storage
        'list_object_storage', 'get_object_storage', 'create_object_storage',
        'update_object_storage', 'delete_object_storage', 'regenerate_object_storage_keys',
        'list_object_storage_clusters', 'list_object_storage_cluster_tiers',
        
        # ISO Management
        'list_isos', 'get_iso', 'create_iso', 'delete_iso',
        
        # Applications & Marketplace
        'list_applications', 'get_marketplace_app_variables',
        
        # Startup Scripts
        'list_startup_scripts', 'get_startup_script', 'create_startup_script',
        'update_startup_script', 'delete_startup_script',
        
        # Bare Metal
        'list_bare_metal_servers', 'get_bare_metal_server', 'create_bare_metal_server',
        'update_bare_metal_server', 'delete_bare_metal_server', 'start_bare_metal_server',
        'stop_bare_metal_server', 'reboot_bare_metal_server', 'reinstall_bare_metal_server',
        'get_bare_metal_bandwidth', 'get_bare_metal_neighbors', 'get_bare_metal_user_data',
        'list_bare_metal_plans', 'get_bare_metal_plan'
    ]
    
    for method_name in methods_to_log:
        if hasattr(mock_client, method_name):
            method = getattr(mock_client, method_name)
            original_return = method.return_value
            original_side_effect = method.side_effect
            
            # Create a wrapper that logs
            def make_logged_method(name, orig_return, orig_side_effect):
                async def logged_method(*args, **kwargs):
                    try:
                        # Use original behavior
                        if orig_side_effect:
                            if asyncio.iscoroutinefunction(orig_side_effect):
                                result = await orig_side_effect(*args, **kwargs)
                            else:
                                result = orig_side_effect(*args, **kwargs)
                        else:
                            result = orig_return
                        
                        logger.log_call(name, args, kwargs, result=result)
                        return result
                    except Exception as e:
                        logger.log_call(name, args, kwargs, error=e)
                        raise
                return logged_method
            
            # Set the new side_effect
            method.side_effect = make_logged_method(
                method_name, original_return, original_side_effect
            )
    
    return mock_client


# Global logger instance for easy access during tests
mock_api_logger = MockAPILogger(console_output=False)


def enable_mock_api_logging(console: bool = True, log_file: Optional[str] = None):
    """
    Enable mock API logging for debugging.
    
    Args:
        console: Whether to print to console
        log_file: Optional file path for log output
    """
    global mock_api_logger
    mock_api_logger.console_output = console
    if log_file:
        mock_api_logger.log_file = Path(log_file)


def get_mock_api_summary():
    """Get a summary of all mock API calls made during tests."""
    return mock_api_logger.get_call_summary()


def clear_mock_api_logs():
    """Clear all mock API logs."""
    mock_api_logger.clear()
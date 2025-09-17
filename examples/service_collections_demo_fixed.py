#!/usr/bin/env python3
"""
Service Collections Demo

This example demonstrates the Vultr service collection system for organizing
resources by project and environment, with workflow orchestration capabilities.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from mcp_vultr.service_collections import (
    ServiceCollection,
    ServiceCollectionStore,
    ResourceReference,
    ResourceType,
    Environment,
    WorkflowDefinition,
    WorkflowTrigger,
    create_service_collections_mcp,
)


class MockVultrClient:
    """Mock Vultr client for demonstration purposes."""
    
    def __init__(self):
        self.domains = ["example.com", "test.dev"]
        self.instances = [
            {"id": "web-1", "label": "web-server-1", "region": "ewr"},
            {"id": "db-1", "label": "database-1", "region": "ewr"},
        ]


async def demo_service_collections():
    """Demonstrate service collection management."""
    
    print("🚀 Vultr Service Collections Demo")
    print("=" * 50)
    
    # Initialize the service collection system
    vultr_client = MockVultrClient()
    store = ServiceCollectionStore()
    mcp = create_service_collections_mcp(vultr_client, store)
    
    print("\\n📂 Creating Service Collections...")
    
    # Create development environment collection
    dev_collection = ServiceCollection(
        name="web-app",
        project="ecommerce-platform",
        environment=Environment.DEVELOPMENT,
        description="Development environment for e-commerce web application",
        region="ewr",
        tags={"team": "frontend", "cost-center": "engineering"},
        created_by="developer@company.com",
    )
    dev_collection.owners.add("developer@company.com")
    dev_collection.editors.add("team-lead@company.com")
    
    # Add development resources
    dev_resources = [
        ResourceReference(
            resource_type=ResourceType.INSTANCE,
            resource_id="dev-web-1",
            resource_name="dev-web-server",
            tags={"role": "web", "tier": "frontend"},
            metadata={"cpu": "1vcpu", "memory": "1gb", "storage": "25gb"},
        ),
        ResourceReference(
            resource_type=ResourceType.DOMAIN,
            resource_id="dev.example.com",
            resource_name="Development Domain",
            tags={"environment": "dev"},
            metadata={"ssl": "letsencrypt", "cdn": "disabled"},
        ),
        ResourceReference(
            resource_type=ResourceType.BLOCK_STORAGE,
            resource_id="dev-storage-1",
            resource_name="Development Storage",
            tags={"backup": "daily"},
            metadata={"size": "10gb", "type": "high_perf"},
        ),
    ]
    
    for resource in dev_resources:
        dev_collection.add_resource(resource)
    
    store.save(dev_collection)
    
    print(f"✅ Created development collection: {dev_collection}")
    print(f"   Resources: {len(dev_collection.resources)}")
    print(f"   Permissions: {len(dev_collection.owners)} owners, {len(dev_collection.editors)} editors")
    
    # Create production environment collection
    prod_collection = ServiceCollection(
        name="web-app",
        project="ecommerce-platform",
        environment=Environment.PRODUCTION,
        description="Production environment for e-commerce web application",
        region="ewr",
        tags={"team": "frontend", "cost-center": "engineering", "critical": "true"},
        created_by="devops@company.com",
    )
    prod_collection.owners.add("devops@company.com")
    prod_collection.editors.add("team-lead@company.com")
    prod_collection.viewers.add("developer@company.com")
    
    # Add production resources (more robust setup)
    prod_resources = [
        ResourceReference(
            resource_type=ResourceType.INSTANCE,
            resource_id="prod-web-1",
            resource_name="prod-web-server-1",
            tags={"role": "web", "tier": "frontend", "ha": "primary"},
            metadata={"cpu": "4vcpu", "memory": "8gb", "storage": "100gb"},
        ),
        ResourceReference(
            resource_type=ResourceType.INSTANCE,
            resource_id="prod-web-2",
            resource_name="prod-web-server-2",
            tags={"role": "web", "tier": "frontend", "ha": "secondary"},
            metadata={"cpu": "4vcpu", "memory": "8gb", "storage": "100gb"},
        ),
        ResourceReference(
            resource_type=ResourceType.LOAD_BALANCER,
            resource_id="prod-lb-1",
            resource_name="Production Load Balancer",
            tags={"role": "load-balancer"},
            metadata={"ssl": "enabled", "health_check": "enabled"},
        ),
        ResourceReference(
            resource_type=ResourceType.DOMAIN,
            resource_id="example.com",
            resource_name="Production Domain",
            tags={"environment": "prod"},
            metadata={"ssl": "wildcard", "cdn": "enabled"},
        ),
    ]
    
    for resource in prod_resources:
        prod_collection.add_resource(resource)
    
    store.save(prod_collection)
    
    print(f"\\n✅ Created production collection: {prod_collection}")
    print(f"   Resources: {len(prod_collection.resources)}")
    print(f"   Permissions: {len(prod_collection.owners)} owners, {len(prod_collection.editors)} editors, {len(prod_collection.viewers)} viewers")
    
    print("\\n🔄 Demonstrating Environment Promotion...")
    
    # Create staging collection by promotion
    staging_collection = ServiceCollection(
        name="web-app",
        project="ecommerce-platform",
        environment=Environment.STAGING,
        description="Promoted from development for testing",
        region="ewr",
        tags=dev_collection.tags.copy(),
    )
    
    # Copy some resources for staging
    for resource in dev_collection.resources:
        if resource.resource_type in [ResourceType.DOMAIN, ResourceType.INSTANCE]:
            staging_resource = ResourceReference(
                resource_type=resource.resource_type,
                resource_id=resource.resource_id.replace("dev-", "staging-"),
                resource_name=resource.resource_name.replace("Development", "Staging"),
                tags={**resource.tags, "environment": "staging"},
                metadata=resource.metadata.copy(),
            )
            staging_collection.add_resource(staging_resource)
    
    store.save(staging_collection)
    
    print(f"✅ Promoted to staging: {staging_collection}")
    print(f"   Resources copied: {len(staging_collection.resources)}")
    
    print("\\n📊 Collection Summary:")
    print("-" * 30)
    
    # List all collections by project
    project_collections = store.list_by_project("ecommerce-platform")
    
    for collection in project_collections:
        env_name = collection.environment.value if isinstance(collection.environment, Environment) else collection.environment
        print(f"Environment: {env_name.upper()}")
        print(f"  Collection: {collection.name}")
        print(f"  Resources: {len(collection.resources)}")
        print(f"  Region: {collection.region}")
        print(f"  Created: {collection.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Show resource breakdown
        resource_types = {}
        for resource in collection.resources:
            res_type = resource.resource_type.value
            resource_types[res_type] = resource_types.get(res_type, 0) + 1
        
        for res_type, count in resource_types.items():
            print(f"    {res_type}: {count}")
        print()
    
    print("🎉 Service Collections Demo Complete!")
    print("\\nKey Features Demonstrated:")
    print("  ✅ Multi-environment organization (dev/staging/prod)")
    print("  ✅ Resource grouping and tagging")
    print("  ✅ Permission-based access control")
    print("  ✅ Environment promotion workflows")
    print("  ✅ Resource filtering and organization")


if __name__ == "__main__":
    asyncio.run(demo_service_collections())
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
    
    print(f\"✅ Created development collection: {dev_collection}\")\n    print(f\"   Resources: {len(dev_collection.resources)}\")\n    print(f\"   Permissions: {len(dev_collection.owners)} owners, {len(dev_collection.editors)} editors\")\n    \n    print(f\"\\n✅ Created production collection: {prod_collection}\")\n    print(f\"   Resources: {len(prod_collection.resources)}\")\n    print(f\"   Permissions: {len(prod_collection.owners)} owners, {len(prod_collection.editors)} editors, {len(prod_collection.viewers)} viewers\")\n    \n    print(\"\\n🔄 Demonstrating Environment Promotion...\")\n    \n    # Create staging collection by promotion\n    staging_collection = ServiceCollection(\n        name=\"web-app\",\n        project=\"ecommerce-platform\",\n        environment=Environment.STAGING,\n        description=\"Promoted from development for testing\",\n        region=\"ewr\",\n        tags=dev_collection.tags.copy(),\n    )\n    \n    # Copy some resources for staging\n    for resource in dev_collection.resources:\n        if resource.resource_type in [ResourceType.DOMAIN, ResourceType.INSTANCE]:\n            staging_resource = ResourceReference(\n                resource_type=resource.resource_type,\n                resource_id=resource.resource_id.replace(\"dev-\", \"staging-\"),\n                resource_name=resource.resource_name.replace(\"Development\", \"Staging\"),\n                tags={**resource.tags, \"environment\": \"staging\"},\n                metadata=resource.metadata.copy(),\n            )\n            staging_collection.add_resource(staging_resource)\n    \n    store.save(staging_collection)\n    \n    print(f\"✅ Promoted to staging: {staging_collection}\")\n    print(f\"   Resources copied: {len(staging_collection.resources)}\")\n    \n    print(\"\\n📊 Collection Summary:\")\n    print(\"-\" * 30)\n    \n    # List all collections by project\n    project_collections = store.list_by_project(\"ecommerce-platform\")\n    \n    for collection in project_collections:\n        env_name = collection.environment.value if isinstance(collection.environment, Environment) else collection.environment\n        print(f\"Environment: {env_name.upper()}\")\n        print(f\"  Collection: {collection.name}\")\n        print(f\"  Resources: {len(collection.resources)}\")\n        print(f\"  Region: {collection.region}\")\n        print(f\"  Created: {collection.created_at.strftime('%Y-%m-%d %H:%M')}\")\n        \n        # Show resource breakdown\n        resource_types = {}\n        for resource in collection.resources:\n            res_type = resource.resource_type.value\n            resource_types[res_type] = resource_types.get(res_type, 0) + 1\n        \n        for res_type, count in resource_types.items():\n            print(f\"    {res_type}: {count}\")\n        print()\n    \n    print(\"\\n🔧 Demonstrating Workflow System...\")\n    \n    # Add deployment workflow to production collection\n    deployment_workflow = WorkflowDefinition(\n        name=\"Production Deployment\",\n        description=\"Automated deployment workflow with approval gates\",\n        triggers=[\n            WorkflowTrigger.ENVIRONMENT_PROMOTED,\n            WorkflowTrigger.MANUAL_TRIGGER,\n        ],\n        conditions={\n            \"target_environment\": Environment.PRODUCTION,\n            \"approval_required\": True,\n        },\n        actions=[\n            {\"type\": \"notification\", \"channel\": \"slack\", \"message\": \"Production deployment requested\"},\n            {\"type\": \"approval\", \"approvers\": [\"devops@company.com\", \"team-lead@company.com\"]},\n            {\"type\": \"deploy\", \"strategy\": \"blue-green\"},\n            {\"type\": \"health_check\", \"timeout\": 300},\n            {\"type\": \"notification\", \"channel\": \"slack\", \"message\": \"Production deployment completed\"},\n        ],\n        permissions={\"devops@company.com\", \"team-lead@company.com\"},\n    )\n    \n    prod_collection.workflows.append(deployment_workflow)\n    store.save(prod_collection)\n    \n    print(f\"✅ Added workflow: {deployment_workflow.name}\")\n    print(f\"   Triggers: {[t.value for t in deployment_workflow.triggers]}\")\n    print(f\"   Actions: {len(deployment_workflow.actions)}\")\n    \n    # Test workflow trigger conditions\n    test_context = {\n        \"target_environment\": Environment.PRODUCTION,\n        \"approval_required\": True,\n        \"source_environment\": Environment.STAGING,\n    }\n    \n    would_trigger = deployment_workflow.can_trigger(\n        WorkflowTrigger.ENVIRONMENT_PROMOTED, \n        test_context\n    )\n    \n    print(f\"\\n🎯 Workflow Trigger Test:\")\n    print(f\"   Context: staging -> production promotion\")\n    print(f\"   Would trigger: {'✅ YES' if would_trigger else '❌ NO'}\")\n    \n    print(\"\\n🔐 Permission Management Demo...\")\n    \n    # Check permissions\n    test_user = \"developer@company.com\"\n    \n    permissions_test = [\n        (dev_collection, \"read\"),\n        (dev_collection, \"write\"),\n        (prod_collection, \"read\"),\n        (prod_collection, \"write\"),\n    ]\n    \n    print(f\"\\nPermissions for {test_user}:\")\n    for collection, permission in permissions_test:\n        has_permission = collection.has_permission(test_user, permission)\n        env_name = collection.environment.value if isinstance(collection.environment, Environment) else collection.environment\n        status = \"✅\" if has_permission else \"❌\"\n        print(f\"  {env_name} {permission}: {status}\")\n    \n    print(\"\\n🏷️  Resource Tagging and Organization...\")\n    \n    # Demonstrate resource filtering by tags\n    all_resources = []\n    for collection in project_collections:\n        for resource in collection.resources:\n            all_resources.append({\n                \"collection\": collection.name,\n                \"environment\": collection.environment.value if isinstance(collection.environment, Environment) else collection.environment,\n                \"resource\": str(resource),\n                \"tags\": resource.tags,\n            })\n    \n    # Filter by role\n    web_resources = [r for r in all_resources if r[\"tags\"].get(\"role\") == \"web\"]\n    print(f\"\\nWeb resources across all environments: {len(web_resources)}\")\n    for resource in web_resources:\n        print(f\"  {resource['environment']}: {resource['resource']}\")\n    \n    # Filter by tier\n    frontend_resources = [r for r in all_resources if r[\"tags\"].get(\"tier\") == \"frontend\"]\n    print(f\"\\nFrontend resources: {len(frontend_resources)}\")\n    for resource in frontend_resources:\n        print(f\"  {resource['environment']}: {resource['resource']}\")\n    \n    print(\"\\n🎉 Service Collections Demo Complete!\")\n    print(\"\\nKey Features Demonstrated:\")\n    print(\"  ✅ Multi-environment organization (dev/staging/prod)\")\n    print(\"  ✅ Resource grouping and tagging\")\n    print(\"  ✅ Permission-based access control\")\n    print(\"  ✅ Workflow orchestration and triggers\")\n    print(\"  ✅ Environment promotion workflows\")\n    print(\"  ✅ Resource filtering and organization\")\n    print(\"\\nThis provides the foundation for:\")\n    print(\"  🔄 Infrastructure CI/CD pipelines\")\n    print(\"  🔐 Team-based permission management\")\n    print(\"  📊 Resource cost tracking and optimization\")\n    print(\"  🚨 Automated monitoring and alerting\")\n    print(\"  📋 Audit trails and compliance reporting\")\n\n\nif __name__ == \"__main__\":\n    asyncio.run(demo_service_collections())
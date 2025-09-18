# Service Collection Workflow Architecture

## Overview

This document outlines the enterprise workflow system built on Service Collections, transforming the Vultr MCP from a simple API wrapper into a comprehensive infrastructure-as-code platform with approval workflows, pre-resource collections, and environment protection.

## Core Concepts

### 1. Pre-Resource Service Collections

Service Collections can exist before their underlying Vultr resources are created, serving as "deployment intents" or "infrastructure blueprints."

```json
{
  "collection_id": "new-api-service",
  "status": "pending_approval",
  "environment": "production",
  "resources": {
    "planned": [
      {
        "type": "instance",
        "config": {
          "label": "api-server-01",
          "plan": "vc2-2c-4gb",
          "region": "ewr",
          "os": "ubuntu-22.04"
        },
        "status": "queued",
        "created_by": "developer@company.com",
        "approval_required": true
      },
      {
        "type": "domain",
        "config": {
          "domain": "api.company.com",
          "ip": "TBD_FROM_INSTANCE"
        },
        "status": "queued",
        "depends_on": "api-server-01"
      }
    ],
    "existing": []
  }
}
```

### 2. Workflow Queue System

Operations are queued and processed through approval workflows rather than executed immediately.

#### Queue States
- **`queued`**: Operation waiting for approval
- **`approved`**: Ready for execution
- **`executing`**: Currently being processed
- **`completed`**: Successfully executed
- **`failed`**: Execution failed
- **`rejected`**: Approval denied

#### Approval Types
- **Self-Approval**: User can approve their own operations (development environments)
- **Manager Approval**: Requires approval from collection owner/manager
- **Multi-Stage Approval**: Complex workflows requiring multiple approvers
- **Automated Approval**: CI/CD triggered approvals for tested deployments

### 3. Dashboard-First Architecture

The Service Collection system becomes the primary interface, with vultr.com as fallback "console access."

```
┌─────────────────────────────────────────────────────────┐
│                Service Collection Dashboard              │
│  • Workflow Management                                  │
│  • Resource Planning                                    │
│  • Approval Queues                                     │
│  • Environment Protection                              │
│  • Cost Estimation                                     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              MCP Vultr Server (This System)             │
│  • OAuth Authentication                                 │
│  • Service Collection Management                       │
│  • Workflow Orchestration                             │
│  • API Key Brokering                                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Vultr API                            │
│  • Direct Resource Management                          │
│  • Limited to Service User Operations                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 Vultr.com Console                       │
│  • Emergency/Last Resort Access                        │
│  • Service Collection Unaware                          │
│  • Manual Operations Only                              │
└─────────────────────────────────────────────────────────┘
```

## User Management Strategy

### 1. Vultr Service Users

Dedicated Vultr accounts for managed deployments:

```json
{
  "service_users": {
    "prod-infrastructure-svc": {
      "vultr_email": "prod-infra@company.com",
      "vultr_api_key": "VULTR_PROD_KEY_123...",
      "purpose": "Production infrastructure management",
      "collections": ["prod-web", "prod-api", "prod-database"],
      "restrictions": {
        "no_manual_access": true,
        "workflow_only": true,
        "approval_required": ["delete", "reinstall"]
      }
    },
    "staging-deployment-svc": {
      "vultr_email": "staging@company.com", 
      "vultr_api_key": "VULTR_STAGING_KEY_456...",
      "purpose": "Staging environment automation",
      "collections": ["staging-*"],
      "restrictions": {
        "auto_approve": ["create", "update", "restart"],
        "manual_approve": ["delete"]
      }
    }
  }
}
```

### 2. Individual Developer Access

Developers retain access to their personal Vultr resources while being governed by Service Collection workflows for shared environments:

```json
{
  "user_permissions": {
    "developer@company.com": {
      "personal_vultr_key": "DEV_PERSONAL_KEY_789...",
      "personal_resources": {
        "instances": ["dev-*", "test-*"],
        "domains": ["*.dev.company.com"],
        "unrestricted": true
      },
      "service_collections": {
        "prod-web": {
          "role": "editor",
          "permissions": ["read", "propose_changes"],
          "restrictions": ["no_direct_access"]
        },
        "staging-api": {
          "role": "owner", 
          "permissions": ["read", "write", "approve"],
          "workflow_required": false
        }
      }
    }
  }
}
```

## Workflow Implementation

### 1. Queue-Based Operations

Instead of immediate execution, operations are queued:

```python
@mcp.tool()
@require_collection_access("prod-web", "instance", "create")
async def queue_create_instance(
    collection_id: str,
    instance_config: Dict[str, Any],
    approval_required: bool = True,
    context: dict = None
) -> dict:
    """Queue instance creation for approval workflow."""
    
    # Validate user can propose changes to collection
    user_context = await get_user_context_from_mcp(mcp, context)
    collection = await get_service_collection(collection_id)
    
    if not collection.allows_resource_creation(user_context, "instance"):
        raise PermissionError("Cannot create instances in this collection")
    
    # Queue the operation
    operation = QueuedOperation(
        collection_id=collection_id,
        operation_type="create_instance",
        config=instance_config,
        requested_by=user_context.username,
        approval_required=approval_required,
        status="queued"
    )
    
    # Add to workflow queue
    await workflow_queue.add_operation(operation)
    
    return {
        "operation_id": operation.id,
        "status": "queued",
        "approval_required": approval_required,
        "estimated_cost": await estimate_instance_cost(instance_config)
    }
```

### 2. Approval Workflow Engine

```python
class WorkflowEngine:
    """Manages approval workflows for Service Collection operations."""
    
    async def process_approval_request(
        self,
        operation_id: str,
        approver: UserContext,
        decision: str,  # "approve", "reject", "request_changes"
        comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an approval decision."""
        
        operation = await self.get_queued_operation(operation_id)
        
        # Validate approver permissions
        if not operation.collection.can_approve(approver, operation.operation_type):
            raise PermissionError("Insufficient approval permissions")
        
        if decision == "approve":
            # Move to execution queue
            await self.execute_operation(operation)
            
        elif decision == "reject":
            operation.status = "rejected"
            operation.rejection_reason = comments
            
        # Audit log
        await self.audit_approval(operation, approver, decision, comments)
        
        return {"status": operation.status, "operation_id": operation_id}
```

### 3. Environment Protection

```python
class EnvironmentProtection:
    """Enforces environment-specific workflow requirements."""
    
    ENVIRONMENT_POLICIES = {
        "production": {
            "approval_required": True,
            "min_approvers": 2,
            "restricted_operations": ["delete", "reinstall"],
            "change_window": "maintenance_only",
            "rollback_plan_required": True
        },
        "staging": {
            "approval_required": True,
            "min_approvers": 1,
            "auto_approve": ["restart", "update_config"],
            "change_window": "business_hours"
        },
        "development": {
            "approval_required": False,
            "self_approve": True,
            "unrestricted": True
        }
    }
    
    def validate_operation(
        self,
        collection: ServiceCollection,
        operation: QueuedOperation,
        user: UserContext
    ) -> ValidationResult:
        """Validate operation against environment policies."""
        
        env_policy = self.ENVIRONMENT_POLICIES.get(collection.environment)
        if not env_policy:
            return ValidationResult.allow()
        
        # Check if operation requires approval
        if env_policy.get("approval_required", False):
            if operation.operation_type in env_policy.get("restricted_operations", []):
                return ValidationResult.require_approval(
                    min_approvers=env_policy.get("min_approvers", 1)
                )
        
        # Check change windows
        if not self.in_change_window(env_policy.get("change_window")):
            return ValidationResult.deny("Outside change window")
        
        return ValidationResult.allow()
```

## Read-Only Access During Workflow

While operations are queued, users maintain read access with permission validation:

```python
@mcp.tool()
@require_collection_access("prod-web", "instance", "read")
async def list_collection_instances(
    collection_id: str,
    include_planned: bool = True,
    context: dict = None
) -> dict:
    """List instances in collection, including planned/queued resources."""
    
    user_context = await get_user_context_from_mcp(mcp, context)
    collection = await get_service_collection(collection_id)
    
    # Get existing resources
    existing_instances = []
    for instance_id in collection.resources.get("instances", []):
        if collection.user_can_access_resource(user_context, "instance", instance_id, "read"):
            instance = await vultr_client.get_instance(instance_id)
            existing_instances.append(instance)
    
    # Get planned resources (if user has permission)
    planned_instances = []
    if include_planned and collection.user_can_view_planned_resources(user_context):
        planned_instances = await workflow_queue.get_planned_resources(
            collection_id, "instance"
        )
    
    return {
        "collection_id": collection_id,
        "existing": existing_instances,
        "planned": planned_instances,
        "total_estimated_cost": await calculate_total_cost(existing_instances, planned_instances)
    }
```

## Dashboard Integration

The system provides a comprehensive dashboard that becomes the primary interface:

### Dashboard Features
- **Resource Planning**: Visual infrastructure design with cost estimation
- **Workflow Queues**: Approval pipelines with status tracking  
- **Environment Overview**: Multi-environment resource visualization
- **Cost Management**: Real-time cost tracking and budgeting
- **Access Control**: Service Collection membership management
- **Audit Trails**: Complete operation history and compliance reporting

### vultr.com as Fallback
- Emergency access when MCP system is unavailable
- Manual operations outside Service Collection workflows
- Direct console access for troubleshooting
- Service Collection system remains authoritative for managed resources

## Benefits

### 1. **Controlled Deployments**
- All production changes go through approval workflows
- Staging/production environments protected from unauthorized changes
- Individual developers maintain freedom for personal resources

### 2. **Infrastructure as Code**
- Service Collections define infrastructure declaratively
- Version-controlled resource definitions
- Rollback capabilities and change tracking

### 3. **Cost Management**
- Pre-deployment cost estimation
- Budget enforcement through approval workflows
- Resource optimization recommendations

### 4. **Compliance & Auditing**
- Complete audit trail of all operations
- Approval workflow compliance
- Environment change tracking

### 5. **Developer Experience**
- Self-service infrastructure provisioning
- Clear approval processes
- Personal resource freedom maintained

This architecture transforms the Vultr MCP into a comprehensive enterprise infrastructure platform while maintaining the flexibility and security required for modern cloud operations.
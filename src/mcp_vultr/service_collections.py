"""
Vultr Service Collections FastMCP Module.

This module provides service grouping, environment management, and workflow orchestration
for Vultr resources. It enables project-based organization with dev/test/prod environments.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from .notification_manager import NotificationManager


class Environment(str, Enum):
    """Standard environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    
    # Allow custom environments
    @classmethod
    def _missing_(cls, value):
        return value


class ResourceType(str, Enum):
    """Vultr resource types that can be managed in collections."""
    INSTANCE = "instance"
    DOMAIN = "domain"
    DNS_RECORD = "dns_record"
    LOAD_BALANCER = "load_balancer"
    BLOCK_STORAGE = "block_storage"
    SNAPSHOT = "snapshot"
    SSH_KEY = "ssh_key"
    STARTUP_SCRIPT = "startup_script"
    FIREWALL_GROUP = "firewall_group"
    RESERVED_IP = "reserved_ip"
    VPC = "vpc"
    VPC2 = "vpc2"
    CONTAINER_REGISTRY = "container_registry"
    KUBERNETES_CLUSTER = "kubernetes_cluster"
    MANAGED_DATABASE = "managed_database"
    OBJECT_STORAGE = "object_storage"


class WorkflowTrigger(str, Enum):
    """Events that can trigger workflows."""
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    SERVICE_DEPLOYED = "service_deployed"
    ENVIRONMENT_PROMOTED = "environment_promoted"
    MANUAL_TRIGGER = "manual_trigger"
    SCHEDULED_TRIGGER = "scheduled_trigger"


@dataclass
class ResourceReference:
    """Reference to a Vultr resource within a service collection."""
    resource_type: ResourceType
    resource_id: str
    resource_name: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        name = self.resource_name or self.resource_id
        return f"{self.resource_type.value}:{name}"


@dataclass 
class WorkflowDefinition:
    """Defines a workflow that can be attached to service collections."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    triggers: List[WorkflowTrigger] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    permissions: Set[str] = field(default_factory=set)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def can_trigger(self, trigger: WorkflowTrigger, context: Dict[str, Any]) -> bool:
        """Check if workflow should trigger for given event and context."""
        if not self.enabled or trigger not in self.triggers:
            return False
            
        # Evaluate conditions
        for condition_key, condition_value in self.conditions.items():
            if condition_key not in context:
                return False
            if context[condition_key] != condition_value:
                return False
                
        return True


@dataclass
class ServiceCollection:
    """A collection of Vultr resources grouped by project and environment."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    project: str = ""
    environment: Environment = Environment.DEVELOPMENT
    description: str = ""
    
    # Resource management
    resources: List[ResourceReference] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Workflow orchestration
    workflows: List[WorkflowDefinition] = field(default_factory=list)
    
    # Access control
    owners: Set[str] = field(default_factory=set)
    editors: Set[str] = field(default_factory=set)
    viewers: Set[str] = field(default_factory=set)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    region: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.project}:{self.environment.value}:{self.name}"
    
    def add_resource(self, resource: ResourceReference) -> None:
        """Add a resource to this collection."""
        # Remove existing resource with same type and ID
        self.resources = [r for r in self.resources 
                         if not (r.resource_type == resource.resource_type and 
                                r.resource_id == resource.resource_id)]
        self.resources.append(resource)
        self.updated_at = datetime.utcnow()
    
    def remove_resource(self, resource_type: ResourceType, resource_id: str) -> bool:
        """Remove a resource from this collection."""
        original_count = len(self.resources)
        self.resources = [r for r in self.resources 
                         if not (r.resource_type == resource_type and 
                                r.resource_id == resource_id)]
        self.updated_at = datetime.utcnow()
        return len(self.resources) < original_count
    
    def get_resources_by_type(self, resource_type: ResourceType) -> List[ResourceReference]:
        """Get all resources of a specific type."""
        return [r for r in self.resources if r.resource_type == resource_type]
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specified permission on this collection."""
        if user_id in self.owners:
            return True
        if permission in ["read", "view"] and user_id in self.viewers:
            return True
        if permission in ["read", "view", "write", "edit"] and user_id in self.editors:
            return True
        return False


class ServiceCollectionStore:
    """In-memory store for service collections. Production would use persistent storage."""
    
    def __init__(self):
        self._collections: Dict[str, ServiceCollection] = {}
        self._project_index: Dict[str, Set[str]] = {}  # project -> collection_ids
        self._environment_index: Dict[Environment, Set[str]] = {}  # env -> collection_ids
        
    def save(self, collection: ServiceCollection) -> None:
        """Save a service collection."""
        collection.updated_at = datetime.utcnow()
        self._collections[collection.id] = collection
        
        # Update indexes
        if collection.project not in self._project_index:
            self._project_index[collection.project] = set()
        self._project_index[collection.project].add(collection.id)
        
        if collection.environment not in self._environment_index:
            self._environment_index[collection.environment] = set()
        self._environment_index[collection.environment].add(collection.id)
    
    def get(self, collection_id: str) -> Optional[ServiceCollection]:
        """Get a service collection by ID."""
        return self._collections.get(collection_id)
    
    def list_all(self) -> List[ServiceCollection]:
        """List all service collections."""
        return list(self._collections.values())
    
    def list_by_project(self, project: str) -> List[ServiceCollection]:
        """List collections for a specific project."""
        collection_ids = self._project_index.get(project, set())
        return [self._collections[cid] for cid in collection_ids if cid in self._collections]
    
    def list_by_environment(self, environment: Environment) -> List[ServiceCollection]:
        """List collections for a specific environment."""
        collection_ids = self._environment_index.get(environment, set())
        return [self._collections[cid] for cid in collection_ids if cid in self._collections]
    
    def delete(self, collection_id: str) -> bool:
        """Delete a service collection."""
        if collection_id not in self._collections:
            return False
            
        collection = self._collections[collection_id]
        
        # Remove from indexes
        if collection.project in self._project_index:
            self._project_index[collection.project].discard(collection_id)
        if collection.environment in self._environment_index:
            self._environment_index[collection.environment].discard(collection_id)
            
        del self._collections[collection_id]
        return True


def create_service_collections_mcp(vultr_client, store: Optional[ServiceCollectionStore] = None) -> FastMCP:
    """
    Create a FastMCP instance for service collection management.
    
    Args:
        vultr_client: VultrDNSServer instance
        store: Service collection store (uses in-memory if not provided)
    
    Returns:
        Configured FastMCP instance with service collection tools
    """
    mcp = FastMCP(name="vultr-service-collections")
    
    # Use provided store or create default in-memory store
    collection_store = store or ServiceCollectionStore()
    
    # Service Collection resources
    @mcp.resource("service-collections://list")
    async def list_collections_resource() -> List[Dict[str, Any]]:
        """List all service collections."""
        collections = collection_store.list_all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "project": c.project,
                "environment": c.environment.value,
                "description": c.description,
                "resource_count": len(c.resources),
                "workflow_count": len(c.workflows),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                "tags": c.tags,
            }
            for c in collections
        ]
    
    @mcp.resource("service-collections://projects")
    async def list_projects_resource() -> List[Dict[str, Any]]:
        """List all projects with their environment breakdown."""
        projects = {}
        
        for collection in collection_store.list_all():
            if collection.project not in projects:
                projects[collection.project] = {
                    "name": collection.project,
                    "environments": {},
                    "total_collections": 0,
                    "total_resources": 0,
                }
            
            project = projects[collection.project]
            env_key = collection.environment.value
            
            if env_key not in project["environments"]:
                project["environments"][env_key] = {
                    "collections": 0,
                    "resources": 0,
                }
            
            project["environments"][env_key]["collections"] += 1
            project["environments"][env_key]["resources"] += len(collection.resources)
            project["total_collections"] += 1
            project["total_resources"] += len(collection.resources)
        
        return list(projects.values())
    
    @mcp.resource("service-collections://{collection_id}")
    async def get_collection_resource(collection_id: str) -> Dict[str, Any]:
        """Get details of a specific service collection."""
        collection = collection_store.get(collection_id)
        if not collection:
            raise ValueError(f"Service collection {collection_id} not found")
        
        return {
            "id": collection.id,
            "name": collection.name,
            "project": collection.project,
            "environment": collection.environment.value,
            "description": collection.description,
            "resources": [
                {
                    "type": r.resource_type.value,
                    "id": r.resource_id,
                    "name": r.resource_name,
                    "tags": r.tags,
                    "created_at": r.created_at.isoformat(),
                    "metadata": r.metadata,
                }
                for r in collection.resources
            ],
            "workflows": [
                {
                    "id": w.id,
                    "name": w.name,
                    "description": w.description,
                    "triggers": [t.value for t in w.triggers],
                    "enabled": w.enabled,
                    "created_at": w.created_at.isoformat(),
                }
                for w in collection.workflows
            ],
            "permissions": {
                "owners": list(collection.owners),
                "editors": list(collection.editors),
                "viewers": list(collection.viewers),
            },
            "created_at": collection.created_at.isoformat(),
            "updated_at": collection.updated_at.isoformat(),
            "created_by": collection.created_by,
            "region": collection.region,
            "tags": collection.tags,
        }
    
    # Service Collection management tools
    @mcp.tool
    async def create_collection(
        name: str,
        project: str,
        environment: str,
        ctx: Context | None = None,
        description: str = "",
        region: str | None = None,
        tags: Dict[str, str] | None = None,
        created_by: str | None = None,
    ) -> Dict[str, Any]:
        """Create a new service collection.
        
        Args:
            name: Name for the service collection
            project: Project name to group collections
            environment: Environment (development, testing, staging, production, or custom)
            ctx: FastMCP context for resource change notifications
            description: Optional description
            region: Vultr region for resources
            tags: Optional tags for organization
            created_by: User who created the collection
            
        Returns:
            Created service collection details
        """
        # Validate environment
        try:
            env = Environment(environment.lower())
        except ValueError:
            # Allow custom environments
            env = environment.lower()
        
        collection = ServiceCollection(
            name=name,
            project=project,
            environment=env,
            description=description,
            region=region,
            tags=tags or {},
            created_by=created_by,
        )
        
        # Set creator as owner
        if created_by:
            collection.owners.add(created_by)
        
        collection_store.save(collection)
        
        # Notify clients that service collection list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, 
                operation="create_service_collection", 
                collection_id=collection.id
            )
        
        return {
            "id": collection.id,
            "name": collection.name,
            "project": collection.project,
            "environment": collection.environment,
            "description": collection.description,
            "created_at": collection.created_at.isoformat(),
        }
    
    @mcp.tool
    async def add_resource_to_collection(
        collection_id: str,
        resource_type: str,
        resource_id: str,
        ctx: Context | None = None,
        resource_name: str | None = None,
        tags: Dict[str, str] | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, str]:
        """Add a Vultr resource to a service collection.
        
        Args:
            collection_id: ID of the service collection
            resource_type: Type of resource (instance, domain, etc.)
            resource_id: Vultr resource ID
            ctx: FastMCP context for resource change notifications
            resource_name: Human-readable name for the resource
            tags: Optional tags for the resource
            metadata: Additional metadata for the resource
            
        Returns:
            Success confirmation
        """
        collection = collection_store.get(collection_id)
        if not collection:
            raise ValueError(f"Service collection {collection_id} not found")
        
        try:
            res_type = ResourceType(resource_type.lower())
        except ValueError:
            raise ValueError(f"Invalid resource type: {resource_type}")
        
        resource_ref = ResourceReference(
            resource_type=res_type,
            resource_id=resource_id,
            resource_name=resource_name,
            tags=tags or {},
            metadata=metadata or {},
        )
        
        collection.add_resource(resource_ref)
        collection_store.save(collection)
        
        # Notify clients that collection has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx,
                operation="update_service_collection",
                collection_id=collection_id
            )
        
        return {
            "success": True,
            "message": f"Added {resource_type} {resource_id} to collection {collection.name}",
            "collection_id": collection_id,
            "resource_count": len(collection.resources),
        }
    
    @mcp.tool
    async def remove_resource_from_collection(
        collection_id: str,
        resource_type: str,
        resource_id: str,
        ctx: Context | None = None,
    ) -> Dict[str, str]:
        """Remove a resource from a service collection.
        
        Args:
            collection_id: ID of the service collection
            resource_type: Type of resource to remove
            resource_id: Vultr resource ID to remove
            ctx: FastMCP context for resource change notifications
            
        Returns:
            Success confirmation
        """
        collection = collection_store.get(collection_id)
        if not collection:
            raise ValueError(f"Service collection {collection_id} not found")
        
        try:
            res_type = ResourceType(resource_type.lower())
        except ValueError:
            raise ValueError(f"Invalid resource type: {resource_type}")
        
        removed = collection.remove_resource(res_type, resource_id)
        if not removed:
            raise ValueError(f"Resource {resource_type}:{resource_id} not found in collection")
        
        collection_store.save(collection)
        
        # Notify clients that collection has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx,
                operation="update_service_collection",
                collection_id=collection_id
            )
        
        return {
            "success": True,
            "message": f"Removed {resource_type} {resource_id} from collection {collection.name}",
            "collection_id": collection_id,
            "resource_count": len(collection.resources),
        }
    
    @mcp.tool
    async def list_collections_by_project(
        project: str,
        environment: str | None = None,
    ) -> List[Dict[str, Any]]:
        """List service collections for a specific project.
        
        Args:
            project: Project name to filter by
            environment: Optional environment filter
            
        Returns:
            List of matching service collections
        """
        collections = collection_store.list_by_project(project)
        
        if environment:
            try:
                env_filter = Environment(environment.lower())
                collections = [c for c in collections if c.environment == env_filter]
            except ValueError:
                # Custom environment
                collections = [c for c in collections if c.environment == environment.lower()]
        
        return [
            {
                "id": c.id,
                "name": c.name,
                "environment": c.environment.value if isinstance(c.environment, Environment) else c.environment,
                "description": c.description,
                "resource_count": len(c.resources),
                "workflow_count": len(c.workflows),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                "region": c.region,
                "tags": c.tags,
            }
            for c in collections
        ]
    
    @mcp.tool
    async def promote_collection_environment(
        collection_id: str,
        target_environment: str,
        ctx: Context | None = None,
        copy_resources: bool = False,
        workflow_triggers: bool = True,
    ) -> Dict[str, Any]:
        """Promote a service collection to a different environment.
        
        Args:
            collection_id: ID of the collection to promote
            target_environment: Target environment (development, testing, staging, production)
            ctx: FastMCP context for resource change notifications
            copy_resources: Whether to copy resources to new environment
            workflow_triggers: Whether to trigger promotion workflows
            
        Returns:
            Details of the promotion operation
        """
        source_collection = collection_store.get(collection_id)
        if not source_collection:
            raise ValueError(f"Service collection {collection_id} not found")
        
        try:
            target_env = Environment(target_environment.lower())
        except ValueError:
            # Allow custom environments
            target_env = target_environment.lower()
        
        # Create new collection in target environment
        promoted_collection = ServiceCollection(
            name=source_collection.name,
            project=source_collection.project,
            environment=target_env,
            description=f"Promoted from {source_collection.environment.value if isinstance(source_collection.environment, Environment) else source_collection.environment}",
            tags=source_collection.tags.copy(),
            region=source_collection.region,
            owners=source_collection.owners.copy(),
            editors=source_collection.editors.copy(),
            viewers=source_collection.viewers.copy(),
        )
        
        if copy_resources:
            # Copy resource references (not actual resources)
            for resource in source_collection.resources:
                new_resource = ResourceReference(
                    resource_type=resource.resource_type,
                    resource_id=resource.resource_id,
                    resource_name=resource.resource_name,
                    tags=resource.tags.copy(),
                    metadata=resource.metadata.copy(),
                )
                promoted_collection.add_resource(new_resource)
        
        collection_store.save(promoted_collection)
        
        # Trigger promotion workflows if enabled
        if workflow_triggers:
            for workflow in source_collection.workflows:
                if workflow.can_trigger(
                    WorkflowTrigger.ENVIRONMENT_PROMOTED,
                    {
                        "source_environment": source_collection.environment,
                        "target_environment": target_env,
                        "collection_id": collection_id,
                        "promoted_collection_id": promoted_collection.id,
                    }
                ):
                    # Here you would execute the workflow
                    # For now, just log it
                    pass
        
        # Notify clients
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx,
                operation="create_service_collection",
                collection_id=promoted_collection.id
            )
        
        return {
            "success": True,
            "source_collection_id": collection_id,
            "promoted_collection_id": promoted_collection.id,
            "source_environment": source_collection.environment.value if isinstance(source_collection.environment, Environment) else source_collection.environment,
            "target_environment": target_env.value if isinstance(target_env, Environment) else target_env,
            "resources_copied": len(promoted_collection.resources) if copy_resources else 0,
            "workflows_triggered": sum(1 for w in source_collection.workflows 
                                     if w.can_trigger(WorkflowTrigger.ENVIRONMENT_PROMOTED, {})),
        }
    
    @mcp.tool
    async def update_collection_permissions(
        collection_id: str,
        user_id: str,
        permission_level: str,
        ctx: Context | None = None,
        action: str = "add",
    ) -> Dict[str, str]:
        """Update permissions for a service collection.
        
        Args:
            collection_id: ID of the service collection
            user_id: User ID to grant/revoke permissions
            permission_level: Permission level (owner, editor, viewer)
            ctx: FastMCP context for resource change notifications
            action: Action to take (add, remove)
            
        Returns:
            Success confirmation
        """
        collection = collection_store.get(collection_id)
        if not collection:
            raise ValueError(f"Service collection {collection_id} not found")
        
        # Remove user from all permission sets first
        collection.owners.discard(user_id)
        collection.editors.discard(user_id)
        collection.viewers.discard(user_id)
        
        if action == "add":
            if permission_level == "owner":
                collection.owners.add(user_id)
            elif permission_level == "editor":
                collection.editors.add(user_id)
            elif permission_level == "viewer":
                collection.viewers.add(user_id)
            else:
                raise ValueError(f"Invalid permission level: {permission_level}")
        
        collection_store.save(collection)
        
        # Notify clients that collection permissions have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx,
                operation="update_service_collection",
                collection_id=collection_id
            )
        
        return {
            "success": True,
            "message": f"{action.capitalize()}ed {permission_level} permission for {user_id}",
            "collection_id": collection_id,
            "user_id": user_id,
            "permission_level": permission_level if action == "add" else "none",
        }
    
    @mcp.tool
    async def delete_collection(
        collection_id: str,
        ctx: Context | None = None,
        force: bool = False,
    ) -> Dict[str, str]:
        """Delete a service collection.
        
        Args:
            collection_id: ID of the collection to delete
            ctx: FastMCP context for resource change notifications
            force: Force deletion even if collection has resources
            
        Returns:
            Success confirmation
        """
        collection = collection_store.get(collection_id)
        if not collection:
            raise ValueError(f"Service collection {collection_id} not found")
        
        if collection.resources and not force:
            raise ValueError(
                f"Collection {collection.name} contains {len(collection.resources)} resources. "
                "Use force=True to delete anyway."
            )
        
        deleted = collection_store.delete(collection_id)
        if not deleted:
            raise ValueError(f"Failed to delete collection {collection_id}")
        
        # Notify clients that collection list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx,
                operation="delete_service_collection",
                collection_id=collection_id
            )
        
        return {
            "success": True,
            "message": f"Deleted service collection {collection.name}",
            "collection_id": collection_id,
            "resources_removed": len(collection.resources),
        }
    
    return mcp
"""
Service Collections CLI commands for Vultr MCP.

Provides command-line interface for managing service collections,
environments, and workflow orchestration.
"""

import json
from typing import Dict, Any, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..service_collections import (
    ServiceCollection,
    ServiceCollectionStore,
    ResourceReference,
    ResourceType,
    Environment,
    create_service_collections_mcp,
)
from ..server import VultrDNSServer

console = Console()


@click.group(name="collections")
@click.pass_context
def collections_cli(ctx):
    """Service Collections - Enterprise infrastructure organization."""
    pass


@collections_cli.command()
@click.option("--project", help="Filter by project name")
@click.option("--environment", help="Filter by environment")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def list(ctx, project: str, environment: str, format: str):
    """List service collections."""
    api_key = ctx.obj.get("api_key")
    if not api_key:
        console.print("❌ VULTR_API_KEY not found", style="red")
        return
    
    try:
        vultr_client = VultrDNSServer(api_key)
        store = ServiceCollectionStore()
        
        # Get collections (in real implementation, would load from persistent storage)
        collections = store.list_all()
        
        # Apply filters
        if project:
            collections = [c for c in collections if c.project == project]
        if environment:
            collections = [c for c in collections if 
                         (c.environment.value if isinstance(c.environment, Environment) else c.environment) == environment]
        
        if format == "json":
            output = []
            for collection in collections:
                output.append({
                    "id": collection.id,
                    "name": collection.name,
                    "project": collection.project,
                    "environment": collection.environment.value if isinstance(collection.environment, Environment) else collection.environment,
                    "description": collection.description,
                    "resource_count": len(collection.resources),
                    "workflow_count": len(collection.workflows),
                    "created_at": collection.created_at.isoformat(),
                })
            console.print(json.dumps(output, indent=2))
        else:
            table = Table(title="Service Collections")
            table.add_column("Project", style="cyan")
            table.add_column("Environment", style="green")
            table.add_column("Name", style="yellow")
            table.add_column("Resources", justify="right")
            table.add_column("Workflows", justify="right")
            table.add_column("Created", style="dim")
            
            for collection in collections:
                env_name = collection.environment.value if isinstance(collection.environment, Environment) else collection.environment
                table.add_row(
                    collection.project,
                    env_name,
                    collection.name,
                    str(len(collection.resources)),
                    str(len(collection.workflows)),
                    collection.created_at.strftime("%Y-%m-%d"),
                )
            
            console.print(table)
            
            if not collections:
                console.print("No service collections found", style="yellow")
    
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")


@collections_cli.command()
@click.argument("name")
@click.argument("project")
@click.argument("environment")
@click.option("--description", help="Collection description")
@click.option("--region", help="Primary Vultr region")
@click.option("--created-by", help="Creator identifier")
@click.pass_context
def create(ctx, name: str, project: str, environment: str, description: str, region: str, created_by: str):
    """Create a new service collection."""
    api_key = ctx.obj.get("api_key")
    if not api_key:
        console.print("❌ VULTR_API_KEY not found", style="red")
        return
    
    try:
        vultr_client = VultrDNSServer(api_key)
        store = ServiceCollectionStore()
        
        # Validate environment
        try:
            env = Environment(environment.lower())
        except ValueError:
            env = environment.lower()  # Allow custom environments
        
        collection = ServiceCollection(
            name=name,
            project=project,
            environment=env,
            description=description or "",
            region=region,
            created_by=created_by,
        )
        
        if created_by:
            collection.owners.add(created_by)
        
        store.save(collection)
        
        console.print(Panel.fit(
            f"✅ Created service collection: [bold]{collection}[/bold]\\n"
            f"ID: {collection.id}\\n"
            f"Created: {collection.created_at.strftime('%Y-%m-%d %H:%M')}",
            title="Service Collection Created",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"❌ Error creating collection: {e}", style="red")


@collections_cli.command()
@click.argument("collection_id")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def show(ctx, collection_id: str, format: str):
    """Show detailed information about a service collection."""
    api_key = ctx.obj.get("api_key")
    if not api_key:
        console.print("❌ VULTR_API_KEY not found", style="red")
        return
    
    try:
        vultr_client = VultrDNSServer(api_key)
        store = ServiceCollectionStore()
        
        collection = store.get(collection_id)
        if not collection:
            console.print(f"❌ Collection {collection_id} not found", style="red")
            return
        
        if format == "json":
            output = {
                "id": collection.id,
                "name": collection.name,
                "project": collection.project,
                "environment": collection.environment.value if isinstance(collection.environment, Environment) else collection.environment,
                "description": collection.description,
                "region": collection.region,
                "created_by": collection.created_by,
                "created_at": collection.created_at.isoformat(),
                "updated_at": collection.updated_at.isoformat(),
                "resources": [
                    {
                        "type": r.resource_type.value,
                        "id": r.resource_id,
                        "name": r.resource_name,
                        "tags": r.tags,
                        "metadata": r.metadata,
                    }
                    for r in collection.resources
                ],
                "workflows": [
                    {
                        "id": w.id,
                        "name": w.name,
                        "description": w.description,
                        "enabled": w.enabled,
                    }
                    for w in collection.workflows
                ],
                "permissions": {
                    "owners": list(collection.owners),
                    "editors": list(collection.editors),
                    "viewers": list(collection.viewers),
                },
            }
            console.print(json.dumps(output, indent=2))
        else:
            env_name = collection.environment.value if isinstance(collection.environment, Environment) else collection.environment
            console.print(Panel.fit(
                f"[bold]{collection.name}[/bold] ({collection.project})\\n"
                f"Environment: [green]{env_name}[/green]\\n"
                f"Description: {collection.description}\\n"
                f"Region: {collection.region}\\n"
                f"Created: {collection.created_at.strftime('%Y-%m-%d %H:%M')} by {collection.created_by}",
                title=f"Collection: {collection_id[:8]}...",
                border_style="blue"
            ))
            
            if collection.resources:
                console.print("\\n📦 Resources:")
                resource_table = Table()
                resource_table.add_column("Type")
                resource_table.add_column("ID")
                resource_table.add_column("Name")
                resource_table.add_column("Tags")
                
                for resource in collection.resources:
                    tags_str = ", ".join(f"{k}={v}" for k, v in resource.tags.items())
                    resource_table.add_row(
                        resource.resource_type.value,
                        resource.resource_id,
                        resource.resource_name or "",
                        tags_str,
                    )
                
                console.print(resource_table)
            
            if collection.workflows:
                console.print("\\n⚙️  Workflows:")
                workflow_table = Table()
                workflow_table.add_column("Name")
                workflow_table.add_column("Description")
                workflow_table.add_column("Status")
                
                for workflow in collection.workflows:
                    status = "✅ Enabled" if workflow.enabled else "❌ Disabled"
                    workflow_table.add_row(
                        workflow.name,
                        workflow.description,
                        status,
                    )
                
                console.print(workflow_table)
            
            console.print("\\n🔐 Permissions:")
            perm_table = Table()
            perm_table.add_column("Role")
            perm_table.add_column("Users")
            
            perm_table.add_row("Owners", ", ".join(collection.owners) or "None")
            perm_table.add_row("Editors", ", ".join(collection.editors) or "None")
            perm_table.add_row("Viewers", ", ".join(collection.viewers) or "None")
            
            console.print(perm_table)
    
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")


@collections_cli.command()
@click.argument("collection_id")
@click.argument("resource_type")
@click.argument("resource_id")
@click.option("--name", help="Human-readable name for the resource")
@click.option("--tags", help="Tags as JSON object")
@click.pass_context
def add_resource(ctx, collection_id: str, resource_type: str, resource_id: str, name: str, tags: str):
    """Add a Vultr resource to a service collection."""
    api_key = ctx.obj.get("api_key")
    if not api_key:
        console.print("❌ VULTR_API_KEY not found", style="red")
        return
    
    try:
        vultr_client = VultrDNSServer(api_key)
        store = ServiceCollectionStore()
        
        collection = store.get(collection_id)
        if not collection:
            console.print(f"❌ Collection {collection_id} not found", style="red")
            return
        
        try:
            res_type = ResourceType(resource_type.lower())
        except ValueError:
            console.print(f"❌ Invalid resource type: {resource_type}", style="red")
            console.print(f"Valid types: {', '.join([rt.value for rt in ResourceType])}")
            return
        
        # Parse tags if provided
        resource_tags = {}
        if tags:
            try:
                resource_tags = json.loads(tags)
            except json.JSONDecodeError:
                console.print("❌ Invalid JSON for tags", style="red")
                return
        
        resource_ref = ResourceReference(
            resource_type=res_type,
            resource_id=resource_id,
            resource_name=name,
            tags=resource_tags,
        )
        
        collection.add_resource(resource_ref)
        store.save(collection)
        
        console.print(f"✅ Added {resource_type} {resource_id} to collection {collection.name}", style="green")
    
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")


@collections_cli.command()
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def projects(ctx, format: str):
    """List all projects with environment breakdown."""
    api_key = ctx.obj.get("api_key")
    if not api_key:
        console.print("❌ VULTR_API_KEY not found", style="red")
        return
    
    try:
        vultr_client = VultrDNSServer(api_key)
        store = ServiceCollectionStore()
        
        # Calculate project statistics
        projects = {}
        for collection in store.list_all():
            if collection.project not in projects:
                projects[collection.project] = {
                    "name": collection.project,
                    "environments": {},
                    "total_collections": 0,
                    "total_resources": 0,
                }
            
            project = projects[collection.project]
            env_key = collection.environment.value if isinstance(collection.environment, Environment) else collection.environment
            
            if env_key not in project["environments"]:
                project["environments"][env_key] = {"collections": 0, "resources": 0}
            
            project["environments"][env_key]["collections"] += 1
            project["environments"][env_key]["resources"] += len(collection.resources)
            project["total_collections"] += 1
            project["total_resources"] += len(collection.resources)
        
        if format == "json":
            console.print(json.dumps(list(projects.values()), indent=2))
        else:
            table = Table(title="Projects Overview")
            table.add_column("Project", style="cyan")
            table.add_column("Environments")
            table.add_column("Collections", justify="right")
            table.add_column("Resources", justify="right")
            
            for project in projects.values():
                env_list = []
                for env, stats in project["environments"].items():
                    env_list.append(f"{env} ({stats['collections']}c, {stats['resources']}r)")
                
                table.add_row(
                    project["name"],
                    "\\n".join(env_list),
                    str(project["total_collections"]),
                    str(project["total_resources"]),
                )
            
            console.print(table)
    
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")


# Helper function to validate resource types
def get_valid_resource_types() -> List[str]:
    """Get list of valid resource types."""
    return [rt.value for rt in ResourceType]


# Helper function to validate environments
def get_valid_environments() -> List[str]:
    """Get list of standard environments."""
    return [env.value for env in Environment]
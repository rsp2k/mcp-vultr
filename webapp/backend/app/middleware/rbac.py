"""Role-Based Access Control (RBAC) middleware for project-scoped access."""

from typing import Optional, List, Callable, Any
from uuid import UUID
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, text

from app.core.database import get_db
from app.api.auth import require_auth
from app.models import User, Project, ProjectRole, ProjectStatus
from app.models.project import project_members


# Role hierarchy for permission checking
ROLE_HIERARCHY = {
    ProjectRole.VIEWER: 1,
    ProjectRole.DEVELOPER: 2,
    ProjectRole.MANAGER: 3,
    ProjectRole.ADMIN: 4,
    ProjectRole.OWNER: 5
}


class ProjectAccessControl:
    """Helper class for project-based access control."""

    @staticmethod
    async def check_project_access(
        project_id: UUID,
        user: User,
        db: AsyncSession,
        required_role: ProjectRole = ProjectRole.VIEWER,
        allow_admin_override: bool = True
    ) -> Project:
        """
        Check if user has required access to project.

        Args:
            project_id: ID of the project to check
            user: User making the request
            db: Database session
            required_role: Minimum required role for access
            allow_admin_override: Allow admin users to bypass role requirements

        Returns:
            Project object if access is granted

        Raises:
            HTTPException: If project not found or access denied
        """
        # Get the project using raw SQL to avoid enum issues
        project_sql = text("""
            SELECT id, name, slug, description, status, color,
                   avatar_url, owner_id, created_at, updated_at, settings
            FROM projects
            WHERE id = :project_id
        """)
        result = await db.execute(project_sql, {"project_id": project_id})
        row = result.fetchone()

        if not row:
            project = None
        else:
            project_data = {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "description": row.description,
                "status": row.status,
                "color": row.color,
                "avatar_url": row.avatar_url,
                "owner_id": row.owner_id,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "settings": row.settings
            }
            project = Project(**project_data)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Admin override
        if allow_admin_override and user.is_admin:
            return project

        # Check if user has required access to project
        if not project.can_user_access(user.id, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have {required_role.value} access to this project"
            )

        return project

    @staticmethod
    async def get_user_accessible_projects(
        user: User,
        db: AsyncSession,
        min_role: ProjectRole = ProjectRole.VIEWER
    ) -> List[Project]:
        """
        Get all projects user has access to with at least the minimum role.

        Args:
            user: User to check access for
            db: Database session
            min_role: Minimum role required

        Returns:
            List of accessible projects
        """
        # Admin users can access all projects
        if user.is_admin:
            projects_sql = text("""
                SELECT DISTINCT id, name, slug, description, status, color,
                       avatar_url, owner_id, created_at, updated_at, settings
                FROM projects
            """)
            result = await db.execute(projects_sql)

            # Convert raw results to Project objects
            projects = []
            for row in result:
                # Handle status conversion carefully
                if isinstance(row.status, str):
                    status_value = ProjectStatus(row.status.lower())
                else:
                    # Already an enum, convert to string first then back to enum to ensure consistency
                    status_value = ProjectStatus(str(row.status).lower())

                project_data = {
                    "id": row.id,
                    "name": row.name,
                    "slug": row.slug,
                    "description": row.description,
                    "status": status_value,
                    "color": row.color,
                    "avatar_url": row.avatar_url,
                    "owner_id": row.owner_id,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "settings": row.settings
                }
                projects.append(Project(**project_data))
            return projects

        # Use completely raw SQL to avoid all SQLAlchemy enum issues
        # Simply get all projects where user is owner OR member (regardless of role)
        # Note: Using DISTINCT ON (p.id) to handle potential duplicates from JOIN while including JSON settings
        projects_sql = text("""
            SELECT DISTINCT ON (p.id) p.id, p.name, p.slug, p.description, p.status, p.color,
                   p.avatar_url, p.owner_id, p.created_at, p.updated_at, p.settings
            FROM projects p
            LEFT JOIN project_members pm ON p.id = pm.project_id
            WHERE (
                -- User is project owner
                p.owner_id = :user_id
                OR
                -- User is a member (any role - we'll handle role hierarchy in application layer)
                pm.user_id = :user_id
            )
            ORDER BY p.id
        """)

        result = await db.execute(projects_sql, {"user_id": user.id})

        # Convert raw results to Project objects
        projects = []
        for row in result:
            # Handle status conversion carefully
            if isinstance(row.status, str):
                status_value = ProjectStatus(row.status.lower())
            else:
                # Already an enum, convert to string first then back to enum to ensure consistency
                status_value = ProjectStatus(str(row.status).lower())

            project = Project(
                id=row.id, name=row.name, slug=row.slug, description=row.description,
                status=status_value, color=row.color, avatar_url=row.avatar_url,
                owner_id=row.owner_id, created_at=row.created_at, updated_at=row.updated_at,
                settings=row.settings
            )
            projects.append(project)

        return projects

    @staticmethod
    async def filter_by_project_access(
        query: Any,
        user: User,
        db: AsyncSession,
        project_id_column: str = 'project_id',
        min_role: ProjectRole = ProjectRole.VIEWER
    ) -> Any:
        """
        Filter a SQLAlchemy query to only include records from projects the user has access to.

        Args:
            query: SQLAlchemy query to filter
            user: User making the request
            db: Database session
            project_id_column: Name of the project_id column to filter on
            min_role: Minimum role required for access

        Returns:
            Filtered query
        """
        if user.is_admin:
            # Admin can access all projects
            return query

        # Get accessible project IDs
        accessible_projects = await ProjectAccessControl.get_user_accessible_projects(
            user, db, min_role
        )
        accessible_project_ids = [p.id for p in accessible_projects]

        if not accessible_project_ids:
            # No accessible projects - return empty result
            return query.where(False)

        # Filter by accessible projects
        return query.where(
            getattr(query.column_descriptions[0]['entity'], project_id_column).in_(
                accessible_project_ids
            )
        )


def require_project_access(
    required_role: ProjectRole = ProjectRole.VIEWER,
    allow_admin_override: bool = True
) -> Callable:
    """
    Dependency factory for project-based access control.

    Args:
        required_role: Minimum required role for access
        allow_admin_override: Allow admin users to bypass role requirements

    Returns:
        FastAPI dependency function

    Usage:
        @router.get("/projects/{project_id}/collections")
        async def list_collections(
            project_id: UUID,
            project: Project = Depends(require_project_access(ProjectRole.VIEWER))
        ):
            # project is guaranteed to be accessible by user
            ...
    """
    async def project_access_dependency(
        project_id: UUID,
        current_user: User = Depends(require_auth),
        db: AsyncSession = Depends(get_db)
    ) -> Project:
        return await ProjectAccessControl.check_project_access(
            project_id, current_user, db, required_role, allow_admin_override
        )

    return project_access_dependency


def require_project_role(role: ProjectRole) -> Callable:
    """
    Simplified dependency for requiring specific project role.

    Args:
        role: Required project role

    Returns:
        FastAPI dependency function
    """
    return require_project_access(required_role=role, allow_admin_override=True)


# Convenience dependencies for common role requirements
require_project_viewer = require_project_role(ProjectRole.VIEWER)
require_project_developer = require_project_role(ProjectRole.DEVELOPER)
require_project_manager = require_project_role(ProjectRole.MANAGER)
require_project_admin = require_project_role(ProjectRole.ADMIN)
require_project_owner = require_project_role(ProjectRole.OWNER)


class CollectionAccessControl:
    """Access control specifically for service collections within projects."""

    @staticmethod
    async def check_collection_project_access(
        collection_id: UUID,
        user: User,
        db: AsyncSession,
        required_project_role: ProjectRole = ProjectRole.VIEWER,
        required_collection_permission: str = "read"
    ) -> tuple[Any, Project]:
        """
        Check access to a collection considering both project and collection-level permissions.

        Args:
            collection_id: ID of the collection to check
            user: User making the request
            db: Database session
            required_project_role: Minimum project role required
            required_collection_permission: Collection permission required (read, write, manage)

        Returns:
            Tuple of (collection, project) if access is granted

        Raises:
            HTTPException: If collection not found or access denied
        """
        from app.models import ServiceCollection

        # Get the collection using raw SQL to avoid enum issues
        collection_sql = text("""
            SELECT id, name, description, environment, status, project_id,
                   created_by, owner_email, vultr_service_user,
                   allowed_regions, cost_budget_monthly,
                   members, permissions,
                   approval_required, auto_approve_operations, restricted_operations,
                   tags, configuration,
                   created_at, updated_at, archived_at
            FROM service_collections
            WHERE id = :collection_id
        """)
        result = await db.execute(collection_sql, {"collection_id": collection_id})
        row = result.fetchone()

        if not row:
            collection = None
        else:
            collection_data = {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "environment": row.environment,
                "status": row.status,
                "project_id": row.project_id,
                "created_by": row.created_by,
                "owner_email": row.owner_email,
                "vultr_service_user": row.vultr_service_user,
                "allowed_regions": row.allowed_regions or [],
                "cost_budget_monthly": row.cost_budget_monthly,
                "members": row.members or [],
                "permissions": row.permissions or {},
                "approval_required": row.approval_required,
                "auto_approve_operations": row.auto_approve_operations or [],
                "restricted_operations": row.restricted_operations or [],
                "tags": row.tags or {},
                "configuration": row.configuration or {},
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "archived_at": row.archived_at
            }
            collection = ServiceCollection(**collection_data)

        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service Collection not found"
            )

        # Check project access first
        project = await ProjectAccessControl.check_project_access(
            collection.project_id,
            user,
            db,
            required_project_role
        )

        # Check collection-level permissions
        if not collection.can_user_access(user.email, required_collection_permission) and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have {required_collection_permission} permission for this collection"
            )

        return collection, project


def has_minimum_role(user_role: ProjectRole, required_role: ProjectRole) -> bool:
    """
    Check if user role meets minimum requirement.

    Args:
        user_role: Role the user has
        required_role: Minimum role required

    Returns:
        True if user role is sufficient
    """
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)


async def enforce_project_context(
    user: User,
    db: AsyncSession,
    project_id: Optional[UUID] = None,
    min_role: ProjectRole = ProjectRole.VIEWER
) -> Optional[UUID]:
    """
    Enforce project context for API operations.

    If project_id is provided, verify access.
    If not provided and user has access to only one project, use that.

    Args:
        user: User making the request
        db: Database session
        project_id: Optional specific project ID
        min_role: Minimum role required

    Returns:
        Project ID to use for the operation

    Raises:
        HTTPException: If no valid project context can be determined
    """
    if project_id:
        # Verify access to specified project
        await ProjectAccessControl.check_project_access(
            project_id, user, db, min_role
        )
        return project_id

    # Get all accessible projects
    accessible_projects = await ProjectAccessControl.get_user_accessible_projects(
        user, db, min_role
    )

    if not accessible_projects:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to any projects"
        )

    if len(accessible_projects) == 1:
        # Only one project - use it
        return accessible_projects[0].id

    # Multiple projects - require explicit specification
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Multiple projects available - please specify project_id"
    )
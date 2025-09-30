"""Project Management API routes."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, field_validator

from app.core.database import get_db
from app.api.auth import require_auth
from app.models import (
    Project, ProjectInvitation, AuditLog, ProjectStatus, ProjectRole,
    User, UserRole, UserStatus, AuditLogEntry, AuditAction, AuditSeverity
)

router = APIRouter(prefix="/projects", tags=["projects"])


# Pydantic models for request/response
class ProjectCreate(BaseModel):
    """Project creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r'^[a-z0-9-]+$')
    description: Optional[str] = Field(None, max_length=1000)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    avatar_url: Optional[str] = Field(None, max_length=512)
    settings: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('slug', mode='before')
    @classmethod
    def generate_slug(cls, v, info):
        if not v and info.data and 'name' in info.data:
            # Generate slug from name
            slug = info.data['name'].lower()
            slug = ''.join(c if c.isalnum() or c == '-' else '-' for c in slug)
            slug = '-'.join(filter(None, slug.split('-')))
            return slug[:100]  # Ensure max length
        return v


class ProjectUpdate(BaseModel):
    """Project update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    avatar_url: Optional[str] = Field(None, max_length=512)
    settings: Optional[Dict[str, Any]] = None
    status: Optional[ProjectStatus] = None


class ProjectInvitationCreate(BaseModel):
    """Project invitation creation request."""
    email: str = Field(..., min_length=1, max_length=255)
    role: ProjectRole = ProjectRole.VIEWER


class ProjectInvitationUpdate(BaseModel):
    """Project invitation update request."""
    role: ProjectRole


class ProjectMemberUpdate(BaseModel):
    """Project member role update request."""
    role: ProjectRole


class ProjectResponse(BaseModel):
    """Project response model."""
    id: str
    name: str
    slug: str
    description: Optional[str]
    status: str
    color: Optional[str]
    avatar_url: Optional[str]
    owner_id: str
    created_at: str
    updated_at: str
    settings: Dict[str, Any]
    member_count: int
    collection_count: int
    user_role: Optional[str] = None  # Current user's role in project

    model_config = {"from_attributes": True}


class ProjectMemberResponse(BaseModel):
    """Project member response model."""
    user_id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    added_at: str
    is_owner: bool

    model_config = {"from_attributes": True}


class ProjectInvitationResponse(BaseModel):
    """Project invitation response model."""
    id: str
    project_id: str
    project_name: Optional[str]
    email: str
    role: str
    accepted: bool
    accepted_at: Optional[str]
    invited_by: Optional[Dict[str, Any]]
    created_at: str
    expires_at: str
    is_expired: bool
    is_pending: bool

    model_config = {"from_attributes": True}


# Helper functions
def generate_invitation_token() -> str:
    """Generate a secure invitation token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))


async def get_user_role_in_project(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID
) -> Optional[ProjectRole]:
    """Get user's role in a project."""
    # Check if user is the owner using raw SQL to avoid enum casting issues
    from sqlalchemy import text
    owner_result = await db.execute(
        text("SELECT owner_id FROM projects WHERE id = :project_id"),
        {"project_id": project_id}
    )
    owner_row = owner_result.first()
    if owner_row and owner_row[0] == user_id:
        return ProjectRole.OWNER

    # Check project_members table with raw SQL to avoid enum casting issues
    result = await db.execute(
        text("SELECT role FROM project_members WHERE project_id = :project_id AND user_id = :user_id"),
        {"project_id": project_id, "user_id": user_id}
    )
    role_row = result.first()
    if role_row:
        # Convert string role back to enum
        return ProjectRole(role_row[0])
    return None


async def check_project_permission(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    required_role: ProjectRole = ProjectRole.VIEWER
) -> bool:
    """Check if user has required permission level in project."""
    user_role = await get_user_role_in_project(db, project_id, user_id)
    if not user_role:
        return False

    # Define role hierarchy (higher number = more permissions)
    role_hierarchy = {
        ProjectRole.VIEWER: 1,
        ProjectRole.DEVELOPER: 2,
        ProjectRole.MANAGER: 3,
        ProjectRole.ADMIN: 4,
        ProjectRole.OWNER: 5
    }

    return role_hierarchy[user_role] >= role_hierarchy[required_role]


async def log_project_audit(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    context_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log project audit event."""
    audit_log = AuditLog(
        project_id=project_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        old_values=old_values,
        new_values=new_values,
        context_data=context_data,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit_log)
    await db.commit()


# API Endpoints
@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[ProjectStatus] = Query(None, description="Filter by project status"),
    search: Optional[str] = Query(None, description="Search projects by name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List projects accessible to the current user.

    Returns projects where the user is either:
    - The owner
    - A project member with any role
    """
    # Use raw SQL query to avoid enum casting issues entirely
    sql_conditions = []
    sql_params = {"user_id": current_user.id, "limit": limit, "offset": offset}

    # Base condition for user access
    sql_conditions.append("(p.owner_id = :user_id OR pm.user_id = :user_id)")

    # Add status filter if specified
    if status_filter:
        sql_conditions.append("p.status = :status_filter")
        sql_params["status_filter"] = status_filter.value

    # Add search filter if specified
    if search:
        sql_conditions.append("(p.name ILIKE :search_term OR p.description ILIKE :search_term)")
        sql_params["search_term"] = f"%{search}%"

    # Combine all conditions
    where_clause = " AND ".join(sql_conditions)

    projects_sql = text(f"""
        SELECT DISTINCT ON (p.id) p.id, p.name, p.slug, p.description, p.status, p.color,
               p.avatar_url, p.owner_id, p.created_at, p.updated_at, p.settings,
               (SELECT COUNT(*) FROM project_members WHERE project_id = p.id) + 1 as member_count,
               (SELECT COUNT(*) FROM service_collections WHERE project_id = p.id) as collection_count
        FROM projects p
        LEFT JOIN project_members pm ON p.id = pm.project_id
        WHERE {where_clause}
        ORDER BY p.id, p.updated_at DESC
        LIMIT :limit OFFSET :offset
    """)

    result = await db.execute(projects_sql, sql_params)

    # Convert raw results to Project response objects
    response_projects = []
    for row in result:
        # Get user role for each project
        user_role = await get_user_role_in_project(db, row.id, current_user.id)

        # Create project response
        project_dict = {
            'id': str(row.id),
            'name': row.name,
            'slug': row.slug,
            'description': row.description,
            'status': row.status.lower() if hasattr(row.status, 'lower') else row.status,
            'color': row.color,
            'avatar_url': row.avatar_url,
            'owner_id': str(row.owner_id),
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'updated_at': row.updated_at.isoformat() if row.updated_at else None,
            'settings': row.settings or {},
            'user_role': user_role.value if user_role else None,
            'member_count': row.member_count,
            'collection_count': row.collection_count
        }

        response_projects.append(ProjectResponse(**project_dict))

    return response_projects


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project.

    The current user becomes the project owner.
    """
    # Check if slug is already taken
    if project_data.slug:
        existing = await db.execute(
            select(Project).where(Project.slug == project_data.slug)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project slug '{project_data.slug}' is already taken"
            )

    # Create the project
    project = Project(
        name=project_data.name,
        slug=project_data.slug,
        description=project_data.description,
        color=project_data.color,
        avatar_url=project_data.avatar_url,
        settings=project_data.settings,
        owner_id=current_user.id,
        status=ProjectStatus.ACTIVE
    )

    db.add(project)
    await db.flush()  # Get the project ID

    # Log the creation
    await log_project_audit(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
        action="project.create",
        resource_type="project",
        resource_id=str(project.id),
        resource_name=project.name,
        new_values=project.to_dict()
    )

    await db.commit()

    # Return response with user role
    project_dict = project.to_dict()
    project_dict['user_role'] = ProjectRole.OWNER.value
    return ProjectResponse(**project_dict)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get project details."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check access
    if not await check_project_permission(db, project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get user's role and return response
    user_role = await get_user_role_in_project(db, project.id, current_user.id)
    project_dict = project.to_dict()
    project_dict['user_role'] = user_role.value if user_role else None
    return ProjectResponse(**project_dict)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update project details. Requires ADMIN or OWNER role."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check permission (ADMIN or OWNER required)
    if not await check_project_permission(db, project_id, current_user.id, ProjectRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Store old values for audit
    old_values = project.to_dict()

    # Update fields
    update_data = project_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    project.updated_at = datetime.utcnow()

    # Log the update
    await log_project_audit(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
        action="project.update",
        resource_type="project",
        resource_id=str(project.id),
        resource_name=project.name,
        old_values=old_values,
        new_values=project.to_dict()
    )

    await db.commit()

    # Return response with user role
    user_role = await get_user_role_in_project(db, project.id, current_user.id)
    project_dict = project.to_dict()
    project_dict['user_role'] = user_role.value if user_role else None
    return ProjectResponse(**project_dict)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete a project. Only project owners can delete projects."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Only owners can delete projects
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owners can delete projects"
        )

    # Log the deletion before deleting
    await log_project_audit(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
        action="project.delete",
        resource_type="project",
        resource_id=str(project.id),
        resource_name=project.name,
        old_values=project.to_dict()
    )

    # Delete the project (cascading will handle related records)
    await db.delete(project)
    await db.commit()


# Team Management Endpoints
@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def list_project_members(
    project_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List project members. Requires VIEWER access or higher."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check access
    if not await check_project_permission(db, project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get all project members including owner
    from app.models.project import project_members

    # Get owner
    owner_result = await db.execute(
        select(User).where(User.id == project.owner_id)
    )
    owner = owner_result.scalar_one_or_none()

    # Get other members with raw SQL to avoid enum casting issues
    from sqlalchemy import text
    members_result = await db.execute(
        text("""
            SELECT u.id, u.email, u.full_name, u.avatar_url, pm.role, pm.added_at
            FROM users u
            JOIN project_members pm ON u.id = pm.user_id
            WHERE pm.project_id = :project_id
        """),
        {"project_id": project_id}
    )
    members_data = members_result.all()

    # Build response
    response_members = []

    # Add owner
    if owner:
        response_members.append(ProjectMemberResponse(
            user_id=str(owner.id),
            email=owner.email,
            full_name=owner.full_name,
            avatar_url=owner.avatar_url,
            role=ProjectRole.OWNER.value,
            added_at=project.created_at.isoformat(),
            is_owner=True
        ))

    # Add other members
    for row in members_data:
        user_id, email, full_name, avatar_url, role_str, added_at = row
        response_members.append(ProjectMemberResponse(
            user_id=str(user_id),
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            role=role_str,  # Already a string from raw SQL
            added_at=added_at.isoformat() if added_at else project.created_at.isoformat(),
            is_owner=False
        ))

    return response_members


@router.put("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
async def update_project_member_role(
    project_id: UUID,
    user_id: UUID,
    member_update: ProjectMemberUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update a project member's role. Requires ADMIN access or higher."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check permission (ADMIN required)
    if not await check_project_permission(db, project_id, current_user.id, ProjectRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Cannot change owner's role
    if project.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change project owner's role"
        )

    # Check if user is a project member using raw SQL to avoid enum casting
    member_sql = text("""
        SELECT id, role FROM project_members
        WHERE project_id = :project_id AND user_id = :user_id
    """)
    member_result = await db.execute(member_sql, {"project_id": project_id, "user_id": user_id})
    existing_member = member_result.first()

    if not existing_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a project member"
        )

    # Get user details
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update role
    await db.execute(
        text("""
            UPDATE project_members
            SET role = :role, updated_at = :updated_at
            WHERE project_id = :project_id AND user_id = :user_id
        """),
        {
            "role": member_update.role.value,
            "updated_at": datetime.utcnow(),
            "project_id": str(project_id),
            "user_id": str(user_id)
        }
    )

    # Log the change
    await log_project_audit(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
        action="member.role_update",
        resource_type="member",
        resource_id=str(user_id),
        resource_name=user.email,
        old_values={"role": existing_member.role.value},
        new_values={"role": member_update.role.value}
    )

    await db.commit()

    return ProjectMemberResponse(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=member_update.role.value,
        added_at=existing_member.added_at.isoformat() if existing_member.added_at else project.created_at.isoformat(),
        is_owner=False
    )


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Remove a member from the project. Requires ADMIN access or higher."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check permission (ADMIN required)
    if not await check_project_permission(db, project_id, current_user.id, ProjectRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Cannot remove owner
    if project.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove project owner"
        )

    # Get user details for audit log
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Remove from project
    from app.models.project import project_members

    result = await db.execute(
        text("DELETE FROM project_members WHERE project_id = :project_id AND user_id = :user_id"),
        {"project_id": str(project_id), "user_id": str(user_id)}
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a project member"
        )

    # Log the removal
    await log_project_audit(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
        action="member.remove",
        resource_type="member",
        resource_id=str(user_id),
        resource_name=user.email,
        old_values={"email": user.email, "full_name": user.full_name}
    )

    await db.commit()


# Project Invitation Endpoints
@router.get("/{project_id}/invitations", response_model=List[ProjectInvitationResponse])
async def list_project_invitations(
    project_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, accepted, expired")
):
    """List project invitations. Requires ADMIN access or higher."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check permission (ADMIN required)
    if not await check_project_permission(db, project_id, current_user.id, ProjectRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Build query
    query = select(ProjectInvitation).options(
        selectinload(ProjectInvitation.project),
        selectinload(ProjectInvitation.invited_by)
    ).where(ProjectInvitation.project_id == project_id)

    # Apply status filter
    if status_filter == "pending":
        query = query.where(
            and_(
                ProjectInvitation.accepted == False,
                ProjectInvitation.expires_at > datetime.utcnow()
            )
        )
    elif status_filter == "accepted":
        query = query.where(ProjectInvitation.accepted == True)
    elif status_filter == "expired":
        query = query.where(
            and_(
                ProjectInvitation.accepted == False,
                ProjectInvitation.expires_at <= datetime.utcnow()
            )
        )

    query = query.order_by(ProjectInvitation.created_at.desc())

    result = await db.execute(query)
    invitations = result.scalars().all()

    return [ProjectInvitationResponse(**inv.to_dict()) for inv in invitations]


@router.post("/{project_id}/invitations", response_model=ProjectInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_project_invitation(
    project_id: UUID,
    invitation_data: ProjectInvitationCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Create a project invitation. Requires ADMIN access or higher."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check permission (ADMIN required)
    if not await check_project_permission(db, project_id, current_user.id, ProjectRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Check if user is already a member or has pending invitation
    existing_member_query = text("""
        SELECT 1 FROM project_members
        WHERE project_id = :project_id
        AND user_id = (SELECT id FROM users WHERE email = :email)
    """)
    existing_member_result = await db.execute(existing_member_query, {
        "project_id": str(project_id),
        "email": invitation_data.email
    })

    if existing_member_result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a project member"
        )

    # Check for existing pending invitation
    existing_invitation = await db.execute(
        select(ProjectInvitation).where(
            and_(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.email == invitation_data.email,
                ProjectInvitation.accepted == False,
                ProjectInvitation.expires_at > datetime.utcnow()
            )
        )
    )

    if existing_invitation.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a pending invitation"
        )

    # Create invitation
    invitation = ProjectInvitation(
        project_id=project_id,
        email=invitation_data.email,
        role=invitation_data.role,
        token=generate_invitation_token(),
        invited_by_user_id=current_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7)  # 7-day expiration
    )

    db.add(invitation)
    await db.flush()

    # Log the invitation
    await log_project_audit(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
        action="invitation.create",
        resource_type="invitation",
        resource_id=str(invitation.id),
        resource_name=invitation.email,
        new_values={
            "email": invitation.email,
            "role": invitation.role.value,
            "expires_at": invitation.expires_at.isoformat()
        }
    )

    await db.commit()

    return ProjectInvitationResponse(**invitation.to_dict())


@router.delete("/{project_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_project_invitation(
    project_id: UUID,
    invitation_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a project invitation. Requires ADMIN access or higher."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check permission (ADMIN required)
    if not await check_project_permission(db, project_id, current_user.id, ProjectRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Get invitation
    invitation = await db.get(ProjectInvitation, invitation_id)
    if not invitation or invitation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Log the cancellation
    await log_project_audit(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
        action="invitation.cancel",
        resource_type="invitation",
        resource_id=str(invitation.id),
        resource_name=invitation.email,
        old_values=invitation.to_dict()
    )

    await db.delete(invitation)
    await db.commit()


# Public invitation acceptance endpoint (no auth required)
@router.post("/invitations/{token}/accept", response_model=Dict[str, str])
async def accept_project_invitation(
    token: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Accept a project invitation using the invitation token."""
    # Find invitation by token
    invitation = await db.execute(
        select(ProjectInvitation).options(selectinload(ProjectInvitation.project))
        .where(ProjectInvitation.token == token)
    )
    invitation = invitation.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )

    # Check if invitation is still valid
    if invitation.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been accepted"
        )

    if invitation.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )

    # Check if email matches current user
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation email does not match authenticated user"
        )

    # Check if user is already a member
    existing_role = await get_user_role_in_project(db, invitation.project_id, current_user.id)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a project member"
        )

    # Accept invitation - add user to project
    from app.models.project import project_members

    await db.execute(
        text("""
            INSERT INTO project_members (id, project_id, user_id, role, added_by_user_id, added_at, updated_at)
            VALUES (:id, :project_id, :user_id, :role, :added_by_user_id, :added_at, :updated_at)
        """),
        {
            "id": str(uuid4()),
            "project_id": str(invitation.project_id),
            "user_id": str(current_user.id),
            "role": invitation.role.value,
            "added_by_user_id": str(invitation.invited_by_user_id),
            "added_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    )

    # Mark invitation as accepted
    invitation.accepted = True
    invitation.accepted_at = datetime.utcnow()
    invitation.accepted_by_user_id = current_user.id

    # Log the acceptance
    await log_project_audit(
        db=db,
        project_id=invitation.project_id,
        user_id=current_user.id,
        action="invitation.accept",
        resource_type="invitation",
        resource_id=str(invitation.id),
        resource_name=current_user.email,
        new_values={
            "role": invitation.role.value,
            "accepted_at": invitation.accepted_at.isoformat()
        }
    )

    await db.commit()

    return {
        "message": "Invitation accepted successfully",
        "project_id": str(invitation.project_id),
        "project_name": invitation.project.name,
        "role": invitation.role.value
    }
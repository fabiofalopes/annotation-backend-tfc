from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..database import get_db
from ..models import User, Project
from ..schemas import UserCreate, User as UserSchema, ProjectCreate, Project as ProjectSchema
from ..auth import get_current_admin_user

router = APIRouter()


@router.get("/users", response_model=List[UserSchema])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """List all users (admin only)"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users


@router.post("/users", response_model=UserSchema)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """Create a new user (admin only)"""
    # Check if user exists
    query = select(User).where(User.email == user_data.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    new_user = User(
        email=user_data.email,
        hashed_password=user_data.password,  # Will be hashed by the database trigger
        is_admin=user_data.is_admin
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.get("/projects", response_model=List[ProjectSchema])
async def list_all_projects(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """List all projects (admin only)"""
    result = await db.execute(select(Project))
    projects = result.scalars().all()
    return projects


@router.post("/projects", response_model=ProjectSchema)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """Create a new project (admin only)"""
    new_project = Project(**project_data.model_dump())
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a user (admin only)"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await db.delete(user)
    await db.commit()


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    """Delete a project (admin only)"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    await db.delete(project)
    await db.commit() 
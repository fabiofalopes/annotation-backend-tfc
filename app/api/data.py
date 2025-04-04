from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from ..database import get_db
from ..models import User, Project, DataContainer, DataItem, Annotation
from ..schemas import (
    DataContainer as DataContainerSchema,
    DataItem as DataItemSchema,
    Annotation as AnnotationSchema,
    ImportStatus
)
from ..auth import get_current_user, get_current_admin_user

router = APIRouter()

@router.get("/containers/{container_id}/items", response_model=List[DataItemSchema])
async def list_items(
    container_id: int,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated items from a container"""
    # Check container exists and user has access
    container_query = (
        select(DataContainer)
        .join(Project)
        .where(
            DataContainer.id == container_id,
            Project.id.in_(
                select(Project.id)
                .join(Project.assignments)
                .where(
                    (Project.assignments.any(user_id=current_user.id)) |
                    (User.is_admin == True)
                )
            )
        )
    )
    result = await db.execute(container_query)
    container = result.scalar_one_or_none()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found or access denied"
        )
    
    # Get items with pagination
    query = (
        select(DataItem)
        .where(DataItem.container_id == container_id)
        .order_by(DataItem.created_at)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    
    return items

@router.post("/items/{item_id}/annotations", response_model=AnnotationSchema)
async def create_annotation(
    item_id: int,
    annotation_type: str,
    annotation_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new annotation for an item"""
    # Check item exists
    query = select(DataItem).where(DataItem.id == item_id)
    result = await db.execute(query)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Create annotation
    annotation = Annotation(
        item_id=item_id,
        type=annotation_type,
        data=annotation_data,
        created_by=current_user.id,
        created_at=datetime.now()
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)
    
    return annotation

@router.get("/items/{item_id}/annotations", response_model=List[AnnotationSchema])
async def list_annotations(
    item_id: int,
    annotation_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all annotations for an item, optionally filtered by type"""
    # Check item exists and user has access
    query = (
        select(DataItem)
        .join(DataContainer)
        .join(Project)
        .where(
            DataItem.id == item_id,
            Project.id.in_(
                select(Project.id)
                .join(Project.assignments)
                .where(
                    (Project.assignments.any(user_id=current_user.id)) |
                    (User.is_admin == True)
                )
            )
        )
    )
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found or access denied"
        )
    
    # Get annotations
    query = select(Annotation).where(Annotation.item_id == item_id)
    if annotation_type:
        query = query.where(Annotation.type == annotation_type)
    
    result = await db.execute(query)
    annotations = result.scalars().all()
    
    return annotations

@router.put("/annotations/{annotation_id}", response_model=AnnotationSchema)
async def update_annotation(
    annotation_id: int,
    annotation_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing annotation"""
    # Check annotation exists and user owns it
    query = select(Annotation).where(
        Annotation.id == annotation_id,
        Annotation.created_by == current_user.id
    )
    result = await db.execute(query)
    annotation = result.scalar_one_or_none()
    
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found or access denied"
        )
    
    # Update annotation
    annotation.data = annotation_data
    annotation.updated_at = datetime.now()
    await db.commit()
    await db.refresh(annotation)
    
    return annotation 
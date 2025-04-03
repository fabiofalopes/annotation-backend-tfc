from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy import select

from ..database import get_db
from ..models import ImportedData, DataContainer
from ..schemas import ImportedDataCreate, ImportedData as ImportedDataSchema
from ..auth import get_current_user
from ..models import User

router = APIRouter()

@router.post("/", response_model=ImportedDataSchema)
async def create_imported_data(
    data_item: ImportedDataCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify container exists and user has access
    container = await db.get(DataContainer, data_item.container_id)
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Create imported data item
    db_item = ImportedData(
        container_id=data_item.container_id,
        content=data_item.content,
        meta_data=data_item.meta_data,
        title=data_item.title,
        category=data_item.category,
        tags=data_item.tags,
        source=data_item.source or "manual"
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


@router.get("/{item_id}", response_model=ImportedDataSchema)
async def get_imported_data(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = await db.get(ImportedData, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data item not found"
        )
    return item


@router.get("/container/{container_id}", response_model=List[ImportedDataSchema])
async def list_container_items(
    container_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify container exists and user has access
    container = await db.get(DataContainer, container_id)
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Get all items in container
    result = await db.execute(
        select(ImportedData)
        .where(ImportedData.container_id == container_id)
    )
    items = result.scalars().all()
    return items


@router.put("/{item_id}", response_model=ImportedDataSchema)
async def update_imported_data(
    item_id: int,
    data_item: ImportedDataCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get existing item
    db_item = await db.get(ImportedData, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data item not found"
        )
    
    # Update fields
    for field, value in data_item.dict(exclude_unset=True).items():
        setattr(db_item, field, value)
    
    await db.commit()
    await db.refresh(db_item)
    return db_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_imported_data(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get existing item
    db_item = await db.get(ImportedData, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data item not found"
        )
    
    await db.delete(db_item)
    await db.commit() 
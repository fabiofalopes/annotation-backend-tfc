from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Set, Any
import pandas as pd
import json
from io import StringIO
from datetime import datetime

from ..database import get_db
from ..models import User, Project, DataContainer, DataItem, Annotation, ChatMessage as ChatMessageModel
from ..schemas import (
    DataContainer as DataContainerSchema,
    DataItem as DataItemSchema,
    Annotation as AnnotationSchema,
    ChatMessage as ChatMessageSchema,
    ThreadAnnotation,
    ChatCSVImportRequest,
    ImportStatus,
    ThreadAnnotationBase
)
from ..auth import get_current_user, get_current_admin_user

router = APIRouter()

# Constants
MANDATORY_CHAT_COLUMNS = {"user_id", "turn_id", "turn_text", "reply_to_turn"}
THREAD_COLUMN = "thread"


@router.get("/containers/{container_id}/messages", response_model=List[ChatMessageSchema])
async def list_messages(
    container_id: int,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated messages from a container"""
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
    
    # Get messages with pagination
    query = (
        select(DataItem)
        .where(DataItem.container_id == container_id)
        .order_by(DataItem.created_at)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Convert to ChatMessage format
    messages = []
    for item in items:
        metadata = item.meta_data or {}
        messages.append(ChatMessageSchema(
            id=item.id,
            container_id=item.container_id,
            content=item.content,
            meta_data=metadata,
            type=item.type,
            created_at=item.created_at,
            turn_id=metadata.get("turn_id", str(item.id)),
            user_id=metadata.get("user_id", "unknown"),
            turn_text=item.content,
            timestamp=metadata.get("timestamp"),
            reply_to_turn=metadata.get("reply_to_turn")
        ))
    
    return messages


@router.post("/messages/{message_id}/thread", response_model=AnnotationSchema)
async def annotate_thread(
    message_id: int,
    thread_data: ThreadAnnotationBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create or update a thread annotation for a message"""
    # Check message exists
    query = select(DataItem).where(DataItem.id == message_id)
    result = await db.execute(query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check if annotation already exists
    query = select(Annotation).where(
        Annotation.item_id == message_id,
        Annotation.type == "thread",
        Annotation.created_by == current_user.id
    )
    result = await db.execute(query)
    existing_annotation = result.scalar_one_or_none()
    
    if existing_annotation:
        # Update existing annotation
        existing_annotation.data = thread_data.model_dump()
        existing_annotation.updated_at = datetime.now()
        await db.commit()
        return existing_annotation
    
    # Create new annotation
    annotation = Annotation(
        item_id=message_id,
        type="thread",
        data=thread_data.model_dump(),
        created_by=current_user.id,
        created_at=datetime.now()
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)
    
    return annotation


@router.get("/containers/{container_id}/threads", response_model=Dict[str, List[Dict[str, Any]]])
async def get_thread_annotations(
    container_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all thread annotations for a container"""
    # Check container access
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
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found or access denied"
        )
    
    # Get all thread annotations with user information
    query = (
        select(DataItem, Annotation, User)
        .select_from(DataItem)
        .join(Annotation, Annotation.item_id == DataItem.id)
        .join(User, User.id == Annotation.created_by)
        .where(
            DataItem.container_id == container_id,
            Annotation.type == "thread"
        )
        .order_by(DataItem.created_at)
    )
    result = await db.execute(query)
    rows = result.all()
    
    # Organize by thread ID with metadata
    threads = {}
    for item, annotation, user in rows:
        thread_id = annotation.data.get("thread_id")
        if thread_id:
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append({
                "turn_id": str(item.meta_data.get("turn_id", item.id)),
                "message_content": item.content,
                "annotation_id": annotation.id,
                "annotator": {
                    "id": user.id,
                    "email": user.email
                },
                "created_at": annotation.created_at.isoformat(),
                "updated_at": annotation.updated_at.isoformat() if annotation.updated_at else None,
                "confidence": annotation.data.get("confidence"),
                "notes": annotation.data.get("notes")
            })
    
    return threads


@router.post("/import", response_model=ImportStatus)
async def import_chat_data(
    file: UploadFile = File(...),
    import_request: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Import chat data from CSV file (admin only)"""
    try:
        # Parse import request from JSON string
        import_data = json.loads(import_request)
        import_request = ChatCSVImportRequest(**import_data)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in import_request"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Read CSV file
    content = await file.read()
    df = pd.read_csv(StringIO(content.decode()))
    
    # Get CSV columns
    csv_columns = set(df.columns)
    warnings = []
    
    # Validate mandatory columns
    reverse_mapping = {v: k for k, v in import_request.column_mapping.items()}
    missing_fields = MANDATORY_CHAT_COLUMNS - set(import_request.column_mapping.values())
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing mandatory fields in mapping: {missing_fields}"
        )
    
    # Check if thread column exists
    has_thread_column = THREAD_COLUMN in csv_columns
    if has_thread_column:
        warnings.append(f"Found '{THREAD_COLUMN}' column - will create initial thread annotations")
    
    # Create container
    container = DataContainer(
        name=import_request.container_name,
        project_id=import_request.project_id,
        meta_data={"import_type": "chat"}
    )
    db.add(container)
    await db.commit()
    await db.refresh(container)
    
    # Import data
    errors = []
    for idx, row in df.iterrows():
        try:
            # Prepare metadata
            metadata = {}
            for field_name, csv_col in reverse_mapping.items():
                if csv_col in row:
                    value = row[csv_col]
                    # Handle NaN values
                    if pd.isna(value):
                        if field_name == "reply_to_turn":
                            value = None
                        else:
                            value = ""
                    metadata[field_name] = str(value) if value is not None else None
            
            # Get content, handling NaN
            content = row[reverse_mapping["turn_text"]]
            if pd.isna(content):
                content = ""
            
            # Create chat message
            message = ChatMessageModel(
                container_id=container.id,
                content=str(content),
                meta_data=metadata
            )
            db.add(message)
            await db.commit()
            await db.refresh(message)
            
            # Create initial thread annotation if thread column exists
            if has_thread_column:
                thread_value = row.get(THREAD_COLUMN)
                annotation = Annotation(
                    item_id=message.id,
                    type="thread",
                    data={
                        "thread_id": str(thread_value) if pd.notna(thread_value) else None,
                        "confidence": 1.0 if pd.notna(thread_value) else None,
                        "source": "import",
                        "notes": "Initial thread annotation from import"
                    },
                    created_by=current_user.id
                )
                db.add(annotation)
                await db.commit()
        
        except Exception as e:
            errors.append(f"Error on row {idx}: {str(e)}")
    
    return ImportStatus(
        id=str(container.id),
        status="completed",
        progress=1.0,
        total_rows=len(df),
        processed_rows=len(df) - len(errors),
        errors=errors,
        warnings=warnings
    ) 
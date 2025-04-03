from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class ImportType(str, Enum):
    GENERIC = "generic"
    CHAT = "chat"


# Base Models
class UserBase(BaseModel):
    email: EmailStr


class ProjectBase(BaseModel):
    name: str
    type: str
    description: Optional[str] = None


class DataContainerBase(BaseModel):
    name: str
    meta_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = "pending"


class DataItemBase(BaseModel):
    content: str
    meta_data: Dict[str, Any]


class ImportedDataBase(DataItemBase):
    title: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    source: Optional[str] = None


class ChatMessageBase(DataItemBase):
    turn_id: str
    user_id: str
    turn_text: str
    timestamp: Optional[datetime] = None
    reply_to_turn: Optional[str] = None


class AnnotationBase(BaseModel):
    type: str
    data: Dict[str, Any]


class ThreadAnnotationBase(AnnotationBase):
    thread_id: str
    confidence: Optional[float] = None
    notes: Optional[str] = None


# Create Request Models
class UserCreate(UserBase):
    password: str
    is_admin: Optional[bool] = False


class ProjectCreate(ProjectBase):
    pass


class DataContainerCreate(DataContainerBase):
    project_id: int


class DataItemCreate(DataItemBase):
    container_id: int


class ImportedDataCreate(DataItemCreate, ImportedDataBase):
    pass


class ChatMessageCreate(DataItemCreate, ChatMessageBase):
    pass


class AnnotationCreate(AnnotationBase):
    item_id: int


class ThreadAnnotationCreate(AnnotationCreate, ThreadAnnotationBase):
    pass


# Response Models
class User(UserBase):
    id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Project(ProjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DataContainer(DataContainerBase):
    id: int
    project_id: int
    created_at: datetime
    status: str

    class Config:
        from_attributes = True


class DataItem(DataItemBase):
    id: int
    container_id: int
    type: str
    created_at: datetime

    class Config:
        from_attributes = True


class ImportedData(DataItem, ImportedDataBase):
    class Config:
        from_attributes = True


class ChatMessage(DataItem, ChatMessageBase):
    class Config:
        from_attributes = True


class Annotation(AnnotationBase):
    id: int
    item_id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ThreadAnnotation(Annotation, ThreadAnnotationBase):
    class Config:
        from_attributes = True


# Token Models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# Import Models
class CSVImportRequest(BaseModel):
    project_id: int
    container_name: str
    import_type: ImportType = ImportType.GENERIC
    column_mapping: Dict[str, str]  # Maps CSV columns to data fields


class ChatCSVImportRequest(CSVImportRequest):
    import_type: Literal[ImportType.CHAT] = ImportType.CHAT
    column_mapping: Dict[str, str] = Field(
        default={
            "user_id": "user_id",
            "turn_id": "turn_id",
            "turn_text": "turn_text",
            "reply_to_turn": "reply_to_turn"
        }
    )


class ImportStatus(BaseModel):
    id: str
    status: str
    progress: float
    total_rows: int
    processed_rows: int
    errors: List[str]
    warnings: List[str] = Field(default_factory=list) 
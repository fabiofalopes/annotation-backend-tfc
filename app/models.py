from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Boolean, DateTime, Float
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional, Dict, Any
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project_assignments = relationship("ProjectAssignment", back_populates="user")


class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # e.g., "chat_disentanglement"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    containers = relationship("DataContainer", back_populates="project")
    assignments = relationship("ProjectAssignment", back_populates="project")


class ProjectAssignment(Base):
    __tablename__ = "project_assignments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    
    # Relationships
    user = relationship("User", back_populates="project_assignments")
    project = relationship("Project", back_populates="assignments")


class DataContainer(Base):
    __tablename__ = "data_containers"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, processing, completed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="containers")
    items = relationship("DataItem", back_populates="container")


class DataItem(Base):
    __tablename__ = "data_items"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    container_id: Mapped[int] = mapped_column(ForeignKey("data_containers.id"))
    content: Mapped[str] = mapped_column(Text)
    meta_data: Mapped[Dict[str, Any]] = mapped_column(JSON)
    type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    container = relationship("DataContainer", back_populates="items")
    annotations = relationship("Annotation", back_populates="item")

    __mapper_args__ = {
        "polymorphic_identity": "data_item",
        "polymorphic_on": "type",
    }


class ImportedData(DataItem):
    __tablename__ = "imported_data_items"
    
    id: Mapped[int] = mapped_column(ForeignKey("data_items.id"), primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., "csv_import", "manual", etc.

    __mapper_args__ = {
        "polymorphic_identity": "imported_data",
    }


class ChatMessage(DataItem):
    """Chat message data item with specific chat fields"""
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(ForeignKey("data_items.id"), primary_key=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "chat_message",
    }
    
    @property
    def turn_id(self) -> str:
        """Get the turn ID from metadata"""
        return str(self.meta_data.get("turn_id", self.id))
    
    @property
    def user_id(self) -> str:
        """Get the user ID from metadata"""
        return str(self.meta_data.get("user_id", "unknown"))
    
    @property
    def reply_to_turn(self) -> Optional[str]:
        """Get the reply-to turn ID from metadata"""
        return self.meta_data.get("reply_to_turn")
    
    @property
    def timestamp(self) -> Optional[datetime]:
        """Get the message timestamp from metadata"""
        return self.meta_data.get("timestamp")


class Annotation(Base):
    __tablename__ = "annotations"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("data_items.id"))
    type: Mapped[str] = mapped_column(String)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    item = relationship("DataItem", back_populates="annotations")
    user = relationship("User")

    __mapper_args__ = {
        "polymorphic_identity": "annotation",
        "polymorphic_on": "type",
    }


class ThreadAnnotation(Annotation):
    __tablename__ = "thread_annotations"
    
    id: Mapped[int] = mapped_column(ForeignKey("annotations.id"), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "thread",
    } 
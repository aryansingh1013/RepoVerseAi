"""Pydantic models for Phase 1 database entities."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------- repositories ----------
class RepositoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    url: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    branch: str = "main"
    language: Optional[str] = None


class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    branch: Optional[str] = None
    current_commit_sha: Optional[str] = None
    indexed_commit_sha: Optional[str] = None
    status: Optional[str] = None  # pending | indexing | ready | error
    language: Optional[str] = None


class RepositoryOut(BaseModel):
    id: UUID
    name: str
    url: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    branch: str = "main"
    status: str = "pending"
    language: Optional[str] = None
    current_commit_sha: Optional[str] = None
    indexed_commit_sha: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------- indexing jobs ----------
class IndexingJobCreate(BaseModel):
    repository_id: UUID
    job_type: str = "initial_index"  # initial_index | incremental_index | reindex
    commit_sha: Optional[str] = None
    branch: Optional[str] = None


class IndexingJobUpdate(BaseModel):
    status: Optional[str] = None  # pending | running | succeeded | failed | cancelled
    error_message: Optional[str] = None
    files_processed: Optional[int] = None
    chunks_generated: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class IndexingJobOut(BaseModel):
    id: UUID
    repository_id: UUID
    job_type: str
    status: str
    commit_sha: Optional[str] = None
    branch: Optional[str] = None
    error_message: Optional[str] = None
    files_processed: int = 0
    chunks_generated: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# ---------- conversations / messages / citations ----------
class ConversationCreate(BaseModel):
    repository_id: UUID
    title: Optional[str] = None


class ConversationOut(BaseModel):
    id: UUID
    repository_id: UUID
    title: Optional[str] = None
    created_at: Optional[datetime] = None


class MessageCreate(BaseModel):
    conversation_id: UUID
    role: str  # user | assistant | system
    content: str
    confidence_score: Optional[float] = None
    reasoning_trace: Optional[Dict[str, Any]] = None


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    confidence_score: Optional[float] = None
    created_at: Optional[datetime] = None


class CitationCreate(BaseModel):
    message_id: UUID
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    score: Optional[float] = None
    chunk_id: Optional[UUID] = None


class CitationOut(BaseModel):
    id: UUID
    message_id: UUID
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    score: Optional[float] = None


# ---------- user settings ----------
class UserSettingsOut(BaseModel):
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    fallback_order: Optional[List[str]] = None
    embedding_model: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)

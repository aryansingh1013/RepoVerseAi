"""Phase 1 — REST API routes for the Supabase foundation.

New namespaced endpoints (architecture §7):
  /api/auth/me                     — current user
  /api/repositories                — CRUD (user-scoped)
  /api/repositories/{id}/index     — create indexing job
  /api/jobs/{id}                   — job status
  /api/repositories/{id}/jobs      — job history
  /api/repositories/{id}/conversations        — conversations CRUD
  /api/conversations/{id}/messages            — message history
  /api/conversations/{id}/messages/{mid}/citations — citations

NOTE: in Phase 1 the indexing job still executes locally via the
existing pipeline (FastAPI BackgroundTasks) so no functionality is
lost. Phase 3 replaces the execution engine with SQS + ECS Worker;
the job model created here is already the contract for that.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from backend.auth import AuthUser, get_current_user
from backend.database.models import (
    CitationCreate,
    ConversationCreate,
    IndexingJobCreate,
    IndexingJobUpdate,
    MessageCreate,
    RepositoryCreate,
    RepositoryUpdate,
)
from backend.database.repository import (
    ConversationStore,
    JobStore,
    RepositoryStore,
    SettingsStore,
)

router = APIRouter()


# ---------- auth ----------
@router.get("/api/auth/me")
def read_current_user(user: AuthUser = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}


class RegisterPayload(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


@router.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterPayload):
    """Admin-backed registration.

    Supabase's built-in email service allows only a few confirmation emails
    per hour on free projects, which makes public signups fail with
    'email rate limit exceeded'. This endpoint creates the user directly
    via the service-role admin API with the email pre-confirmed, so NO
    email is sent and the user can sign in immediately.
    """
    import re as _re
    from backend.database.client import get_supabase_admin, supabase_enabled

    if not supabase_enabled():
        raise HTTPException(status_code=503, detail="Auth backend is not configured.")
    email = payload.email.strip().lower()
    if not _re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Invalid email address.")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    admin = get_supabase_admin()
    try:
        created = admin.auth.admin.create_user(
            {
                "email": email,
                "password": payload.password,
                "email_confirm": True,
                "user_metadata": (
                    {"name": payload.display_name} if payload.display_name else {}
                ),
            }
        )
    except Exception as exc:
        msg = str(exc)
        if "already" in msg.lower() or "registered" in msg.lower() or "duplicate" in msg.lower():
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please sign in.",
            )
        raise HTTPException(status_code=400, detail=f"Registration failed: {msg[:200]}")

    return {"id": created.user.id, "email": created.user.email}


# ---------- repositories ----------
@router.post("/api/repositories", status_code=status.HTTP_201_CREATED)
def create_repository(payload: RepositoryCreate, user: AuthUser = Depends(get_current_user)):
    try:
        return RepositoryStore.create(user.id, payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not create repository: {exc}")


@router.get("/api/repositories")
def list_repositories(user: AuthUser = Depends(get_current_user)):
    return RepositoryStore.list_for_user(user.id)


@router.get("/api/repositories/{repository_id}")
def get_repository(repository_id: UUID, user: AuthUser = Depends(get_current_user)):
    repo = RepositoryStore.get(user.id, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    return repo


@router.patch("/api/repositories/{repository_id}")
def update_repository(
    repository_id: UUID, payload: RepositoryUpdate, user: AuthUser = Depends(get_current_user)
):
    repo = RepositoryStore.update(user.id, repository_id, payload)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    return repo


@router.delete("/api/repositories/{repository_id}")
def delete_repository(repository_id: UUID, user: AuthUser = Depends(get_current_user)):
    if not RepositoryStore.delete(user.id, repository_id):
        raise HTTPException(status_code=404, detail="Repository not found.")
    return {"status": "deleted"}


# ---------- indexing jobs ----------
def _run_local_index_job(repository_id: UUID, job_id: UUID, user_id: str):
    """Phase 1 local execution of a job (replaced by ECS worker in Phase 3)."""
    try:
        JobStore.update(user_id, job_id, IndexingJobUpdate(status="running"))
        from backend.core.config import settings as _settings
        from backend.app import index_galaxy  # reuse existing pipeline

        import asyncio

        asyncio.run(index_galaxy())
        JobStore.update(
            user_id, job_id, IndexingJobUpdate(status="succeeded", finished_at=None)
        )
        RepositoryStore.update(
            user_id, repository_id, RepositoryUpdate(status="ready")
        )
    except Exception as exc:
        JobStore.update(
            user_id,
            job_id,
            IndexingJobUpdate(status="failed", error_message=str(exc)),
        )
        RepositoryStore.update(
            user_id, repository_id, RepositoryUpdate(status="error")
        )


@router.post("/api/repositories/{repository_id}/index", status_code=status.HTTP_202_ACCEPTED)
def start_indexing(
    repository_id: UUID,
    background: BackgroundTasks,
    payload: IndexingJobCreate | None = None,
    user: AuthUser = Depends(get_current_user),
):
    repo = RepositoryStore.get(user.id, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    body = payload or IndexingJobCreate(repository_id=repository_id)
    job = JobStore.create(user.id, body)
    background.add_task(_run_local_index_job, repository_id, job["id"], user.id)
    return {"job_id": job["id"], "status": job["status"]}


@router.get("/api/repositories/{repository_id}/jobs")
def list_jobs(repository_id: UUID, user: AuthUser = Depends(get_current_user)):
    return JobStore.list_for_repository(user.id, repository_id)


@router.get("/api/jobs/{job_id}")
def get_job(job_id: UUID, user: AuthUser = Depends(get_current_user)):
    job = JobStore.get(user.id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


# ---------- conversations / messages / citations ----------
@router.post("/api/repositories/{repository_id}/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(
    repository_id: UUID, payload: ConversationCreate, user: AuthUser = Depends(get_current_user)
):
    body = payload.model_copy(update={"repository_id": repository_id})
    try:
        return ConversationStore.create_conversation(user.id, body)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/repositories/{repository_id}/conversations")
def list_conversations(repository_id: UUID, user: AuthUser = Depends(get_current_user)):
    return ConversationStore.list_conversations(user.id, repository_id)


@router.post("/api/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
def add_message(conversation_id: UUID, payload: MessageCreate, user: AuthUser = Depends(get_current_user)):
    body = payload.model_copy(update={"conversation_id": conversation_id})
    try:
        return ConversationStore.add_message(user.id, body)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/conversations/{conversation_id}/messages")
def list_messages(conversation_id: UUID, user: AuthUser = Depends(get_current_user)):
    try:
        return ConversationStore.list_messages(user.id, conversation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/api/conversations/{conversation_id}/citations", status_code=status.HTTP_201_CREATED)
def add_citations(conversation_id: UUID, citations: list[CitationCreate], user: AuthUser = Depends(get_current_user)):
    if not citations:
        return []
    # Ensure all citations belong to messages inside this conversation.
    try:
        messages = ConversationStore.list_messages(user.id, conversation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    valid_ids = {str(m["id"]) for m in messages}
    scoped = [c for c in citations if str(c.message_id) in valid_ids]
    if not scoped:
        raise HTTPException(status_code=400, detail="No citations reference messages in this conversation.")
    return ConversationStore.add_citations(user.id, scoped)


# ---------- user settings ----------
@router.get("/api/user/settings")
def get_user_settings(user: AuthUser = Depends(get_current_user)):
    return SettingsStore.get(user.id)


@router.put("/api/user/settings")
def put_user_settings(payload: dict, user: AuthUser = Depends(get_current_user)):
    allowed = {
        "preferred_provider", "preferred_model", "fallback_order", "embedding_model", "settings",
    }
    data = {k: v for k, v in payload.items() if k in allowed}
    return SettingsStore.upsert(user.id, data)

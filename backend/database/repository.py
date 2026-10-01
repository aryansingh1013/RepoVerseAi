"""Typed data-access helpers over Supabase (Phase 1).

All functions take an explicit ``user_id`` — ownership is enforced here
in addition to Postgres RLS, so a bug in one layer cannot expose another
user's data (defense in depth, per architecture Rule 21).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from backend.database.client import get_supabase_admin
from backend.database.models import (
    CitationCreate,
    ConversationCreate,
    IndexingJobCreate,
    IndexingJobUpdate,
    MessageCreate,
    RepositoryCreate,
    RepositoryUpdate,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RepositoryStore:
    """CRUD for repositories. Every query is scoped to the owning user."""

    TABLE = "repositories"

    @staticmethod
    def create(user_id: UUID, payload: RepositoryCreate) -> Dict[str, Any]:
        row = payload.model_dump()
        row["user_id"] = str(user_id)
        res = get_supabase_admin().table(RepositoryStore.TABLE).insert(row).execute()
        return res.data[0]

    @staticmethod
    def get(user_id: UUID, repository_id: UUID) -> Optional[Dict[str, Any]]:
        res = (
            get_supabase_admin()
            .table(RepositoryStore.TABLE)
            .select("*")
            .eq("id", str(repository_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    @staticmethod
    def list_for_user(user_id: UUID) -> List[Dict[str, Any]]:
        res = (
            get_supabase_admin()
            .table(RepositoryStore.TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []

    @staticmethod
    def update(user_id: UUID, repository_id: UUID, payload: RepositoryUpdate) -> Optional[Dict[str, Any]]:
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not data:
            return RepositoryStore.get(user_id, repository_id)
        res = (
            get_supabase_admin()
            .table(RepositoryStore.TABLE)
            .update(data)
            .eq("id", str(repository_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return res.data[0] if res.data else None

    @staticmethod
    def delete(user_id: UUID, repository_id: UUID) -> bool:
        res = (
            get_supabase_admin()
            .table(RepositoryStore.TABLE)
            .delete()
            .eq("id", str(repository_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return bool(res.data)


class JobStore:
    """Indexing job lifecycle: create → running → succeeded/failed."""

    TABLE = "indexing_jobs"

    @staticmethod
    def create(user_id: UUID, payload: IndexingJobCreate) -> Dict[str, Any]:
        # Verify the user owns the repository before creating a job for it.
        if not RepositoryStore.get(user_id, payload.repository_id):
            raise PermissionError("Repository not found for this user.")
        row = payload.model_dump()
        row["user_id"] = str(user_id)
        row["repository_id"] = str(payload.repository_id)
        res = get_supabase_admin().table(JobStore.TABLE).insert(row).execute()
        return res.data[0]

    @staticmethod
    def get(user_id: UUID, job_id: UUID) -> Optional[Dict[str, Any]]:
        res = (
            get_supabase_admin()
            .table(JobStore.TABLE)
            .select("*")
            .eq("id", str(job_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    @staticmethod
    def list_for_repository(user_id: UUID, repository_id: UUID) -> List[Dict[str, Any]]:
        res = (
            get_supabase_admin()
            .table(JobStore.TABLE)
            .select("*")
            .eq("repository_id", str(repository_id))
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []

    @staticmethod
    def update(user_id: UUID, job_id: UUID, payload: IndexingJobUpdate) -> Optional[Dict[str, Any]]:
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        if "status" in data and data["status"] == "running" and not data.get("started_at"):
            data["started_at"] = _utcnow()
        if "status" in data and data["status"] in ("succeeded", "failed", "cancelled") and not data.get("finished_at"):
            data["finished_at"] = _utcnow()
        res = (
            get_supabase_admin()
            .table(JobStore.TABLE)
            .update(data)
            .eq("id", str(job_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return res.data[0] if res.data else None


class ConversationStore:
    """Conversations, messages and citations."""

    @staticmethod
    def create_conversation(user_id: UUID, payload: ConversationCreate) -> Dict[str, Any]:
        if not RepositoryStore.get(user_id, payload.repository_id):
            raise PermissionError("Repository not found for this user.")
        row = payload.model_dump()
        row["user_id"] = str(user_id)
        res = get_supabase_admin().table("conversations").insert(row).execute()
        return res.data[0]

    @staticmethod
    def list_conversations(user_id: UUID, repository_id: UUID) -> List[Dict[str, Any]]:
        res = (
            get_supabase_admin()
            .table("conversations")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("repository_id", str(repository_id))
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []

    @staticmethod
    def add_message(user_id: UUID, payload: MessageCreate) -> Dict[str, Any]:
        # Ownership check via conversation → user.
        conv = (
            get_supabase_admin()
            .table("conversations")
            .select("id")
            .eq("id", str(payload.conversation_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if not conv.data:
            raise PermissionError("Conversation not found for this user.")
        row = payload.model_dump(exclude={"conversation_id"})
        row["conversation_id"] = str(payload.conversation_id)
        res = get_supabase_admin().table("messages").insert(row).execute()
        return res.data[0]

    @staticmethod
    def list_messages(user_id: UUID, conversation_id: UUID) -> List[Dict[str, Any]]:
        conv = (
            get_supabase_admin()
            .table("conversations")
            .select("id")
            .eq("id", str(conversation_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if not conv.data:
            raise PermissionError("Conversation not found for this user.")
        res = (
            get_supabase_admin()
            .table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", asc=True)
            .execute()
        )
        return res.data or []

    @staticmethod
    def add_citations(user_id: UUID, citations: List[CitationCreate]) -> List[Dict[str, Any]]:
        if not citations:
            return []
        # Validate ownership of every referenced message first.
        message_ids = {str(c.message_id) for c in citations}
        owned = (
            get_supabase_admin()
            .table("messages")
            .select("id, conversations!inner(user_id)")
            .in_("id", list(message_ids))
            .eq("conversations.user_id", str(user_id))
            .execute()
        )
        owned_ids = {m["id"] for m in (owned.data or [])}
        unknown = message_ids - owned_ids
        if unknown:
            raise PermissionError(f"Message(s) not owned by user: {unknown}")
        rows = []
        for c in citations:
            row = c.model_dump()
            row["message_id"] = str(c.message_id)
            row["chunk_id"] = str(c.chunk_id) if c.chunk_id else None
            rows.append(row)
        res = get_supabase_admin().table("citations").insert(rows).execute()
        return res.data or []


class SettingsStore:
    """Per-user settings (LLM provider preferences etc.)."""

    TABLE = "user_settings"

    @staticmethod
    def get(user_id: UUID) -> Dict[str, Any]:
        res = (
            get_supabase_admin()
            .table(SettingsStore.TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else {}

    @staticmethod
    def upsert(user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(data)
        row["user_id"] = str(user_id)
        res = get_supabase_admin().table(SettingsStore.TABLE).upsert(row).execute()
        return res.data[0]

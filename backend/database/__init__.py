"""Phase 1 — Supabase persistence layer.

Provides the Supabase client factory and typed data-access helpers.
The API service uses the service-role key server-side ONLY; the
anon key + user JWT are used for auth validation.
"""

from backend.database.client import get_supabase, get_supabase_admin, supabase_enabled
from backend.database.models import (
    RepositoryCreate,
    RepositoryOut,
    RepositoryUpdate,
    IndexingJobCreate,
    IndexingJobOut,
    IndexingJobUpdate,
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
    CitationCreate,
    CitationOut,
    UserSettingsOut,
)
from backend.database.repository import (
    RepositoryStore,
    JobStore,
    ConversationStore,
    SettingsStore,
)

__all__ = [
    "get_supabase",
    "get_supabase_admin",
    "supabase_enabled",
    "RepositoryCreate", "RepositoryOut", "RepositoryUpdate",
    "IndexingJobCreate", "IndexingJobOut", "IndexingJobUpdate",
    "ConversationCreate", "ConversationOut",
    "MessageCreate", "MessageOut",
    "CitationCreate", "CitationOut",
    "UserSettingsOut",
    "RepositoryStore", "JobStore", "ConversationStore", "SettingsStore",
]

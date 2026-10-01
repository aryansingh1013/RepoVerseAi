"""Supabase client factory.

Two clients:
- admin client (service-role key): bypasses RLS, used by API backend for
  trusted writes (indexing jobs, chunk writes after auth check).
- anon client (anon key): used with the caller's JWT for auth validation.

Both are lazy singletons so importing the module never fails when Supabase
is not configured (local dev without cloud).
"""

from functools import lru_cache
from typing import Optional

from backend.core.config import settings

try:
    from supabase import create_client, Client
    SUPABASE_SDK_AVAILABLE = True
except ImportError:  # supabase not installed yet — feature stays optional
    create_client = None
    Client = None
    SUPABASE_SDK_AVAILABLE = False


class SupabaseNotConfigured(RuntimeError):
    """Raised when a code path requires Supabase but it is not configured."""


def supabase_enabled() -> bool:
    """True when URL + service key are present and the SDK is installed."""
    return bool(
        SUPABASE_SDK_AVAILABLE
        and getattr(settings, "SUPABASE_URL", "")
        and getattr(settings, "SUPABASE_SERVICE_KEY", "")
    )


@lru_cache(maxsize=1)
def get_supabase_admin():
    """Service-role client. NEVER expose this client or its key to the frontend."""
    if not supabase_enabled():
        raise SupabaseNotConfigured(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY in backend/.env"
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


@lru_cache(maxsize=1)
def get_supabase_anon():
    """Anon client. Used together with a user JWT for auth validation."""
    if not (SUPABASE_SDK_AVAILABLE and getattr(settings, "SUPABASE_URL", "") and getattr(settings, "SUPABASE_ANON_KEY", "")):
        raise SupabaseNotConfigured(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in backend/.env"
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_supabase():
    """Alias for the admin client (most backend code wants trusted access)."""
    return get_supabase_admin()


def reset_clients():
    """Clear cached clients (used by tests and after settings changes)."""
    get_supabase_admin.cache_clear()
    get_supabase_anon.cache_clear()

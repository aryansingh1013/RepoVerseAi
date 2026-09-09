"""P0 security primitives for RepoVerse AI.

Centralizes the hardening helpers that were previously missing or ad-hoc:

* ``resolve_within``  – realpath + commonpath containment check, defeating
  ``..`` traversal, symlink escapes, and sibling-prefix confusion
  (``/app/workspace-evil`` vs ``/app/workspace``).
* ``validate_terminal_command`` – shell-free, allowlist-based argv builder for
  the whitelisted terminal tool (no ``shell=True``, no operator chaining).
* ``validate_clone_url`` – scheme allowlist + repo-name sanitization for the
  ``/api/clone`` endpoint (blocks ``file://``, ``ext::`` and argv injection).
* ``require_trusted_client`` – FastAPI dependency guarding mutating/admin
  endpoints: localhost clients are trusted (local desktop app); remote clients
  must present ``REPOVERSE_ADMIN_TOKEN`` via the ``X-RepoVerse-Admin`` header.
"""

import os
import re
import shlex
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# FastAPI is only needed for the request-gate helper below; the pure validation
# functions must stay importable in any context (CLI, tests, workers).
try:
    from fastapi import Header, HTTPException, Request
    _HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    Header = HTTPException = Request = None  # type: ignore
    _HAS_FASTAPI = False

# Characters/operators that must never reach a subprocess, even with
# shell=False (defense in depth; also rejects multiline prompt-injection tricks).
DANGEROUS_SHELL_TOKENS = (";", "&&", "||", "|", "&", ">", "<", "`", "$(", "${", "\n", "\r")

# Exact command prefixes permitted for MCPTools.terminal_run. Each entry maps the
# accepted user-facing prefix to the argv template used to execute it.
DEFAULT_TERMINAL_ALLOWLIST: Dict[str, List[str]] = {
    "pytest": ["pytest"],
    "python -m pytest": ["python", "-m", "pytest"],
    "npm run build": ["npm", "run", "build"],
    "npm run lint": ["npm", "run", "lint"],
    "npm test": ["npm", "test"],
    "npx tsc --noEmit": ["npx", "tsc", "--noEmit"],
}

# Extra flags accepted after an allowlisted command must look like real flags
# (e.g. -q, --maxfail=3), never injection payloads.
_SAFE_FLAG_RE = re.compile(r"^-{1,2}[A-Za-z0-9_][A-Za-z0-9_\-.=]*$")
_SAFE_ARG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-.=/]*$")

_REPO_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


# ── Path containment ─────────────────────────────────────────────────────────

def resolve_within(root_dir: str, candidate: str) -> str:
    """Resolve ``candidate`` and guarantee it stays inside ``root_dir``.

    Returns the real absolute path. Raises ``PermissionError`` when the
    resolved path escapes the root (traversal, symlink escape, or a sibling
    directory whose name merely starts with the root string).
    """
    if candidate is None or not str(candidate).strip():
        raise PermissionError("Empty path rejected.")
    candidate = str(candidate)
    # Reject NUL bytes and embedded control chars outright.
    if "\x00" in candidate or any(ord(c) < 32 and c not in "\t" for c in candidate):
        raise PermissionError("Illegal characters in path.")

    root_real = os.path.realpath(root_dir)
    if os.path.isabs(candidate):
        target = os.path.realpath(candidate)
    else:
        target = os.path.realpath(os.path.join(root_real, candidate))

    try:
        inside = os.path.commonpath([root_real, target]) == root_real
    except ValueError:
        # Different drives on Windows (or empty component) – treat as escape.
        inside = False

    if not inside:
        raise PermissionError("Access outside the workspace root is restricted.")
    return target


# ── Terminal allowlist ───────────────────────────────────────────────────────

def contains_dangerous_tokens(command: str) -> bool:
    return any(token in command for token in DANGEROUS_SHELL_TOKENS)


def validate_terminal_command(
    command: str,
    allowlist: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """Turn a user/LLM-supplied command string into a safe argv list.

    Returns ``(argv, None)`` when the command matches the allowlist, otherwise
    ``(None, reason)``. Execution must always go through ``subprocess`` with
    ``shell=False`` using the returned argv.
    """
    if not command or not str(command).strip():
        return None, "Command string is empty."
    command = str(command).strip()

    if contains_dangerous_tokens(command):
        return None, "Shell operators (;, |, &&, redirects, backticks, $()) are not allowed."

    try:
        tokens = shlex.split(command, posix=True)
    except ValueError as exc:
        return None, f"Unbalanced quoting in command: {exc}"

    if not tokens:
        return None, "Command string is empty."
    if tokens[0].startswith("-"):
        return None, "Command may not start with '-'. A leading dash is argument injection."

    allowlist = allowlist or DEFAULT_TERMINAL_ALLOWLIST
    normalized = " ".join(tokens)

    for prefix, argv_template in allowlist.items():
        prefix_tokens = prefix.split()
        if normalized != prefix and not normalized.startswith(prefix + " "):
            continue
        extra = tokens[len(prefix_tokens):]
        for arg in extra:
            if arg.startswith("-"):
                if not _SAFE_FLAG_RE.match(arg):
                    return None, f"Unsafe flag '{arg}' for allowlisted command."
            elif not _SAFE_ARG_RE.match(arg):
                return None, f"Unsafe argument '{arg}' for allowlisted command."
        return argv_template + extra, None

    allowed = ", ".join(sorted(allowlist.keys()))
    return None, f"Command '{command}' is not in the execution allowlist. Allowed: {allowed}."


# ── Git clone URL validation ─────────────────────────────────────────────────

def validate_clone_url(repo_url: str) -> Tuple[str, str]:
    """Validate a remote repository URL and derive a safe local folder name.

    Returns ``(clean_url, repo_name)`` or raises ``ValueError``. Blocks:
    non-remote schemes (``file://``, ``ext::``, bare paths), control chars,
    URLs that could be parsed as options, and traversal in the derived name.
    """
    if repo_url is None:
        raise ValueError("Repository URL is required.")
    url = str(repo_url).strip()
    if not url:
        raise ValueError("Repository URL is required.")
    if any(ch.isspace() for ch in url) or any(ord(c) < 32 for c in url):
        raise ValueError("Repository URL may not contain whitespace or control characters.")
    if url.startswith("-"):
        raise ValueError("Repository URL may not start with '-'.")

    parsed = urlparse(url)
    allowed_schemes = {"https", "http", "ssh", "git"}
    if parsed.scheme not in allowed_schemes:
        raise ValueError(
            f"Scheme '{parsed.scheme or 'none'}' is not allowed. Use an https://, ssh:// or git:// URL."
        )
    if parsed.scheme == "http" and os.getenv("REPOVERSE_ALLOW_INSECURE_CLONES", "").lower() not in {"1", "true"}:
        raise ValueError("Plain http:// clones are disabled; set REPOVERSE_ALLOW_INSECURE_CLONES=1 for LAN git servers.")
    if not parsed.hostname:
        raise ValueError("Repository URL must include a host.")
    if parsed.username or parsed.password:
        raise ValueError("Embedded credentials in the clone URL are not allowed; use a configured git credential helper.")

    path = parsed.path.strip("/")
    repo_name = os.path.basename(path)
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    repo_name = _REPO_NAME_RE.sub("", repo_name).strip(".")
    if not repo_name or repo_name.startswith("."):
        fallback = _REPO_NAME_RE.sub("", path.replace("/", "-"))[:64]
        repo_name = fallback or f"repo-{int(time.time())}"
    return url, repo_name


# ── Admin / trust gate ───────────────────────────────────────────────────────

def _admin_token() -> str:
    return os.getenv("REPOVERSE_ADMIN_TOKEN", "").strip()


def is_local_request(request: Request) -> bool:
    """Loopback detection. When REPOVERSE_TRUST_PROXY=1, honour X-Forwarded-For
    (required behind Render/Railway/nginx; without it every remote client
    would look like 127.0.0.1 to the proxy and silently inherit local trust)."""
    if os.getenv("REPOVERSE_TRUST_PROXY", "").strip().lower() in {"1", "true", "yes"}:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip() in LOOPBACK_HOSTS
    client = getattr(request, "client", None)
    return bool(client and client.host in LOOPBACK_HOSTS)


def _unauthorized_detail() -> str:
    return (
        "This endpoint is restricted to trusted clients. Local (localhost) access is always "
        "allowed; remote callers must configure REPOVERSE_ADMIN_TOKEN on the server and send "
        "it in the 'X-RepoVerse-Admin' header. (Full multi-user auth arrives with the Supabase "
        "Auth migration.)"
    )


if _HAS_FASTAPI:
    async def require_trusted_client(
        request: Request,
        x_repoverse_admin: Optional[str] = Header(default=None),
    ) -> None:
        """Allow loopback clients unconditionally (local desktop mode). Remote
        clients are rejected unless REPOVERSE_ADMIN_TOKEN is configured and the
        X-RepoVerse-Admin header matches it."""
        if is_local_request(request):
            return
        token = _admin_token()
        if token and x_repoverse_admin == token:
            return
        raise HTTPException(status_code=403, detail=_unauthorized_detail())
else:  # pragma: no cover - FastAPI always present in the real deployment
    async def require_trusted_client(request, x_repoverse_admin: Optional[str] = None) -> None:
        if is_local_request(request):
            return
        raise RuntimeError(_unauthorized_detail())

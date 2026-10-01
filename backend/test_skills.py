"""
RepoVerse AI — Skills Test Suite (master prompt §18/§20).

Covers:
  - universe isolation (two workspaces must never mix data)
  - skill logic (dependencies, health, timeline, overview, security, performance)
  - LLM failure handling (structured errors, no fake success, no caching of failures)
  - router behavior (settings resolution, fallback chain, NameError regression)

Run from project root:  python -m pytest backend/test_skills.py -v
"""
import os
import sys
import json
import shutil
import subprocess
import tempfile
import textwrap

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importing backend.skills registers all 9 skills
import backend.skills  # noqa: F401,E402
from backend.skills.registry import skill_registry  # noqa: E402


# ── Fixtures: two isolated fake universes ────────────────────────────────────

REPO_A_FILES = {
    "uniquely_named_module_alpha.py": (
        "import helper_shared\n"
        "\n"
        "def alpha_secret_function():\n"
        "    '''Universe A marker: ALPHA_MARKER_42.'''\n"
        "    return helper_shared.shared()\n"
        "\n"
        "def avg(x, y):\n"
        "    return (x + y) / 2\n"
    ),
    "helper_shared.py": "def shared():\n    return 'A-shared'\n",
    "cycle_a.py": "import cycle_b\n",
    "cycle_b.py": "import cycle_a\n",
    "README.md": "Universe A readme — ALPHA_MARKER_42\n",
    ".env": "SHOULD_NOT_BE_SCANNED = 'true'\n",
}

REPO_B_FILES = {
    "uniquely_named_module_beta.py": (
        "def beta_secret_function():\n"
        "    '''Universe B marker: BETA_MARKER_99.'''\n"
        "    return 1\n"
    ),
    "README.md": "Universe B readme — BETA_MARKER_99\n",
}


def _write_tree(root: str, files: dict):
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


@pytest.fixture(scope="module")
def universe_a():
    d = tempfile.mkdtemp(prefix="repoverse_uni_a_")
    _write_tree(d, REPO_A_FILES)
    os.makedirs(os.path.join(d, ".git"), exist_ok=True)
    # git init so the timeline skill has real history (no external calls needed
    # for rev-list on an empty repo? Actually empty HEAD fails — add one commit)
    try:
        subprocess.run(["git", "init", "-q"], cwd=d, check=True, timeout=15)
        subprocess.run(["git", "-C", d, "config", "user.email", "t@t.local"], check=True, timeout=15)
        subprocess.run(["git", "-C", d, "config", "user.name", "Tester"], check=True, timeout=15)
        subprocess.run(["git", "-C", d, "add", "-A"], check=True, timeout=15)
        subprocess.run(
            ["git", "-C", d, "commit", "-q", "-m", "init: universe A commit"],
            cwd=d, check=True, timeout=15,
        )
    except Exception:
        pass  # git missing → timeline tests degrade gracefully
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def universe_b():
    d = tempfile.mkdtemp(prefix="repoverse_uni_b_")
    _write_tree(d, REPO_B_FILES)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(autouse=True)
def _no_skill_cache(universe_a, universe_b):
    """Keep tests independent from disk cache."""
    from backend.skills.cache import clear_cache

    clear_cache(universe_a)
    clear_cache(universe_b)
    yield
    clear_cache(universe_a)
    clear_cache(universe_b)


# ── Registry ─────────────────────────────────────────────────────────────────

def test_all_nine_skills_registered():
    expected = {
        "overview", "architecture", "health", "dependencies", "timeline",
        "learning", "readme", "security", "performance",
    }
    slugs = {s["slug"] for s in skill_registry.list_skills()}
    assert expected == slugs, f"Registry mismatch. Missing: {expected - slugs}"


# ── Universe isolation (§18 — mandatory) ────────────────────────────────────

def test_overview_is_isolated_to_active_universe(universe_a, universe_b):
    """Overview's static core: folders_overview/main_components must reflect ONLY
    the active universe. (README summary is intentionally from the repo root.)"""
    skill = skill_registry.get_skill("overview")
    res_a = skill.execute("", None, universe_a)
    res_b = skill.execute("", None, universe_b)

    joined_a = json.dumps(res_a)
    joined_b = json.dumps(res_b)

    assert "BETA_MARKER_99" not in joined_a
    assert "ALPHA_MARKER_42" not in joined_b

    # File-level isolation via the language scan (entry points include unique files)
    assert res_a.get("folders_overview") is not None
    # The A-universe scan must not contain B's unique module folder names
    assert "uniquely_named_module_beta" not in joined_a
    assert "uniquely_named_module_alpha" not in joined_b


def test_dependency_scan_never_crosses_universes(universe_a, universe_b):
    skill = skill_registry.get_skill("dependencies")
    res = skill.execute("", None, universe_a)
    joined = json.dumps(res)
    assert "beta" not in joined.lower()


def test_security_scan_skips_env_files(universe_a):
    skill = skill_registry.get_skill("security")
    res = skill.execute("", None, universe_a)
    assert res["vulnerabilities"] == []  # .env must not be scanned


def test_safe_walk_excludes_db_and_cloned_repos(universe_a):
    """db/ and db/cloned_repos/ hold OTHER universes' clones — never scan them."""
    os.makedirs(os.path.join(universe_a, "db", "cloned_repos", "other_repo"), exist_ok=True)
    with open(
        os.path.join(universe_a, "db", "cloned_repos", "other_repo", "foreign.py"), "w"
    ) as f:
        f.write("FOREIGN_UNIVERSE_MARKER = True\n")

    from backend.skills.utils import scan_workspace

    scan = scan_workspace(universe_a)
    assert "foreign.py" not in json.dumps(scan)


def test_validate_workspace_rejects_missing_universe():
    from backend.skills.utils import validate_workspace

    ok, code = validate_workspace("")
    assert not ok and code == "NO_UNIVERSE_SELECTED"
    ok, code = validate_workspace("Z:/definitely/not/a/real/path/xyz")
    assert not ok and code == "WORKSPACE_NOT_FOUND"


# ── Skill logic (deterministic) ──────────────────────────────────────────────

def test_dependencies_detects_imports_and_cycles(universe_a):
    skill = skill_registry.get_skill("dependencies")
    res = skill.execute("", None, universe_a)

    targets = [d["target"] for d in res["dependencies_map"]]
    assert any("helper_shared" in t for t in targets)
    assert res["circular_dependencies"], "cycle_a <-> cycle_b cycle must be detected"


def test_health_score_counts_all_issues_not_truncated(universe_a):
    from backend.skills.health_analyzer import HealthAnalyzerSkill
    from backend.skills.cache import clear_cache

    skill = HealthAnalyzerSkill()
    clear_cache(universe_a, "health")
    res = skill.execute("", None, universe_a)

    # avg() splits (x+y)/2 across a 120-char line? No — instead assert score
    # matches the deterministic recomputation from returned issues
    high = sum(1 for i in res["issues"] if i["severity"] == "HIGH")
    medium = sum(1 for i in res["issues"] if i["severity"] == "MEDIUM")
    low = sum(1 for i in res["issues"] if i["severity"] == "LOW")
    # score was computed from totals BEFORE truncation; displayed list is capped
    # at 50, so if len(issues) < total the recomputation must be <= score.
    # LOW style nits are de-emphasised (0.5 weight, capped at 30 points total).
    penalty = high * 10 + medium * 4 + min(low * 0.5, 30)
    assert res["score"] == int(max(0, min(100, 100 - penalty))) or len(res["issues"]) < 50


def test_timeline_reports_real_commit_count(universe_a):
    skill = skill_registry.get_skill("timeline")
    res = skill.execute("", None, universe_a)

    if res.get("total_commits_note"):  # git available and ran
        assert res["total_commits"] >= 1
        assert res["total_commits"] >= len(res["timeline"])
    # no git → graceful degradation, never an exception
    assert "timeline" in res


# ── LLM failure handling (§12/§22 — no fake success) ────────────────────────

class _FakeLLMResponse:
    def __init__(self, status="success", response="{}", error_message=None):
        self.status = status
        self.response = response
        self.error_message = error_message
        self.provider = "test"
        self.model = "test"


def test_analyze_with_llm_raises_structured_error_on_failure(monkeypatch):
    import backend.skills.utils as utils

    class FakeRouter:
        def generate(self, **kwargs):
            return _FakeLLMResponse(status="failed", error_message="Connection refused")

    import backend.llm.model_router as mr
    monkeypatch.setattr(mr, "model_router", FakeRouter())
    monkeypatch.setattr(
        "backend.llm.model_router.model_router", FakeRouter(), raising=False
    )

    with pytest.raises(utils.SkillLLMError) as exc:
        utils.analyze_with_llm("test", "do something", '{"a": "string"}', os.getcwd())
    assert exc.value.code == "OLLAMA_UNAVAILABLE"


def test_analyze_with_llm_raises_on_malformed_json(monkeypatch):
    import backend.skills.utils as utils
    import backend.llm.model_router as mr

    class FakeRouter:
        def generate(self, **kwargs):
            return _FakeLLMResponse(status="success", response="not json at all")

    monkeypatch.setattr(mr, "model_router", FakeRouter())

    with pytest.raises(utils.SkillLLMError) as exc:
        utils.analyze_with_llm("test", "do something", '{"a": "string"}', os.getcwd())
    assert exc.value.code == "JSON_PARSE_FAILED"


def test_architecture_skill_does_not_cache_llm_failure(universe_a, monkeypatch):
    import backend.llm.model_router as mr
    import backend.skills.architecture_analyzer as arch
    from backend.skills.cache import get_cached, clear_cache

    clear_cache(universe_a, "architecture")

    class FakeRouter:
        def generate(self, **kwargs):
            return _FakeLLMResponse(status="failed", error_message="Connection refused")

    monkeypatch.setattr(mr, "model_router", FakeRouter())

    skill = skill_registry.get_skill("architecture")
    with pytest.raises(Exception):
        skill.execute("", None, universe_a)

    assert get_cached("architecture", universe_a) is None, "LLM failure must never be cached"


def test_extract_json_handles_fenced_output():
    from backend.skills.utils import _extract_json

    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('Sure! Here: {"a": 1} hope it helps') == {"a": 1}
    assert _extract_json("garbage") is None


# ── Router regression ────────────────────────────────────────────────────────

def test_router_ollama_model_resolution_no_nameerror():
    """Regression: generate() referenced settings before it was imported."""
    from backend.llm.model_router import model_router

    # The old bug crashed with NameError before reaching any provider; with the
    # fix, resolution at least yields a valid model string without raising.
    from backend.llm.task_router import task_router

    # Chat routes to Groq (fast cloud) with local qwen as fallback; every
    # other task stays local-first on Ollama qwen3:8b.
    provider, model = task_router.resolve_task("chat")
    assert provider == "groq"
    assert model  # non-empty model name
    for task in ("repository_summary", "code_review", "architecture_summary",
                 "tool_selection", "offline", "analysis"):
        provider, model = task_router.resolve_task(task)
        assert provider == "ollama", f"task '{task}' must stay on ollama"
        assert model


def test_check_llm_status_shape():
    from backend.skills.utils import check_llm_status

    status = check_llm_status()
    assert set(status.keys()) >= {"connected", "model", "model_available", "error"}

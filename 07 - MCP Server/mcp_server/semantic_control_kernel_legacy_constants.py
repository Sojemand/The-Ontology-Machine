from __future__ import annotations


def _underscore(*parts: str) -> str:
    return "_".join(parts)


def _dot(*parts: str) -> str:
    return ".".join(parts)


def _path(*parts: str, trailing: bool = False) -> str:
    value = "/".join(parts)
    return f"{value}/" if trailing else value


LEGACY_PACKAGE_DIR = _path("mcp_server", "semantic_kernel", trailing=True)
LEGACY_CATALOG_FILE = _path("mcp_server", f"{_underscore('tool', 'catalog', 'semantic', 'kernel')}.py")
LEGACY_HANDLERS_FILE = _path("mcp_server", f"{_underscore('tool', 'handlers', 'semantic', 'kernel')}.py")
LEGACY_STATE_DIR = _path("state", _underscore("semantic", "kernel"), trailing=True)
LEGACY_MODULE_IMPORT = _dot("mcp_server", "semantic_kernel")
LEGACY_CATALOG_SYMBOL = _underscore("tool", "catalog", "semantic", "kernel")
LEGACY_HANDLERS_SYMBOL = _underscore("tool", "handlers", "semantic", "kernel")
LEGACY_TOOL_NAMES_SYMBOL = _underscore("KERNEL", "TOOL", "NAMES")
LEGACY_WORKFLOW_FAMILY_KEY = _underscore("workflow", "family", "id")
LEGACY_WORKFLOW_REVISION_KEY = _underscore("workflow", "revision")
LEGACY_ACTION_TOKEN_KEY = _underscore("action", "token")
LEGACY_RECOMMENDED_WORKFLOW_KEY = _underscore("recommended", "first", "workflow", "family", "id")
LEGACY_RELATED_WORKFLOW_KEY = _underscore("related", "workflow", "family", "ids")
LEGACY_SAFE_NEXT_WORKFLOWS_KEY = _underscore("safe", "next", "kernel", "workflows")


REQUIRED_SCAN_ROOTS: tuple[str, ...] = (
    LEGACY_PACKAGE_DIR,
    LEGACY_CATALOG_FILE,
    LEGACY_HANDLERS_FILE,
    "mcp_server/tool_catalog.py",
    "mcp_server/tool_handler_registry.py",
    "mcp_server/tool_visibility.py",
    "mcp_server/permission_defaults.py",
    "config/agent_permissions.json",
    "runtime/runtime-manifest.json",
    "README.md",
    "mcp_server/product_semantics.py",
    "mcp_server/product_semantics_cards.py",
    "mcp_server/product_semantics_playbooks.py",
    "mcp_server/product_semantics_support.py",
    "mcp_server/tool_handlers_source_fit.py",
    "mcp_server/tool_handler_source_fit_review.py",
    "mcp_server/tool_handler_source_sample_set_paths.py",
    "mcp_server/tool_handler_source_sample_set_review.py",
    "dev-tests/tests/",
    LEGACY_STATE_DIR,
)

REQUIRED_OLD_SYMBOLS: tuple[str, ...] = (
    LEGACY_MODULE_IMPORT,
    LEGACY_CATALOG_SYMBOL,
    LEGACY_HANDLERS_SYMBOL,
    LEGACY_TOOL_NAMES_SYMBOL,
    _underscore("llm", "action", "catalog"),
    _underscore("open", "workflow"),
    _underscore("inspect", "workflow"),
    _underscore("execute", "readonly", "workflow", "action"),
    _underscore("execute", "author", "workflow", "action"),
    _underscore("execute", "operator", "workflow", "action"),
    _underscore("execute", "admin", "workflow", "action"),
    _underscore("interrupt", "workflow"),
    _underscore("close", "workflow"),
    LEGACY_WORKFLOW_FAMILY_KEY,
    LEGACY_WORKFLOW_REVISION_KEY,
    LEGACY_ACTION_TOKEN_KEY,
    LEGACY_RECOMMENDED_WORKFLOW_KEY,
    LEGACY_RELATED_WORKFLOW_KEY,
    LEGACY_SAFE_NEXT_WORKFLOWS_KEY,
)

GENERATED_DIR_NAMES: frozenset[str] = frozenset(
    {"__pycache__", ".pytest_cache", ".venv", "venv"}
)
TEXT_LIKE_SUFFIXES: frozenset[str] = frozenset(
    {
        "",
        ".bat",
        ".cfg",
        ".css",
        ".html",
        ".ini",
        ".js",
        ".json",
        ".jsonl",
        ".md",
        ".ps1",
        ".py",
        ".sql",
        ".toml",
        ".ts",
        ".txt",
        ".yaml",
        ".yml",
    }
)

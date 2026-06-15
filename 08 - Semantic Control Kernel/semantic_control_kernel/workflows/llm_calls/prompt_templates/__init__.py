from __future__ import annotations

from importlib import import_module


PROMPT_MODULES = (
    "analyze_samples",
    "user_report_samples",
    "create_taxonomy_to_sample_analyses",
    "create_projections_to_sample_analyses",
)

_TEMPLATES = {name: import_module(f"{__name__}.{name}") for name in PROMPT_MODULES}
USER_PROMPT_TEMPLATES: dict[str, str] = {name: module.USER_PROMPT for name, module in _TEMPLATES.items()}
OUTPUT_APPENDICES: dict[str, str] = {name: module.OUTPUT_APPENDIX for name, module in _TEMPLATES.items()}

__all__ = ["USER_PROMPT_TEMPLATES", "OUTPUT_APPENDICES"]

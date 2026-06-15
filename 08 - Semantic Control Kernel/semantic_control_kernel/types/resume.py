from __future__ import annotations

from semantic_control_kernel.types.base import make_contract_type


ResumeOption = make_contract_type("ResumeOption", "kernel.resume_option.v1", __name__)


RESUME_OPTION_SCHEMA_VERSION = ResumeOption.SCHEMA_VERSION

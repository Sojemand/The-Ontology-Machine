"""Typed route-family and profile carriers for the orchestrator intake stage."""

from __future__ import annotations

from dataclasses import dataclass

from .. import policy_store


def route_family_documents() -> str:
    return policy_store.route_families()[0]


def route_family_images() -> str:
    return route_family_documents()


def route_family_files() -> str:
    return route_family_documents()


def default_optimizer_module_key() -> str:
    return "optimizer"


def default_interpreter_module_key() -> str:
    return "interpreter"


def is_optimizer_profile(value: str) -> bool:
    return value in {"vision", "file"}


def is_interpreter_profile(value: str) -> bool:
    return value in {"vision", "file", "table"}


def route_family_tables() -> str:
    return ""


def route_families() -> tuple[str, ...]:
    return policy_store.route_families()


def pdf_classification_born_digital() -> str:
    return policy_store.pdf_classification("born_digital")


def pdf_classification_scan() -> str:
    return policy_store.pdf_classification("scan")


@dataclass(frozen=True)
class IntakeDecision:
    route_family: str = ""
    optimizer_profile: str = ""
    interpreter_profile: str = ""
    optimizer_module_key: str = ""
    interpreter_module_key: str = ""
    intake_reason: str = ""
    error: str = ""
    final_error: bool = False

    @property
    def processable(self) -> bool:
        return (
            not self.error
            and bool(self.optimizer_module_key)
            and bool(self.interpreter_module_key)
            and is_optimizer_profile(self.optimizer_profile)
            and is_interpreter_profile(self.interpreter_profile)
        )


def is_route_family(value: str) -> bool:
    return value in route_families()


def __getattr__(name: str):
    dynamic = {
        "ROUTE_FAMILY_DOCUMENTS": route_family_documents,
        "ROUTE_FAMILY_IMAGES": route_family_images,
        "ROUTE_FAMILY_FILES": route_family_files,
        "ROUTE_FAMILIES": route_families,
        "PDF_CLASSIFICATION_BORN_DIGITAL": pdf_classification_born_digital,
        "PDF_CLASSIFICATION_SCAN": pdf_classification_scan,
    }
    if name in dynamic:
        return dynamic[name]()
    raise AttributeError(name)

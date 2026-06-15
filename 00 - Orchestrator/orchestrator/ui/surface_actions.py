"""Mixin methods for the desktop UI surface."""

from __future__ import annotations

from . import model_catalog_actions
from .surface_actions_core import OrchestratorAppCoreActions
from .surface_actions_credentials import OrchestratorAppCredentialActions
from .surface_actions_dialogs import OrchestratorAppDialogActions


class OrchestratorAppActions(
    OrchestratorAppCoreActions,
    OrchestratorAppCredentialActions,
    OrchestratorAppDialogActions,
):
    pass
